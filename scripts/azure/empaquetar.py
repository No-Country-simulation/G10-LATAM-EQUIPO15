"""Empaqueta solo los archivos de ejecucion no ignorados; nunca configuracion privada."""
import io
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile

RUNTIME = ('backend', 'frontend', 'ia', 'nuevamente-ai-core', 'scripts/azure',
           'compose.integration.yaml', 'compose.oci.credentials.yaml', 'compose.azure.yaml')
DENIED = {'.git', '.gstack', '.aws', '.codex', '.agents', '.worktrees', 'node_modules',
          '__pycache__', '.venv', '.oci', '.nuevamente-object-storage', 'tests'}


def allowed(name):
    parts = PurePosixPath(name).parts
    return bool(parts) and not any(p in DENIED or p.startswith('.env') for p in parts) and not name.lower().endswith(('.pem', '.key', '.pfx', '.p12', '.log', '.pyc', '.tar.gz'))


def package(root, destination):
    root = Path(root).resolve()
    paths = subprocess.run(['git', '-c', f'safe.directory={root.as_posix()}', '-C', str(root),
                            'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', *RUNTIME],
                           check=True, capture_output=True).stdout.decode('utf-8').split('\0')
    count = 0
    with tarfile.open(destination, 'w:gz') as archive:
        for name in sorted(set(paths)):
            if not name or not allowed(name):
                continue
            path = root / name
            if path.is_symlink() or not path.is_file() or root not in path.resolve().parents:
                raise ValueError('Archivo no regular en el paquete de ejecucion.')
            body = path.read_bytes()
            if path.suffix == '.sh':
                body = body.replace(b'\r\n', b'\n')
            info = tarfile.TarInfo(name)
            info.size = len(body)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(body))
            count += 1
    print(f'Paquete de aplicacion preparado: {count} archivos; configuracion privada separada.')


if __name__ == '__main__':
    package(sys.argv[1], sys.argv[2])
