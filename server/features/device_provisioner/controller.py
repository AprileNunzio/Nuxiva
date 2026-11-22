from typing import List
from fastapi import APIRouter

from server.features.device_provisioner.models import (
    DebianProbeRequest,
    DebianProvisionRequest,
    Esp32ProvisionRequest,
    ProvisionJobResult,
    SerialPortCandidate,
)
from server.features.device_provisioner.esp32_provisioner import discover_serial_ports, esp32_provisioner
from server.features.device_provisioner.debian_provisioner import debian_provisioner

provisioner_router = APIRouter(prefix="/provisioner", tags=["device_provisioner"])
_recent_jobs: List[ProvisionJobResult] = []


def _record_job(res: ProvisionJobResult) -> ProvisionJobResult:
    _recent_jobs.insert(0, res)
    del _recent_jobs[30:]
    return res


@provisioner_router.get("/esp32/ports", response_model=List[SerialPortCandidate])
async def list_esp32_serial_ports() -> List[SerialPortCandidate]:
    return discover_serial_ports()


@provisioner_router.post("/esp32/install", response_model=ProvisionJobResult)
async def install_esp32_firmware(payload: Esp32ProvisionRequest) -> ProvisionJobResult:
    return _record_job(await esp32_provisioner.provision(payload))


@provisioner_router.post("/debian/probe", response_model=ProvisionJobResult)
async def probe_debian_server(payload: DebianProbeRequest) -> ProvisionJobResult:
    return _record_job(await debian_provisioner.probe(payload))


@provisioner_router.post("/debian/install", response_model=ProvisionJobResult)
async def install_debian_server(payload: DebianProvisionRequest) -> ProvisionJobResult:
    return _record_job(await debian_provisioner.provision(payload))


@provisioner_router.get("/jobs", response_model=List[ProvisionJobResult])
async def list_provision_jobs() -> List[ProvisionJobResult]:
    return list(_recent_jobs)
