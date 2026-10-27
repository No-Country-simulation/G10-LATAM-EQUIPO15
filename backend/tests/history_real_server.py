"""QA optativa con OCI real. Lee el ZIP privado montado; nunca imprime sus secretos.

Usar únicamente en el entorno de QA con IA simulada. Crea documentos nuevos en OCI;
no importa, modifica ni elimina el historial de otros navegadores.
"""

import configparser
from io import StringIO
from zipfile import ZipFile

from dotenv import dotenv_values
import oci
import uvicorn

from app.main import app
from app.services.oci_service import OCIStorage, get_oci_storage


with ZipFile('/run/secrets/oci-connection.zip') as archive:
    environment = dotenv_values(stream=StringIO(archive.read('oci.env').decode()))
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(archive.read('oci/config').decode())
    config = dict(parser[environment.get('OCI_CONFIG_PROFILE', 'DEFAULT')])
    config.pop('key_file', None)
    config['key_content'] = archive.read('oci/key.pem').decode()
    if environment.get('OCI_REGION'):
        config['region'] = environment['OCI_REGION']


def sdk():
    return oci.object_storage.ObjectStorageClient(config, timeout=(5, 10), retry_strategy=oci.retry.NoneRetryStrategy())


app.dependency_overrides[get_oci_storage] = lambda: OCIStorage(
    environment['OCI_NAMESPACE'], environment['OCI_BUCKET_NAME'], client_factory=sdk,
)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
