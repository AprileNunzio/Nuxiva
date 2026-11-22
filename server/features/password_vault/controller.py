from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from server.features.password_vault.models import (
    SecretCategory,
    VaultEntryCreate,
    VaultEntryMetadata,
    VaultEntryRevealed,
    VaultStatusResponse,
    VaultUnlockRequest,
)
from server.features.password_vault.vault_service import password_vault_service

vault_router = APIRouter(prefix="/vault", tags=["password_vault"])


@vault_router.get("/generate-password")
async def generate_password(
    length: int = Query(20, ge=12, le=64),
    symbols: bool = Query(True),
) -> Dict[str, str]:
    return {"password": password_vault_service.generate_strong_password(length=length, include_symbols=symbols)}


@vault_router.get("/{user_id}/status", response_model=VaultStatusResponse)
async def get_vault_status(user_id: str) -> VaultStatusResponse:
    return password_vault_service.get_status(user_id)


@vault_router.post("/{user_id}/unlock", response_model=VaultStatusResponse)
async def unlock_vault(user_id: str, payload: VaultUnlockRequest) -> VaultStatusResponse:
    try:
        return password_vault_service.unlock_or_initialize(
            user_id=user_id,
            master_password=payload.master_password,
            ttl_seconds=payload.ttl_seconds,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@vault_router.post("/{user_id}/lock", response_model=VaultStatusResponse)
async def lock_vault(user_id: str) -> VaultStatusResponse:
    return password_vault_service.lock(user_id)


@vault_router.get("/{user_id}/entries", response_model=List[VaultEntryMetadata])
async def list_vault_entries(
    user_id: str,
    category: Optional[SecretCategory] = Query(None),
    q: Optional[str] = Query(None),
) -> List[VaultEntryMetadata]:
    return password_vault_service.list_entries(user_id=user_id, category=category, query=q)


@vault_router.post("/{user_id}/entries", response_model=VaultEntryMetadata)
async def add_vault_entry(user_id: str, payload: VaultEntryCreate) -> VaultEntryMetadata:
    try:
        return password_vault_service.add_entry(user_id=user_id, payload=payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@vault_router.post("/{user_id}/entries/{entry_id}/reveal", response_model=VaultEntryRevealed)
async def reveal_vault_entry(user_id: str, entry_id: str) -> VaultEntryRevealed:
    try:
        return password_vault_service.reveal_entry(user_id=user_id, entry_id=entry_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@vault_router.delete("/{user_id}/entries/{entry_id}")
async def delete_vault_entry(user_id: str, entry_id: str) -> Dict[str, bool]:
    try:
        deleted = password_vault_service.delete_entry(user_id=user_id, entry_id=entry_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Voce non trovata.")
    return {"deleted": True}
