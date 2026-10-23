"""Servidor exclusivo para QA: SDK real, bucket persistente controlado, IA por HTTP."""

import base64
from hashlib import md5
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import oci
import uvicorn

from app.main import app
from app.services.oci_service import OCIStorage, get_oci_storage
from test_history import BucketTransport


class PersistentBucket(BucketTransport):
    def __init__(self):
        super().__init__()
        self.path = Path('/data/bucket.json')
        if self.path.exists():
            self.objects = {k: base64.b64decode(v) for k, v in json.loads(self.path.read_text()).items()}

    def send(self, request, **kwargs):
        response = super().send(request, **kwargs)
        if (request.method == 'PUT' and response.status_code == 200) or (request.method == 'DELETE' and response.status_code == 204):
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps({k: base64.b64encode(v).decode() for k, v in self.objects.items()}))
            os.replace(temporary, self.path)
        return response


bucket = PersistentBucket()
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
der = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
digest = md5(der, usedforsecurity=False).hexdigest()
config = {'user': 'ocid1.user.oc1..fixture', 'tenancy': 'ocid1.tenancy.oc1..fixture',
          'fingerprint': ':'.join(digest[i:i+2] for i in range(0, 32, 2)), 'region': 'us-ashburn-1',
          'key_content': key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()}


def sdk():
    client = oci.object_storage.ObjectStorageClient(config, service_endpoint='https://objectstorage.fixture.invalid',
                                                  retry_strategy=oci.retry.NoneRetryStrategy())
    client.base_client.session.mount('https://', bucket)
    return client


app.dependency_overrides[get_oci_storage] = lambda: OCIStorage('namespace-fixture', 'bucket-fixture', client_factory=sdk)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
