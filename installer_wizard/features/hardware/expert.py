from __future__ import annotations
import asyncio
import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
from features.hardware.activation import activate
from features.hardware.execution import run_command
from features.hardware.modules import load_module
from features.hardware.packages import PackageOperations
from features.hardware.pipeline import provision_pipeline
from features.hardware.validation import firmware_path
from features.hardware import capabilities as caps_mod
from features.hardware import identify
from features.hardware.accelerators import GpuPlan, plan_gpu, has_graphical_session
from features.hardware.catalog import Recipe, catalog
from features.hardware.dkms import DkmsBroker
from features.hardware.model import HardwareDevice
from features.hardware.repos import RepoManager
from state import store
from features.hardware.localization import translate
log = logging.getLogger('nuxiva.hardware.expert')
BOUND_REQUIRED = {'wifi', 'bluetooth', 'network', 'gpu', 'audio', 'camera', 'serial', 'accelerator', 'platform', 'printer', 'storage', 'input'}
BLACKLIST_DIR = Path(os.environ.get('NUXIVA_MODPROBE_DIR', '/run/modprobe.d'))

@dataclass
class Assessment:

    status: str = 'ready'
    packages: List[str] = field(default_factory=list)
    repos: List[str] = field(default_factory=list)
    missing_firmware: List[str] = field(default_factory=list)
    reason: str = ''
    recipe: Optional[Recipe] = None
    gpu: Optional[GpuPlan] = None

class HardwareAgent(PackageOperations):

    def __init__(self) -> None:
        self._pkg_manager: Optional[str] = None
        self._lock = asyncio.Lock()
        self._repos: Optional[RepoManager] = None
        self._dkms: Optional[DkmsBroker] = None

    def detect_pkg_manager(self) -> str:
        if self._pkg_manager:
            return self._pkg_manager
        if shutil.which('apt-get'):
            self._pkg_manager = 'apt'
        elif shutil.which('dnf'):
            self._pkg_manager = 'dnf'
        elif shutil.which('yum'):
            self._pkg_manager = 'yum'
        elif shutil.which('zypper'):
            self._pkg_manager = 'zypper'
        elif shutil.which('pacman'):
            self._pkg_manager = 'pacman'
        else:
            self._pkg_manager = 'generic'
        return self._pkg_manager

    @property
    def repos(self) -> RepoManager:
        if self._repos is None:
            self._repos = RepoManager(self._run_cmd)
        return self._repos

    @property
    def dkms(self) -> DkmsBroker:
        if self._dkms is None:
            self._dkms = DkmsBroker(self._run_cmd, self.install_packages)
        return self._dkms

    async def _run_cmd(self, cmd, timeout=180, env=None):
        return await run_command(cmd, timeout, env)

    async def _scan_dmesg_missing_firmware(self) -> List[str]:
        missing: List[str] = []
        code, out = await self._run_cmd(['dmesg'], timeout=10)
        if code == 0:
            for line in out.splitlines()[-300:]:
                m = re.search('(?:failed to load|Direct firmware load for)\\s+([a-zA-Z0-9_\\-\\./]+)', line)
                if m:
                    fw_name = m.group(1)
                    fw_name = re.sub('^/?(?:usr/)?(?:lib/)?firmware/', '', fw_name)
                    if fw_name not in missing and (not self._firmware_exists(fw_name)):
                        missing.append(fw_name)
        return missing

    @staticmethod
    def _firmware_exists(name: str) -> bool:
        if not firmware_path(name):
            return False
        for base in ('/lib/firmware', '/usr/lib/firmware'):
            p = Path(base) / name
            if p.exists() or Path(str(p) + '.zst').exists() or Path(str(p) + '.xz').exists():
                return True
        return False

    def _assess(self, device: HardwareDevice) -> Assessment:
        detected = self.detect_pkg_manager()
        pm = detected
        a = Assessment()
        a.recipe = catalog.find(device.bus, device.vendor_id, device.product_id)
        if device.bus == 'pci' and device.category in ('gpu', 'accelerator'):
            ident = identify.Identity(bus='pci', sys_id=device.sys_id, vendor_id=device.vendor_id, product_id=device.product_id, bound_driver=device.driver)
            gp = plan_gpu(ident, pm, distro_family=self.repos.os_info.family)
            if gp is not None:
                a.gpu = gp
                a.packages, a.repos, a.status, a.reason = (gp.packages, gp.repos, gp.status, gp.reason)
                device.details.pop('extra_capabilities', None)
                for firmware in device.details.get('kernel_missing_firmware', []):
                    if firmware_path(firmware) and (not self._firmware_exists(firmware)):
                        a.missing_firmware.append(firmware)
                        a.packages.extend((p for p in catalog.firmware_packages(firmware, pm, self.repos.os_info.family) if p not in a.packages))
                if a.missing_firmware and a.status == 'ready':
                    a.status = 'needs_driver'
                return a
        if a.recipe:
            a.packages = a.recipe.packages_for(pm, self.repos.os_info.family)
            a.repos = list(a.recipe.repos)
            missing = [f for f in a.recipe.firmware if not self._firmware_exists(f)]
        else:
            a.packages = catalog.category_packages(device.category, pm, self.repos.os_info.family)
            a.repos = list(catalog.category(device.category).get('repos', []))
            missing = []
        for firmware in device.details.get('kernel_missing_firmware', []):
            if firmware_path(firmware) and (not self._firmware_exists(firmware)) and (firmware not in missing):
                missing.append(firmware)
                for package in catalog.firmware_packages(firmware, pm, self.repos.os_info.family):
                    if package not in a.packages:
                        a.packages.append(package)
        a.missing_firmware = missing
        needs = False
        if missing:
            needs, a.reason = (True, f'Firmware mancante: {missing[0]}')
        tools = catalog.category(device.category).get('tools', [])
        if device.category == 'wifi':
            if not shutil.which('nmcli') and (not shutil.which('iw')):
                needs, a.reason = (True, a.reason or 'Strumenti Wi-Fi mancanti')
        elif tools and (not any((shutil.which(t) for t in tools))):
            needs, a.reason = (True, a.reason or f"Strumenti mancanti: {', '.join(tools)}")
        if (device.modalias or device.sys_id) and device.category in BOUND_REQUIRED and (not device.driver) and (not device.interface):
            if device.kernel_modules:
                needs, a.reason = (True, a.reason or f'Modulo {device.kernel_modules[0]} disponibile ma non caricato')
            elif a.recipe and a.recipe.dkms:
                needs, a.reason = (True, a.reason or 'Driver esterno al kernel: serve DKMS')
            else:
                a.status = 'unsupported'
                a.reason = 'Nessun driver noto nel kernel in uso né nel catalogo'
                return a
        if needs and detected == 'generic':
            a.status, a.reason = ('unsupported', 'No supported package manager')
            return a
        if device.category in ('wifi', 'network') and device.driver and not device.interface:
            needs, a.reason = True, 'Kernel network interface unavailable'
        a.status = 'needs_driver' if needs else 'ready'
        return a

    def diagnose(self, device: HardwareDevice) -> Tuple[str, List[str], Optional[str]]:
        a = self._assess(device)
        device.details['reason'] = a.reason
        if a.gpu:
            device.details['gpu_plan'] = a.gpu.to_dict()
        return (a.status, a.packages, a.missing_firmware[0] if a.missing_firmware else None)

    async def load_module_safely(self, module: str) -> Tuple[bool, str]:
        return await load_module(module, self._run_cmd, BLACKLIST_DIR)

    async def activate_device(self, device: HardwareDevice) -> bool:
        return await activate(device, self._run_cmd)

    def _rebind(self, device: HardwareDevice) -> Optional[identify.Identity]:

        if not device.sys_id:
            return None
        try:
            for ident in identify.scan_all():
                if ident.bus == device.bus and ident.sys_id == device.sys_id:
                    device.driver = ident.bound_driver
                    device.interface = ident.interface or device.interface
                    return ident
        except OSError as exc:
            log.error('Rilettura sysfs non riuscita: %s', exc)
        return None

    def _set_status(self, device: HardwareDevice, status: str) -> None:
        device.status = status
        device.status_label = 'hardware_' + status
        device.capabilities = caps_mod.capabilities_for(device.category, status, device.details.get('extra_capabilities', []))

    def _notify(self, device: HardwareDevice, ttl: int, label_key: str) -> None:
        from features.desktop.desk import desk
        from nuxiva_bus import nuxiva_bus
        desk.show('notice', {'icon': device.icon, 'title': translate('hardware_setup'), 'text': translate('hardware_notice', device=device.name, status=translate('hardware_' + device.status))}, key=f'hw:{device.id}', ttl=ttl)
        try:
            nuxiva_bus.publish('ui.notification.notice', {'labelKey': label_key, 'device': device.brief()}, origin='hardware')
        except Exception as exc:
            log.error('Notifica bus non pubblicata: %s', exc)

    async def provision(self, device: HardwareDevice, approve: bool=False, refresh: bool=False) -> bool:
        async with self._lock:
            a = self._assess(device)
            device.required_packages = a.packages
            device.missing_firmware = a.missing_firmware[0] if a.missing_firmware else None
            device.details['reason'] = a.reason
            if a.gpu:
                device.details['gpu_plan'] = a.gpu.to_dict()
            if refresh and a.gpu and not approve and await asyncio.to_thread(has_graphical_session):
                device.details['update_approval_required'] = True
                self._set_status(device, 'awaiting_approval')
                return False
            device.details.pop('update_approval_required', None)
            if a.status == 'ready' and (not refresh):
                self._set_status(device, 'ready')
                return True
            if a.status == 'unsupported':
                self._set_status(device, 'unsupported')
                device.add_step('diagnosi', 'ricerca driver', False, a.reason)
                return False
            if a.status == 'awaiting_approval' and (not approve):
                self._set_status(device, 'awaiting_approval')
                device.add_step('diagnosi', 'driver proprietario', False, a.reason)
                self._notify(device, 120, 'os_device_approval')
                return False
            self._set_status(device, 'configuring')
            store.event('INFO', f'Agente Hardware: Avvio installazione driver per {device.name} ({a.reason})', 'hardware')
            self._notify(device, 60, 'os_device_configuring')
            try:
                ok = await self._pipeline(device, a)
            except (OSError, ValueError) as exc:
                log.exception('Provisioning %s fallito', device.name)
                device.add_step('pipeline', 'errore imprevisto', False, str(exc))
                self._set_status(device, 'error')
                ok = False
            store.touch()
            if ok and device.status == 'ready':
                store.event('INFO', f"Agente Hardware: {device.name} configurato e pronto all'uso", 'hardware')
                self._notify(device, 15, 'os_device_ready')
            elif ok and device.status == 'reboot_required':
                store.event('INFO', f'Agente Hardware: {device.name} richiede un riavvio', 'hardware')
                self._notify(device, 60, 'os_device_reboot')
            else:
                self._notify(device, 30, 'os_device_error')
            return ok

    async def _pipeline(self, device, assessment):
        return await provision_pipeline(self, device, assessment)
agent = HardwareAgent()
