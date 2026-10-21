"""Pruebas del configurador: aislamiento de credenciales y errores OCI, sin red."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import io
from contextlib import redirect_stdout
import zipfile

SCRIPT = Path(__file__).parents[1] / "configurar-object-storage.py"
spec = importlib.util.spec_from_file_location("oci_setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

IDENTITY = {"user": "ocid1.user.oc1..testuser", "tenancy": "ocid1.tenancy.oc1..testtenancy",
            "compartment": "ocid1.tenancy.oc1..testtenancy", "region": "sa-saopaulo-1",
            "namespace": "testnamespace", "bucket": "nuevamente-contenidos-educativos"}
BUCKET = {"name": IDENTITY["bucket"], "compartment-id": IDENTITY["compartment"],
          "namespace": IDENTITY["namespace"], "public-access-type": "NoPublicAccess",
          "storage-tier": "Standard", "auto-tiering": "Disabled", "versioning": "Disabled",
          "kms-key-id": None}


class CLIResponseTests(unittest.TestCase):
    def run_cli(self, stdout, stderr="", code=0, operation=("os", "bucket", "list"), **kwargs):
        with patch.object(setup.subprocess, "run", return_value=Mock(
                returncode=code, stdout=stdout, stderr=stderr)) as execute:
            value = setup.CLI(IDENTITY["region"]).call(operation, **kwargs)
            return value, execute

    def test_successful_empty_list_is_accepted_but_empty_mutation_is_rejected(self):
        self.assertEqual(self.run_cli("")[0], [])
        with self.assertRaises(setup.OCIError):
            self.run_cli("", operation=("os", "bucket", "create"))

    def test_query_warning_does_not_hide_an_unknown_list(self):
        with self.assertRaises(setup.SetupError):
            self.run_cli("", "Query returned empty result")

    def test_write_headers_are_not_confused_with_data_wrapper(self):
        value, _ = self.run_cli('{"etag":"confirmed"}', operation=("os", "object", "put"), result="headers")
        self.assertEqual(value["etag"], "confirmed")
        with self.assertRaises(setup.SetupError):
            self.run_cli('{"data":{}}', operation=("os", "object", "put"), result="headers")

    def test_file_download_accepts_no_stdout(self):
        self.assertIsNone(self.run_cli("", operation=("os", "object", "get"), result="file")[0])

    def test_bucket_auto_tiering_is_requested_with_cloud_shell_and_exported_key(self):
        # OCI documenta null si fields no pide autoTiering expresamente.
        def provider(command, **kwargs):
            fields = [command[i + 1] for i, arg in enumerate(command[:-1]) if arg == "--fields"]
            actual = "Disabled" if "autoTiering" in fields else None
            return Mock(returncode=0, stdout=json.dumps({"data": {**BUCKET, "auto-tiering": actual}}), stderr="")
        for config in (None, Path("exported-config")):
            with self.subTest(config=config), patch.object(setup.subprocess, "run", side_effect=provider):
                bucket = setup.CLI(IDENTITY["region"], config).call(
                    ("os", "bucket", "get"), "--namespace-name", IDENTITY["namespace"], "--name", IDENTITY["bucket"])
                setup.validate_bucket(bucket, IDENTITY)

    def test_null_auto_tiering_is_not_silently_assumed_to_be_disabled(self):
        with self.assertRaises(setup.SetupError):
            setup.validate_bucket({**BUCKET, "auto-tiering": None}, IDENTITY)

    def test_api_key_validation_cannot_fall_back_to_cloud_shell_or_env_keys(self):
        with patch.dict(os.environ, {"OCI_CLI_AUTH": "instance_obo_user", "OCI_CLI_KEY_CONTENT": "secret",
                                    "OCI_CLI_CONFIG_FILE": "wrong", "OCI_CLI_ENDPOINT": "https://wrong"}), \
             patch.object(setup.subprocess, "run", return_value=Mock(returncode=0, stdout='{"data":{}}')) as run:
            setup.CLI(IDENTITY["region"], Path("own-config")).call(("os", "bucket", "get"))
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--auth") + 1], "api_key")
            self.assertEqual(command[command.index("--config-file") + 1], "own-config")
            self.assertFalse(any(k.startswith("OCI_CLI_") for k in run.call_args.kwargs["env"]))
            self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_error_output_never_exposes_provider_message_or_credentials(self):
        with self.assertRaises(setup.OCIError) as caught:
            self.run_cli("", 'prefix {"code":"NotAuthenticated","message":"PRIVATE SECRET"}', 1)
        self.assertEqual(caught.exception.code, "NotAuthenticated")
        self.assertNotIn("PRIVATE SECRET", str(caught.exception))
        self.assertEqual(setup.error_code('{"code":"PRIVATE SECRET"}'), "NO_DETERMINADO")

    def test_uncertain_writes_are_not_automatically_repeated(self):
        with patch.object(setup.subprocess, "run", side_effect=subprocess.TimeoutExpired("oci", 90)) as run:
            with self.assertRaises(setup.OCIError):
                setup.CLI(IDENTITY["region"]).call(("os", "bucket", "create"))
            self.assertEqual(run.call_count, 1)

    def test_compute_policy_delete_and_terraform_are_out_of_scope(self):
        for operation in (("compute", "instance", "launch"), ("iam", "policy", "create"),
                          ("os", "bucket", "delete"), ("iam", "user", "api-key", "delete")):
            with self.subTest(operation=operation), patch.object(setup.subprocess, "run") as run:
                with self.assertRaises(setup.SetupError):
                    setup.CLI(IDENTITY["region"]).call(operation)
                run.assert_not_called()


class ResourceTests(unittest.TestCase):
    def test_reuses_existing_bucket_without_modifying_it(self):
        cli = Mock()
        cli.call.side_effect = [[{"name": IDENTITY["bucket"]}], dict(BUCKET)]
        setup.ensure_bucket(cli, IDENTITY)
        self.assertEqual([c.args[0] for c in cli.call.call_args_list],
                         [("os", "bucket", "list"), ("os", "bucket", "get")])

    def test_creates_only_private_standard_bucket_with_no_versioning(self):
        cli = Mock()
        cli.call.side_effect = [[], dict(BUCKET), dict(BUCKET)]
        setup.ensure_bucket(cli, IDENTITY)
        command = cli.call.call_args_list[1].args
        self.assertEqual(command[0], ("os", "bucket", "create"))
        for flag, value in (("--public-access-type", "NoPublicAccess"), ("--storage-tier", "Standard"),
                            ("--versioning", "Disabled"), ("--auto-tiering", "Disabled")):
            self.assertEqual(command[command.index(flag) + 1], value)

    def test_incompatible_existing_bucket_is_never_changed(self):
        for field, value in (("public-access-type", "ObjectRead"), ("storage-tier", "Archive"),
                             ("compartment-id", "another"), ("namespace", "another"),
                             ("versioning", "Enabled"), ("auto-tiering", "InfrequentAccess"),
                             ("kms-key-id", "some-key")):
            with self.subTest(field=field), self.assertRaises(setup.SetupError):
                setup.validate_bucket({**BUCKET, field: value}, IDENTITY)

    def test_failure_to_list_does_not_trigger_bucket_creation(self):
        cli = Mock()
        cli.call.side_effect = setup.OCIError(("os", "bucket", "list"), "NotAuthorizedOrNotFound")
        with self.assertRaises(setup.OCIError):
            setup.ensure_bucket(cli, IDENTITY)
        self.assertEqual(cli.call.call_count, 1)

    def test_uses_home_region_and_rejects_different_explicit_region(self):
        cli = Mock()
        cli.call.return_value = [{"region-name": "sa-saopaulo-1", "is-home-region": True}]
        self.assertEqual(setup.home_region(cli, IDENTITY["tenancy"], None), "sa-saopaulo-1")
        with self.assertRaises(setup.SetupError):
            setup.home_region(cli, IDENTITY["tenancy"], "mx-monterrey-1")

    def test_cloud_shell_identity_is_detected_without_embedded_account_ids(self):
        args = argparse.Namespace(compartment=None, region=None)
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,
                {"OCI_CS_USER_OCID": IDENTITY["user"], "OCI_TENANCY": IDENTITY["tenancy"],
                 "OCI_CLI_CONFIG_FILE": str(Path(folder) / "missing"), "OCI_REGION": IDENTITY["region"]}, clear=True):
            self.assertEqual(setup.detect_identity(args),
                             (IDENTITY["tenancy"], IDENTITY["user"], IDENTITY["compartment"], IDENTITY["region"]))

    def test_key_is_reused_and_unrelated_keys_are_never_removed(self):
        cli = Mock()
        cli.call.return_value = [{"fingerprint": "existing", "lifecycle-state": "ACTIVE"}]
        setup.ensure_api_key(cli, IDENTITY["user"], "existing", Path("public.pem"))
        self.assertTrue(all(c.args[0][-1] == "list" for c in cli.call.call_args_list))
        cli.call.reset_mock()
        cli.call.return_value = [{"fingerprint": str(n)} for n in range(3)]
        with self.assertRaises(setup.SetupError):
            setup.ensure_api_key(cli, IDENTITY["user"], "new", Path("public.pem"))
        self.assertEqual(cli.call.call_count, 1)

    def test_unconfirmed_key_activation_is_not_reported_as_ready(self):
        cli = Mock()
        cli.call.return_value = [{"fingerprint": "existing", "lifecycle-state": "CREATING"}]
        with patch.object(setup.time, "sleep"), self.assertRaises(setup.SetupError):
            setup.ensure_api_key(cli, IDENTITY["user"], "existing", Path("public.pem"))


class ProbeAndExportTests(unittest.TestCase):
    def fake_transport(self, corrupt=False):
        objects = {}
        provider_md5 = hashlib.md5
        def transfer(operation, *args, **kwargs):
            name = args[args.index("--name") + 1]
            path = Path(args[args.index("--file") + 1])
            if operation[-1] == "put":
                content = path.read_bytes()
                objects[name] = content
                return {"etag": "confirmed", "opc-content-md5": base64.b64encode(provider_md5(content).digest()).decode()}
            path.write_bytes(b"CORRUPTED" if corrupt else objects[name])
        return Mock(side_effect=transfer)

    def test_probe_verifies_original_json_and_overwrite_with_exported_auth(self):
        cli = Mock()
        cli.call = self.fake_transport()
        with tempfile.TemporaryDirectory() as folder:
            evidence = setup.probe_storage(cli, IDENTITY, Path(folder), "a" * 32)
            self.assertEqual(len(evidence), 2)
            source = (Path(folder) / "original.txt.descargado").read_bytes()
            document = json.loads((Path(folder) / "resultado.json.descargado").read_bytes())
            self.assertEqual(document["original_sha256"], hashlib.sha256(source).hexdigest())
            operations = [c.args[0][-1] for c in cli.call.call_args_list]
            self.assertEqual(operations, ["put", "put", "get", "put", "get"])
            self.assertIn("--if-match", cli.call.call_args_list[1].args)

    def test_corrupt_download_and_missing_checksum_do_not_allow_success(self):
        cli = Mock()
        cli.call = self.fake_transport(corrupt=True)
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(setup.SetupError):
            setup.probe_storage(cli, IDENTITY, Path(folder), "a" * 32)
        cli.call = Mock(return_value={"etag": "only-etag"})
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(setup.SetupError):
            setup.probe_storage(cli, IDENTITY, Path(folder), "a" * 32)

    def test_generated_package_is_private_and_matches_docker_mount(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "key.pem").write_bytes(b"FAKE KEY FOR OFFLINE TEST ONLY")
            archive = setup.export_bundle(directory, IDENTITY, "fake-fingerprint", [])
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(set(bundle.namelist()),
                                 {"oci/config", "oci/key.pem", "oci.env", "conectar-docker.ps1", "resultado.json", "LEEME.md"})
                config = bundle.read("oci/config").decode()
                self.assertIn("key_file=/run/secrets/oci/key.pem", config)
                env = bundle.read("oci.env").decode()
                self.assertIn("OCI_STORAGE_ENABLED=true", env)
                self.assertIn("OCI_CREDENTIALS_DIRECTORY=@@OCI_CREDENTIALS_DIRECTORY@@", env)
                self.assertNotIn("FAKE KEY", env)
                self.assertNotIn("FAKE KEY", bundle.read("resultado.json").decode())
                self.assertIn("No compartirlo", bundle.read("LEEME.md").decode())
                self.assertIn("SetAccessRuleProtection($true, $false)", bundle.read("conectar-docker.ps1").decode())


class RestrictedHashTests(unittest.TestCase):
    def blocked_security_md5(self):
        original = hashlib.md5
        def restricted(data=b"", **options):
            if options.get("usedforsecurity") is not False:
                raise ValueError("[digital envelope routines] unsupported")
            return original(data, usedforsecurity=False)
        return restricted

    def test_key_fingerprint_uses_md5_as_oci_identifier_in_restricted_python(self):
        der = b"PUBLIC KEY DER FOR OFFLINE TEST"
        expected = hashlib.md5(der, usedforsecurity=False).hexdigest()
        expected = ":".join(expected[i:i + 2] for i in range(0, len(expected), 2))
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "key.pem").write_bytes(b"FAKE PRIVATE KEY FOR TEST")
            with patch.object(setup, "openssl", side_effect=[b"FAKE PUBLIC PEM", der]), \
                 patch.object(setup.hashlib, "md5", side_effect=self.blocked_security_md5()):
                self.assertEqual(setup.prepare_key(directory), expected)

    def test_object_checksum_can_be_computed_in_restricted_python(self):
        cli = Mock()
        cli.call = ProbeAndExportTests().fake_transport()
        restricted = self.blocked_security_md5()
        with tempfile.TemporaryDirectory() as folder, patch.object(setup.hashlib, "md5", side_effect=restricted):
            evidence = setup.probe_storage(cli, IDENTITY, Path(folder), "b" * 32)
            self.assertEqual(len(evidence), 2)

    def test_legacy_python_without_usage_keyword_is_supported(self):
        original = hashlib.md5
        def legacy(data=b"", **options):
            if options:
                raise TypeError("usedforsecurity is not supported")
            return original(data, usedforsecurity=False)
        expected = original(b"test", usedforsecurity=False).digest()
        with patch.object(setup.hashlib, "md5", side_effect=legacy):
            self.assertEqual(setup.md5_for_oci(b"test").digest(), expected)

    def test_restricted_runtime_failure_is_clear_without_provider_message(self):
        with patch.object(setup.hashlib, "md5", side_effect=ValueError("PRIVATE MESSAGE")), \
             self.assertRaises(setup.SetupError) as error:
            setup.md5_for_oci(b"test")
        self.assertIn("uso no criptografico", str(error.exception))
        self.assertNotIn("PRIVATE MESSAGE", str(error.exception))


class DiagnosticTests(unittest.TestCase):
    def test_local_error_reports_source_location_without_exception_contents(self):
        output = io.StringIO()
        with patch.object(setup.sys, "argv", ["configurar-object-storage.py"]), \
             patch.object(setup, "configure", side_effect=ValueError("PRIVATE KEY MUST NOT BE PRINTED")), \
             patch.object(setup.os, "umask"), redirect_stdout(output):
            self.assertEqual(setup.main(), 1)
        self.assertIn("ValueError en main()", output.getvalue())
        self.assertNotIn("PRIVATE KEY MUST NOT BE PRINTED", output.getvalue())


if __name__ == "__main__":
    unittest.main()
