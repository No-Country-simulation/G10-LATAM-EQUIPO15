"""Guardas para acciones con recursos facturables; sin cuenta Azure ni red."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from types import SimpleNamespace


def load(name):
    path = Path(__file__).resolve().parents[1] / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


manage = load('gestionar')
pack = load('empaquetar')


class AzureGuards(unittest.TestCase):
    def setUp(self):
        self.trial = {'state': 'Enabled', 'subscriptionPolicies': {
            'spendingLimit': 'On', 'quotaId': 'FreeTrial_2014-09-01'}}
        self.sku = {'name': 'Standard_D2as_v5', 'resourceType': 'virtualMachines',
                    'locations': ['brazilsouth'], 'family': 'standardDASv5Family',
                    'capabilities': [{'name': 'vCPUs', 'value': '2'}, {'name': 'MemoryGB', 'value': '8'}],
                    'restrictions': []}
        self.usage = [{'name': {'value': 'cores'}, 'limit': 4, 'currentValue': 0},
                      {'name': {'value': 'standardDASv5Family'}, 'limit': 2, 'currentValue': 0}]

    def test_trial_with_spending_limit_is_accepted(self):
        manage.require_trial(self.trial)

    def test_paid_disabled_or_unknown_subscription_is_rejected(self):
        for key, value in [('spendingLimit', 'Off'), ('spendingLimit', 'CurrentPeriodOff'),
                           ('spendingLimit', None), ('quotaId', 'PayAsYouGo_2014-09-01')]:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(self.trial)
                data['subscriptionPolicies'][key] = value
                with self.assertRaises(manage.DeploymentError):
                    manage.require_trial(data)
        for state in ('Disabled', 'Warned', None):
            with self.assertRaises(manage.DeploymentError):
                manage.require_trial({**self.trial, 'state': state})

    def test_catalog_and_both_quotas_must_allow_size(self):
        self.assertTrue(manage.eligible(self.sku, 'brazilsouth', self.usage))
        for index in (0, 1):
            quota = copy.deepcopy(self.usage)
            quota[index]['currentValue'] = quota[index]['limit'] - 1
            self.assertFalse(manage.eligible(self.sku, 'brazilsouth', quota))
        self.assertFalse(manage.eligible(self.sku, 'brazilsouth', self.usage[:1]))
        self.assertFalse(manage.eligible(self.sku, 'eastus2', self.usage))

    def test_location_restriction_and_wrong_hardware_are_rejected(self):
        restricted = {**self.sku, 'restrictions': [{'type': 'Location', 'reasonCode': 'NotAvailableForSubscription'}]}
        self.assertFalse(manage.eligible(restricted, 'brazilsouth', self.usage))
        for memory in ('1', '4', '16', 'desconocido'):
            data = copy.deepcopy(self.sku)
            data['capabilities'][1]['value'] = memory
            self.assertFalse(manage.eligible(data, 'brazilsouth', self.usage))

    def test_quota_numeric_strings_from_cli_are_supported(self):
        usage = copy.deepcopy(self.usage)
        for quota in usage:
            quota['limit'] = str(quota['limit'])
            quota['currentValue'] = str(quota['currentValue'])
        self.assertTrue(manage.eligible(self.sku, 'brazilsouth', usage))
        for value in ('NaN', 'Infinity', 'desconocido', '-1'):
            usage[0]['currentValue'] = value
            self.assertFalse(manage.eligible(self.sku, 'brazilsouth', usage))

    def test_plan_with_replacement_or_deletion_is_rejected(self):
        for actions in (['delete'], ['delete', 'create'], ['create', 'delete']):
            with self.assertRaises(manage.DeploymentError):
                manage.require_nondestructive_plan({'resource_changes': [{'change': {'actions': actions}}]})
        manage.require_nondestructive_plan({'resource_changes': [{'change': {'actions': ['create']}}]})

    def test_runtime_archive_excludes_credentials_and_local_data(self):
        for name in ('ia/.env', 'ia/.env.local', 'backend/.oci/config', 'backend/token.pem',
                     'ia/secret.key', 'ia/__pycache__/cache.pyc', 'scripts/azure/tests/test.py'):
            self.assertFalse(pack.allowed(name), name)
        for name in ('ia/src/dataia/pipeline.py', 'backend/app/core/config.py', 'frontend/js/api.js',
                     'ia/requirements-tests.txt', 'compose.azure.yaml'):
            self.assertTrue(pack.allowed(name), name)

    def test_catalog_filters_server_side_and_follows_pages(self):
        next_page = 'https://management.azure.com/subscriptions/test/providers/Microsoft.Compute/skus?skiptoken=next'
        with patch.object(manage, 'az', side_effect=[{'value': [self.sku], 'nextLink': next_page}, {'value': [{'name': 'second'}]}]) as query:
            rows = manage.regional_skus('test', 'brazilsouth')
        self.assertEqual(2, len(rows))
        first_url = query.call_args_list[0].args[-1]
        self.assertEqual(["location eq 'brazilsouth'"], parse_qs(urlsplit(first_url).query)['$filter'])
        self.assertEqual(next_page, query.call_args_list[1].args[-1])

    def test_host_key_from_real_customscript_status_shape(self):
        message = 'Enable succeeded: \n[stdout]\nssh-ed25519 AAAAtest= root@vm\n\n[stderr]\n'
        for field in ('statuses', 'substatuses'):
            view = {'instanceView': {field: [{'code': 'ProvisioningState/succeeded', 'message': message}]}}
            self.assertEqual('ssh-ed25519 AAAAtest=', manage.extension_host_key(view))
        with self.assertRaises(manage.DeploymentError):
            manage.extension_host_key({'instanceView': {'statuses': []}})
        with self.assertRaises(manage.DeploymentError):
            manage.extension_host_key({'statuses': [{'message': message + '\nssh-ed25519 BBBBtest= other@vm\n'}]})

    def test_only_void_operations_accept_empty_cli_output(self):
        with patch.object(manage.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='')):
            with self.assertRaises(manage.DeploymentError):
                manage.az('account', 'list')
            self.assertIsNone(manage.az('provider', 'register', '--namespace', 'Microsoft.Compute', allow_empty=True))

    def test_catalog_rejects_untrusted_or_repeated_page(self):
        for next_page in ('https://example.com/steal', 'http://management.azure.com/invalid'):
            with patch.object(manage, 'az', return_value={'value': [], 'nextLink': next_page}) as query:
                with self.assertRaises(manage.DeploymentError):
                    manage.regional_skus('test', 'brazilsouth')
                self.assertEqual(1, query.call_count)


if __name__ == '__main__':
    unittest.main()
