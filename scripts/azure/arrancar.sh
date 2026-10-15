#!/usr/bin/env bash
set -euo pipefail
cd /home/azureuser/nuevamente
private=/home/azureuser/.nuevamente-private
export AZURE_BACKEND_UID="$(id -u)"
export AZURE_BACKEND_GID="$(id -g)"
args=(compose --env-file "$private/gemini.env" --env-file "$private/oci.env"
      -f compose.integration.yaml -f compose.oci.credentials.yaml -f compose.azure.yaml)
docker "${args[@]}" config --quiet
docker "${args[@]}" build
docker "${args[@]}" up -d --wait --wait-timeout 240
docker "${args[@]}" exec -T backend python -c 'from app.core.config import settings; import sys; sys.exit(0 if settings.OCI_STORAGE_ENABLED else 1)'
docker "${args[@]}" exec -T backend python - <<'PY'
import sys
from app.core.config import settings
from app.services.oci_service import create_oci_client
try:
    result = create_oci_client().get_bucket(settings.OCI_NAMESPACE, settings.OCI_BUCKET_NAME)
    assert result.status == 200
    print('OCI_CONEXION_VALIDADA: el backend accede al bucket privado.')
except Exception as error:
    print('OCI_NO_VALIDADO:', type(error).__name__, getattr(error, 'status', None))
    sys.exit(1)
PY
curl --fail --silent --output /dev/null http://127.0.0.1/
printf '%s\n' 'APLICACION_INICIADA: frontend publico, IA interna y OCI activado.'
