import asyncio
import re
import shutil
from state import store
from features.hardware.gpu_verification import verified_capabilities
from features.hardware.catalog import catalog
from features.hardware.binding import reprobe
BOUND_REQUIRED = {'wifi', 'bluetooth', 'network', 'gpu', 'audio', 'camera', 'serial', 'accelerator', 'platform', 'printer', 'storage', 'input'}

async def execute_pipeline(self, device, a):
    pm = self.detect_pkg_manager()
    if a.repos:
        repo = await self.repos.ensure(a.repos, pm)
        if repo.changed:
            device.details['repo_backups'] = repo.backups
        device.add_step('repository', 'abilitazione ' + ','.join(a.repos), repo.ok, f"abilitati: {repo.enabled or '-'}; gia' presenti: {repo.already or '-'}; {'; '.join(repo.notes)}")
        if not repo.ok:
            self._set_status(device, 'error')
            return False
    if a.gpu and a.gpu.extra_repos:
        device.add_step('repository', 'repository di terze parti', True, ', '.join(a.gpu.extra_repos))
    code, out = await self.update_packages()
    device.add_step('pacchetti', 'aggiornamento indici', code == 0, out[-150:] if code else '')
    if code:
        self._set_status(device, 'error')
        return False
    packages = list(a.packages)
    for fw in [device.missing_firmware] if device.missing_firmware else []:
        extra = catalog.firmware_packages(fw, pm, self.repos.os_info.family)
        device.add_step('firmware', f'richiesto dal kernel: {fw}', bool(extra), ', '.join(extra))
        packages.extend((p for p in extra if p not in packages))
    packages, skipped = await self.filter_available(packages)
    if skipped:
        device.add_step('pacchetti', 'non disponibili nei repository', False, ', '.join(skipped))
    device.required_packages = packages
    if a.packages and (not packages) or any((p.endswith('-dkms') or p.startswith(('akmod-', 'nvidia-driver')) for p in skipped)):
        self._set_status(device, 'error')
        return False
    wants_dkms_pkg = any((p.endswith('-dkms') or p.startswith('akmod-') for p in packages))
    wants_dkms_src = bool(a.recipe and a.recipe.dkms and (not device.kernel_modules))
    if wants_dkms_pkg or wants_dkms_src:
        ok, msg = await self.dkms.ensure_toolchain(pm, self.repos.os_info.family)
        device.add_step('dkms', 'toolchain e header kernel', ok, msg)
        if not ok:
            self._set_status(device, 'error')
            return False
    if packages:
        code, out = await self.install_packages(packages)
        device.add_step('pacchetti', 'installazione ' + ', '.join(packages[:6]), code == 0, out[-200:] if code else '')
        if code != 0:
            self._set_status(device, 'error')
            store.event('WARN', f'Agente Hardware: Errore installazione driver per {device.name}: {out[-200:]}', 'hardware')
            return False
    if a.gpu and a.gpu.selection_required:
        code, output = await self._run_cmd(['ubuntu-drivers', 'devices'], timeout=60)
        selected = ''
        for block in output.split('== '):
            if block.splitlines() and device.sys_id and (device.sys_id in block.splitlines()[0]):
                for line in block.splitlines():
                    match = re.search('driver\\s*:\\s*(nvidia-driver-[0-9]+(?:-server)?(?:-open)?)\\s+-.*recommended', line)
                    if match:
                        selected = match[1]
        if code or not selected:
            self._set_status(device, 'unsupported')
            return False
        code, output = await self.install_packages([selected])
        device.add_step('gpu', selected, code == 0, output[-200:])
        if code:
            self._set_status(device, 'error')
            return False
        device.required_packages.append(selected)
    modules = list(device.kernel_modules) or (list(a.recipe.modules) if a.recipe else [])
    if wants_dkms_src and a.recipe and a.recipe.dkms:
        res = await self.dkms.install_from_git(a.recipe.dkms)
        device.add_step('dkms', 'compilazione ' + a.recipe.dkms.get('module', ''), res.ok, res.message)
        if not res.ok:
            self._set_status(device, 'error')
            return False
        modules = [res.module] + modules
    for mod in modules[:1]:
        ok, note = await self.load_module_safely(mod)
        device.add_step('kernel', f'modprobe {mod}', ok, note)
        if not ok:
            self._set_status(device, 'error')
            return False
    if device.sys_id and not device.driver:
        await asyncio.to_thread(reprobe, device)
        self._rebind(device)
    if not await self.activate_device(device):
        self._set_status(device, 'error')
        return False
    extra = []
    if a.gpu and a.gpu.verify and shutil.which(a.gpu.verify[0]):
        code, out = await self._run_cmd(a.gpu.verify, timeout=30)
        device.add_step('verifica', ' '.join(a.gpu.verify), code == 0, out[-150:])
        if code == 0 and a.gpu.capability and (a.gpu.capability != 'compute.accelerator'):
            extra.append(a.gpu.capability)
    device.details['extra_capabilities'] = extra
    ident = self._rebind(device)
    if device.sys_id and ident is None:
        self._set_status(device, 'error')
        return False
    if a.gpu and a.gpu.reboot and (not extra):
        driver_ok = set((catalog.gpu_vendor(device.vendor_id) or {}).get('driver_ok', []))
        if not (ident and ident.bound_driver in driver_ok):
            self._set_status(device, 'reboot_required')
            return True
    if a.gpu and ident and (ident.bound_driver not in set((catalog.gpu_vendor(device.vendor_id) or {}).get('driver_ok', []))):
        self._set_status(device, 'error')
        return False
    if device.category in BOUND_REQUIRED and (not (ident and (ident.bound_driver or ident.interface) or (not device.sys_id and (device.driver or device.interface)))):
        self._set_status(device, 'error')
        return False
    if device.category in ('wifi', 'network') and not device.interface:
        self._set_status(device, 'error')
        return False
    if device.missing_firmware and (not self._firmware_exists(device.missing_firmware)):
        self._set_status(device, 'error')
        return False
    device.details['extra_capabilities'] = await verified_capabilities(device, self._run_cmd)
    self._set_status(device, 'ready')
    return True

async def provision_pipeline(agent, device, assessment):
    device.details.pop('repo_backups', None)
    before = len(device.steps)
    try:
        ok = await execute_pipeline(agent, device, assessment)
    except BaseException:
        backups = device.details.pop('repo_backups', [])
        if backups:
            restored = agent.repos.restore(backups)
            device.add_step('rollback', 'repositories', len(restored) == len(backups))
        raise
    if not ok:
        backups = device.details.pop('repo_backups', [])
        if backups:
            restored = agent.repos.restore(backups)
            device.add_step('rollback', 'repositories', len(restored) == len(backups))
    device.details['last_operation_steps'] = len(device.steps) - before
    return ok
