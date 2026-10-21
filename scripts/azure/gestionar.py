"""CLI Azure y Terraform en Docker; credenciales y estado solo en /state."""
import argparse
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import re
import shutil
import tempfile
import time
import urllib.request
from urllib.parse import urlencode, urlsplit

STATE = Path('/state')
SIZES = ('Standard_D2as_v5', 'Standard_D2s_v5', 'Standard_D2as_v6', 'Standard_D2s_v6', 'Standard_B2ms')


class DeploymentError(Exception):
    pass


def run_json(args, allow_empty=False):
    try:
        result = subprocess.run(args, text=True, encoding='utf-8', capture_output=True, timeout=240)
    except subprocess.TimeoutExpired:
        raise DeploymentError('Tiempo agotado en ' + ' '.join(args[:3]) + '.') from None
    if result.returncode:
        raise DeploymentError('Fallo la consulta ' + ' '.join(args[:3]) + '. Revisar sesion, permisos y registro del proveedor.')
    if allow_empty and not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise DeploymentError('La consulta no devolvio JSON valido.') from None


def az(*args, allow_empty=False):
    return run_json(['az', *args, '--only-show-errors', '--output', 'json'], allow_empty=allow_empty)


def regional_skus(subscription_id, region):
    # list-skus de CLI descarga el catalogo global y puede exceder varios minutos.
    # La API oficial admite filtrar en el servidor; conservar todas sus paginas.
    base = f'https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.Compute/skus'
    url = base + '?' + urlencode({'api-version': '2021-07-01', '$filter': f"location eq '{region}'"})
    result = []
    seen = set()
    while url:
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.netloc != 'management.azure.com' or parsed.path.lower() != urlsplit(base).path.lower() or url in seen:
            raise DeploymentError('El catalogo devolvio una pagina inesperada; no se usara un resultado parcial.')
        seen.add(url)
        page = az('rest', '--method', 'get', '--url', url)
        if not isinstance(page.get('value'), list):
            raise DeploymentError('Respuesta incompleta del catalogo regional.')
        result.extend(page['value'])
        url = page.get('nextLink')
    return result


def require_trial(subscription):
    policies = subscription.get('subscriptionPolicies') or {}
    if subscription.get('state') != 'Enabled':
        raise DeploymentError('La suscripcion no esta habilitada.')
    if policies.get('spendingLimit') != 'On':
        raise DeploymentError('No se confirmo el limite de gasto activo. No se crearan recursos.')
    if not str(policies.get('quotaId', '')).lower().startswith('freetrial'):
        raise DeploymentError('La oferta no se identifico como Free Trial. No se crearan recursos.')


def eligible(sku, region, usage):
    if sku.get('name') not in SIZES or sku.get('resourceType') != 'virtualMachines':
        return False
    if region not in sku.get('locations', []):
        return False
    for restriction in sku.get('restrictions') or []:
        if restriction.get('type') != 'Zone':
            return False
    caps = {c['name']: c['value'] for c in sku.get('capabilities', [])}
    try:
        if float(caps.get('vCPUs', 0)) != 2 or float(caps.get('MemoryGB', 0)) != 8:
            return False
    except (TypeError, ValueError):
        return False
    if caps.get('CpuArchitectureType', 'x64').lower() != 'x64':
        return False
    family = str(sku.get('family', '')).lower()
    quotas = {q.get('name', {}).get('value', '').lower(): q for q in usage}
    for name in ('cores', family):
        q = quotas.get(name)
        if q is None or q.get('limit') is None or q.get('currentValue') is None:
            return False
        try:
            limit, used = float(q['limit']), float(q['currentValue'])
        except (TypeError, ValueError):
            return False
        if not math.isfinite(limit) or not math.isfinite(used) or used < 0 or limit - used < 2:
            return False
    return True


def subscription_details(subscription_id):
    accounts = az('account', 'list')
    enabled = [a for a in accounts if a.get('state') == 'Enabled']
    if subscription_id:
        enabled = [a for a in enabled if a['id'] == subscription_id]
    if len(enabled) != 1:
        raise DeploymentError('Indicar -SuscripcionId: no hay una unica suscripcion habilitada.')
    account = enabled[0]
    subprocess.run(['az', 'account', 'set', '--subscription', account['id']], check=True)
    details = az('rest', '--method', 'get', '--url',
                 f"https://management.azure.com/subscriptions/{account['id']}?api-version=2022-12-01")
    require_trial(details)
    return account, details


def inventory(account, details, regions):
    candidates = []
    errors = []
    for region in regions:
        print('Consultando catalogo y cuota en ' + region + '...', flush=True)
        try:
            skus = regional_skus(account['id'], region)
            usage = az('vm', 'list-usage', '--location', region)
            available = [s for s in skus if eligible(s, region, usage)]
            available.sort(key=lambda s: SIZES.index(s['name']))
            for sku in available:
                candidates.append({'region': region, 'size': sku['name'], 'vcpus': 2, 'ram_gb': 8})
        except DeploymentError as error:
            print('No se completo la region ' + region + ': ' + str(error), flush=True)
            errors.append(region)
    report = {'subscription_id': account['id'], 'nombre': account['name'],
              'limite_gasto': details['subscriptionPolicies']['spendingLimit'],
              'oferta': details['subscriptionPolicies']['quotaId'], 'candidatos': candidates,
              'regiones_sin_resolver': errors,
              'alcance': 'Catalogo y cuota; no reserva capacidad fisica.'}
    (STATE / 'inventario.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['login', 'validar', 'revisar', 'plan', 'desplegar'])
    parser.add_argument('--subscription')
    parser.add_argument('--regions', default='brazilsouth,eastus2,centralus,westus3')
    args = parser.parse_args()
    if args.action == 'login':
        # La autenticacion y el segundo factor ocurren en el navegador del usuario.
        return subprocess.run(['az', 'login', '--use-device-code', '--output', 'none']).returncode
    if args.action == 'validar':
        directory = STATE / 'terraform-validation'
        directory.mkdir(exist_ok=True)
        for source in Path('/module').iterdir():
            if source.suffix in {'.tf', '.yaml'} or source.name == '.terraform.lock.hcl':
                (directory / source.name).write_bytes(source.read_bytes().replace(b'\r\n', b'\n'))
        subprocess.run(['terraform', '-chdir=' + str(directory), 'init', '-backend=false', '-input=false', '-no-color'], check=True)
        subprocess.run(['terraform', '-chdir=' + str(directory), 'validate', '-no-color'], check=True)
        subprocess.run(['bash', '-n', '/scripts/arrancar.sh'], check=True)
        print('MODULO_VALIDADO: Terraform y script de arranque; no se consulto ni creo infraestructura Azure.', flush=True)
        return 0
    account, details = subscription_details(args.subscription)
    regions = args.regions.split(',')
    if not all(r.isascii() and r.isalnum() for r in regions):
        raise DeploymentError('Nombres de region invalidos.')
    if args.action == 'revisar':
        inventory(account, details, regions)
        return 0
    return deployment(args.action, account, details, regions)


def deployment(action, account, details, regions):
    # Una suscripcion nueva puede devolver cuotas vacias antes de registrar Compute.
    # Terraform tambien necesita ambos proveedores; el registro no crea recursos.
    for namespace in ('Microsoft.Compute', 'Microsoft.Network'):
        provider = az('provider', 'show', '--namespace', namespace)
        if provider.get('registrationState') != 'Registered':
            print('Registrando proveedor ' + namespace + '...', flush=True)
            az('provider', 'register', '--namespace', namespace, '--wait', allow_empty=True)
    directory = STATE / 'terraform'
    directory.mkdir(exist_ok=True)
    for source in Path('/module').iterdir():
        if source.suffix in {'.tf', '.yaml'} or source.name == '.terraform.lock.hcl':
            (directory / source.name).write_bytes(source.read_bytes().replace(b'\r\n', b'\n'))
    config_path = STATE / 'deployment.json'
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding='utf-8'))
        if config['subscription_id'] != account['id']:
            raise DeploymentError('El estado pertenece a otra suscripcion; no se reutilizara.')
    else:
        if az('group', 'exists', '--name', 'nuevamente-demo-rg'):
            raise DeploymentError('Ya existe nuevamente-demo-rg y falta el estado local; no se importara ni reemplazara automaticamente.')
        report = inventory(account, details, regions)
        if not report['candidatos']:
            raise DeploymentError('No se encontro un perfil elegible de 2 vCPU y 8 GB con cuota suficiente.')
        candidate = report['candidatos'][0]
        image = az('vm', 'image', 'show', '--location', candidate['region'],
                   '--urn', 'Canonical:ubuntu-24_04-lts:server:latest')
        version = str(image.get('name', ''))
        if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
            raise DeploymentError('No se pudo resolver una version concreta de Ubuntu 24.04.')
        with urllib.request.urlopen('https://api.ipify.org', timeout=15) as response:
            address = ipaddress.ip_address(response.read(64).decode().strip())
        if address.version != 4 or not address.is_global:
            raise DeploymentError('No se pudo determinar la IPv4 publica para restringir SSH.')
        key = STATE / 'ssh_key'
        public = STATE / 'ssh_key.pub'
        if key.exists() != public.exists():
            raise DeploymentError('La pareja de claves SSH esta incompleta. No se regenerara automaticamente.')
        if not key.exists():
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'nuevamente-demo', '-f', str(key)], check=True)
        config = {'subscription_id': account['id'], 'location': candidate['region'], 'vm_size': candidate['size'],
                  'admin_cidr': str(address) + '/32', 'ssh_public_key': public.read_text().strip(), 'image_version': version}
        config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    (directory / 'deploy.auto.tfvars.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    print('Configuracion: ' + config['location'] + ' / ' + config['vm_size'] + ' / SSH ' + config['admin_cidr'], flush=True)
    tf = ['terraform', '-chdir=' + str(directory)]
    subprocess.run([*tf, 'init', '-input=false', '-no-color'], check=True)
    subprocess.run([*tf, 'validate', '-no-color'], check=True)
    subprocess.run([*tf, 'plan', '-input=false', '-no-color', '-out=deploy.tfplan'], check=True)
    plan = run_json([*tf, 'show', '-json', 'deploy.tfplan'])
    require_nondestructive_plan(plan)
    if action == 'plan':
        print('Plan guardado en el estado privado. No se ejecuto Apply.', flush=True)
        return 0
    # Revalidar el limite antes de consumir credito con el plan ya revisado.
    subscription_details(account['id'])
    subprocess.run([*tf, 'apply', '-input=false', '-no-color', 'deploy.tfplan'], check=True)
    outputs = {k: v['value'] for k, v in run_json([*tf, 'output', '-json']).items()}
    (STATE / 'infraestructura.json').write_text(json.dumps(outputs, indent=2), encoding='utf-8')
    upload_application(outputs)
    return 0


def require_nondestructive_plan(plan):
    if any('delete' in r.get('change', {}).get('actions', []) for r in plan.get('resource_changes', [])):
        raise DeploymentError('El plan incluye eliminaciones o reemplazos. No se aplicara automaticamente.')


def extension_host_key(view):
    instance_view = view.get('instanceView') or view.get('properties', {}).get('instanceView') or view
    # CustomScript publica stdout en statuses; otras versiones usan substatuses.
    statuses = [*(instance_view.get('statuses') or []), *(instance_view.get('substatuses') or [])]
    messages = '\n'.join(s.get('message', '') for s in statuses)
    keys = set(re.findall(r'^ssh-ed25519 ([A-Za-z0-9+/=]+)(?:\s|$)', messages, re.MULTILINE))
    if len(keys) != 1:
        raise DeploymentError('No se pudo verificar una unica clave publica SSH mediante el plano de control de Azure.')
    return 'ssh-ed25519 ' + keys.pop()


def upload_application(outputs):
    address = str(ipaddress.IPv4Address(outputs['public_ip']))
    view = az('vm', 'extension', 'show', '--resource-group', outputs['resource_group'],
              '--vm-name', outputs['vm_name'], '--name', 'ssh-host-key', '--instance-view')
    hosts = STATE / 'known_hosts'
    hosts.write_text(address + ' ' + extension_host_key(view) + '\n', encoding='utf-8')
    archive = STATE / 'aplicacion.tar.gz'
    if not archive.is_file():
        raise DeploymentError('Falta el paquete de la aplicacion.')
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='nuevamente-ssh-') as temporary:
        key = Path(temporary) / 'key'
        key.write_bytes((STATE / 'ssh_key').read_bytes())
        key.chmod(0o600)
        common = ['-i', str(key), '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(hosts),
                  '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=15', '-o', 'BatchMode=yes']
        target = 'azureuser@' + address

        def ssh(command):
            subprocess.run(['ssh', *common, target, command], check=True)

        print('Esperando a Docker en la VM...', flush=True)
        for _ in range(40):
            ready = subprocess.run(['ssh', *common, target, 'test -f /var/lib/nuevamente-docker-ready'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if ready.returncode == 0:
                break
            time.sleep(15)
        else:
            raise DeploymentError('La VM no confirmo la instalacion de Docker. Conservar el estado y revisar cloud-init.')
        ssh('umask 077; mkdir -p /home/azureuser/nuevamente /home/azureuser/.nuevamente-private/oci; '
            'chmod 700 /home/azureuser/.nuevamente-private /home/azureuser/.nuevamente-private/oci')

        def scp(source, destination):
            subprocess.run(['scp', *common, str(source), target + ':' + destination], check=True)

        scp(archive, '/home/azureuser/nuevamente/aplicacion.tar.gz')
        scp('/source-gemini.env', '/home/azureuser/.nuevamente-private/gemini.env')
        for name in ('config', 'key.pem'):
            scp('/source-oci/oci/' + name, '/home/azureuser/.nuevamente-private/oci/' + name)
        content = Path('/source-oci/oci.env').read_text(encoding='utf-8-sig')
        lines = [line for line in content.splitlines() if not line.startswith('OCI_CREDENTIALS_DIRECTORY=')]
        lines.append('OCI_CREDENTIALS_DIRECTORY=/home/azureuser/.nuevamente-private/oci')
        remote_env = Path(temporary) / 'oci.env'
        remote_env.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        remote_env.chmod(0o600)
        scp(remote_env, '/home/azureuser/.nuevamente-private/oci.env')
        ssh('chmod 600 /home/azureuser/.nuevamente-private/*.env /home/azureuser/.nuevamente-private/oci/*; '
            'cd /home/azureuser/nuevamente && '
            f"echo '{archive_hash}  aplicacion.tar.gz' | sha256sum -c - && "
            'tar -xzf aplicacion.tar.gz && bash scripts/azure/arrancar.sh')
    with urllib.request.urlopen(outputs['app_url'], timeout=30) as response:
        if response.status != 200:
            raise DeploymentError('La aplicacion no respondio HTTP 200 desde Internet.')
    print('DESPLIEGUE_AZURE_LISTO: ' + outputs['app_url'], flush=True)
    print('Falta comprobar una generacion desde la URL publica y descargar sus objetos OCI.', flush=True)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (DeploymentError, OSError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, DeploymentError) else type(error).__name__
        print('DETENIDO: ' + message, file=sys.stderr)
        raise SystemExit(1)
