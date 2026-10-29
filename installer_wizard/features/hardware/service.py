from __future__ import annotations
import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from features.hardware import capabilities as caps_mod
from features.hardware import identify
from features.hardware.catalog import catalog
from features.hardware.expert import agent as hardware_agent
from features.hardware.model import HardwareDevice
from state import store
from config import STATE_DIR
from features.hardware.firmware import missing_for_device
from features.hardware.gpu_verification import verified_capabilities
from features.hardware.managed import ManagedDevices
from features.hardware.localization import translate
log = logging.getLogger('nuxiva.hardware')
SCAN_INTERVAL = 4.0
RETRY_AFTER = 3600.0
STICKY = {'configuring', 'error', 'awaiting_approval', 'reboot_required', 'unsupported'}

def _label(status, reason, missing):
    return translate('hardware_' + status)

class HardwareService:

    def __init__(self) -> None:
        self._devices: Dict[str, HardwareDevice] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._provisioning_tasks: Dict[str, asyncio.Task] = {}
        self._last_attempt: Dict[str, float] = {}
        self._caps_signature: str = ''
        self._kernel_log = ''
        self._last_kernel_log = 0.0
        self.managed = ManagedDevices(STATE_DIR / 'hardware_managed.json')

    @property
    def devices(self) -> List[HardwareDevice]:
        return list(self._devices.values())

    def get_device(self, device_id: str) -> Optional[HardwareDevice]:
        return self._devices.get(device_id)

    @property
    def capabilities(self) -> Dict[str, List[str]]:
        return caps_mod.aggregate(self._devices.values())

    def _from_identity(self, ident: identify.Identity) -> HardwareDevice:
        recipe = catalog.find(ident.bus, ident.vendor_id, ident.product_id)
        category = recipe.category if recipe else ident.category
        dev_id = f'{ident.bus}:{ident.vendor_id}:{ident.product_id}:{ident.sys_id}' if ident.vendor_id and ident.product_id else f'{ident.bus}:{ident.sys_id}'
        return HardwareDevice(id=dev_id, name=recipe.name if recipe else ident.display_name, vendor=ident.vendor_name or translate('hardware_unknown'), vendor_id=ident.vendor_id, product_id=ident.product_id, category=category, bus=ident.bus, driver=ident.bound_driver, interface=ident.interface, icon=identify.ICONS.get(category, ident.icon), sys_id=ident.sys_id, modalias=ident.modalias, kernel_modules=list(ident.kernel_modules))

    def _scan_linux_interfaces(self, known: List[HardwareDevice]) -> List[HardwareDevice]:

        devices: List[HardwareDevice] = []
        known_ifaces = {d.interface for d in known if d.interface}
        sys_net = Path('/sys/class/net')
        if not sys_net.exists():
            return devices
        for if_path in sys_net.iterdir():
            name = if_path.name
            if name == 'lo' or name in known_ifaces or (not (if_path / 'device').exists()):
                continue
            is_wifi = (if_path / 'wireless').exists() or (if_path / 'phy80211').exists()
            category = 'wifi' if is_wifi else 'network'
            devices.append(HardwareDevice(id=f'net:{name}', name=translate('hardware_network_interface', id=name), vendor='Linux Network Device', vendor_id='', product_id='', category=category, bus='usb' if name.startswith('wlx') else 'pci', interface=name, icon=identify.ICONS[category], status='ready', status_label='hardware_ready'))
        return devices

    def _scan_linux_bluetooth(self, known: List[HardwareDevice]) -> List[HardwareDevice]:
        devices: List[HardwareDevice] = []
        if any((d.category == 'bluetooth' for d in known)):
            return devices
        sys_bt = Path('/sys/class/bluetooth')
        if sys_bt.exists():
            for hci in sys_bt.glob('hci*'):
                devices.append(HardwareDevice(id=f'bt:{hci.name}', name=translate('hardware_bluetooth_controller', id=hci.name), vendor='Bluetooth Adapter', vendor_id='', product_id='', category='bluetooth', bus='usb', icon=identify.ICONS['bluetooth'], status='ready', status_label='hardware_ready'))
        return devices

    def _scan(self) -> List[HardwareDevice]:
        if os.name == 'nt':
            return []
        identities = identify.scan_all()
        primary = [self._from_identity(i) for i in identities]
        all_devs = primary + self._scan_linux_interfaces(primary)
        all_devs += self._scan_linux_bluetooth(all_devs)
        for dev in all_devs:
            if dev.id.startswith(('net:', 'bt:')):
                dev.capabilities = caps_mod.capabilities_for(dev.category, 'ready')
                continue
            status, pkgs, missing_fw = hardware_agent.diagnose(dev)
            dev.status = status
            dev.required_packages = pkgs
            dev.missing_firmware = missing_fw
            dev.status_label = _label(status, dev.details.get('reason', ''), missing_fw)
            dev.capabilities = caps_mod.capabilities_for(dev.category, status, dev.details.get('extra_capabilities', []))
        return all_devs

    async def scan(self) -> List[HardwareDevice]:
        devices = await asyncio.to_thread(self._scan)
        if os.name != 'nt' and time.monotonic() - self._last_kernel_log >= 30:
            code, output = await hardware_agent._run_cmd(['dmesg', '--raw'], timeout=10)
            self._kernel_log = output if code == 0 else ''
            self._last_kernel_log = time.monotonic()
        for device in devices:
            missing = missing_for_device(self._kernel_log, device, hardware_agent._firmware_exists)
            if missing:
                device.missing_firmware = missing[0]
                device.details['kernel_missing_firmware'] = missing
                hardware_agent._set_status(device, 'needs_driver')
            if device.status == 'ready' and device.category == 'gpu':
                extra = await verified_capabilities(device, hardware_agent._run_cmd)
                device.details['extra_capabilities'] = extra
                device.capabilities = caps_mod.capabilities_for(device.category, device.status, extra)
        return devices

    def _merge(self, current_map: Dict[str, HardwareDevice]) -> None:

        for dev_id, new in list(current_map.items()):
            old = self._devices.get(dev_id)
            if old is None:
                continue
            new.details = {**old.details, **new.details}
            new.steps = old.steps
            new.connected_at = old.connected_at
            if old.status == 'awaiting_approval' and old.details.get('update_approval_required'):
                current_map[dev_id] = old
                continue
            if old.status in STICKY and new.status != 'ready':
                old.driver = new.driver
                old.interface = new.interface or old.interface
                old.kernel_modules = new.kernel_modules
                current_map[dev_id] = old
            elif old.status == 'configuring':
                current_map[dev_id] = old

    def _publish_capabilities(self) -> None:
        caps = self.capabilities
        signature = repr(sorted(((k, sorted(v)) for k, v in caps.items())))
        if signature == self._caps_signature:
            return
        self._caps_signature = signature
        from nuxiva_bus import nuxiva_bus
        try:
            nuxiva_bus.publish('hardware.capabilities', {'capabilities': caps}, origin='hardware', retain=True)
        except Exception as exc:
            log.error("Capacita' hardware non pubblicate: %s", exc)

    def _update_due(self, device_id):
        try:
            return self.managed.due(device_id)
        except (OSError, ValueError) as exc:
            log.error("Managed update registry unavailable: %s", exc)
            return False

    def _may_attempt(self, dev_id: str) -> bool:
        return time.time() - self._last_attempt.get(dev_id, 0.0) >= RETRY_AFTER

    async def _provision_task(self, dev: HardwareDevice, approve: bool=False, refresh: bool=False) -> None:
        self._last_attempt[dev.id] = time.time()
        try:
            ok = await hardware_agent.provision(dev, approve=approve, refresh=refresh)
            if ok and self._devices.get(dev.id) is dev:
                self.managed.record(dev)
        except Exception:
            hardware_agent._set_status(dev, 'error')
            log.exception('Hardware provisioning task failed: %s', dev.id)
        finally:
            if self._provisioning_tasks.get(dev.id) is asyncio.current_task():
                self._provisioning_tasks.pop(dev.id, None)
            self._publish_capabilities()
            store.touch()

    def start_provisioning(self, dev: HardwareDevice, approve: bool=False, refresh: bool=False) -> bool:

        task = self._provisioning_tasks.get(dev.id)
        if task and (not task.done()):
            return False
        hardware_agent._set_status(dev, 'configuring')
        self._publish_capabilities()
        self._provisioning_tasks[dev.id] = asyncio.create_task(self._provision_task(dev, approve, refresh))
        return True

    async def refresh(self) -> List[HardwareDevice]:
        async with self._lock:
            previous_map = self._devices
            current_list = await self.scan()
            current_map = {d.id: d for d in current_list}
            added_ids = set(current_map.keys()) - set(self._devices.keys())
            removed_ids = set(self._devices.keys()) - set(current_map.keys())
            self._merge(current_map)
            from features.desktop.desk import desk
            from nuxiva_bus import nuxiva_bus
            self._devices = current_map
            for dev_id in added_ids:
                dev = current_map[dev_id]
                store.event('INFO', f'Dispositivo connesso: {dev.name}', 'hardware')
                desk.show('notice', {'icon': dev.icon, 'title': translate('hardware_connected'), 'text': dev.name}, key=f'hw:{dev.id}', ttl=30)
                try:
                    nuxiva_bus.publish('ui.notification.notice', {'labelKey': 'os_device_connected', 'device': dev.brief()}, origin='hardware')
                except Exception as exc:
                    log.error('Notifica connessione non pubblicata: %s', exc)
            for dev_id, dev in current_map.items():
                if dev.status in ('needs_driver', 'error') and self._may_attempt(dev_id):
                    log.info('Dispositivo da configurare: %s (%s), avvio agente esperto', dev.name, dev.status)
                    self.start_provisioning(dev)
                elif dev.status == 'ready' and self._may_attempt(dev_id) and self._update_due(dev_id):
                    self.start_provisioning(dev, refresh=True)
            for dev_id in removed_ids:
                old_dev = previous_map[dev_id]
                store.event('INFO', f'Dispositivo scollegato: {old_dev.name}', 'hardware')
                desk.show('notice', {'icon': '🔌', 'title': translate('hardware_disconnected'), 'text': old_dev.name}, key=f'hw:{dev_id}', ttl=15)
                try:
                    nuxiva_bus.publish('ui.notification.notice', {'labelKey': 'os_device_disconnected', 'device': old_dev.brief()}, origin='hardware')
                except Exception as exc:
                    log.error('Notifica disconnessione non pubblicata: %s', exc)
                task = self._provisioning_tasks.pop(dev_id, None)
                if task:
                    task.cancel()
                self._last_attempt.pop(dev_id, None)
            if added_ids or removed_ids:
                store.touch()
            self._devices = current_map
            self._publish_capabilities()
            return list(self._devices.values())

    async def run(self) -> None:
        self._running = True
        log.info('Servizio monitoraggio hardware e agente driver avviato')
        while self._running:
            try:
                await self.refresh()
            except Exception as exc:
                log.warning('Ciclo monitoraggio hardware non riuscito: %s', exc)
            await asyncio.sleep(SCAN_INTERVAL)
hardware_service = HardwareService()
