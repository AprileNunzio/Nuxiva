import os
import json
import time
from typing import Dict, List, Optional
from server.config.env import settings
from server.core.security_guard.rbac_models import (
    UserAccount,
    TenancyProfile,
    SystemRole,
    ResourcePermission,
    ROLE_PERMISSIONS_MATRIX,
)

class RBACService:
    _instance = None

    def __new__(cls) -> "RBACService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._users_file = os.path.join(settings.DATA_DIR, "rbac_users.json")
            cls._instance._users: Dict[str, UserAccount] = {}
            cls._instance._load_users()
        return cls._instance

    def _load_users(self) -> None:
        if os.path.exists(self._users_file):
            try:
                with open(self._users_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for u_dict in data:
                        account = UserAccount(**u_dict)
                        self._users[account.user_id] = account
                return
            except Exception:
                pass
        
        # Inizializza utente principale in modo universale da configurazione o default di sistema
        username = settings.NUXIVA_USER_NAME.strip().lower() or "admin"
        display = settings.NUXIVA_USER_NAME.strip().title() if settings.NUXIVA_USER_NAME else "Account Amministratore"
        default_owner = UserAccount(
            user_id="user_primary",
            username=username,
            display_name=display,
            profile=TenancyProfile.HOME,
            role=SystemRole.OWNER_ADMIN,
            created_at=time.time(),
        )
        self._users[default_owner.user_id] = default_owner
        self._save_users()

    def _save_users(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._users_file), exist_ok=True)
            with open(self._users_file, "w", encoding="utf-8") as f:
                json.dump([u.model_dump() for u in self._users.values()], f, indent=2)
        except Exception:
            pass

    def get_user(self, user_id: str) -> Optional[UserAccount]:
        return self._users.get(user_id)

    def list_users(self) -> List[UserAccount]:
        return list(self._users.values())

    def upsert_user(self, user: UserAccount) -> UserAccount:
        if not user.created_at:
            user.created_at = time.time()
        self._users[user.user_id] = user
        self._save_users()
        return user

    def delete_user(self, user_id: str) -> bool:
        if user_id in self._users and user_id != "user_primary":
            del self._users[user_id]
            self._save_users()
            return True
        return False

    def has_permission(
        self,
        user_id: str,
        permission: ResourcePermission,
        project_id: Optional[str] = None,
    ) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False

        # Superadmin e Owner hanno permessi globali illimitati
        if user.role in {SystemRole.SUPERADMIN, SystemRole.OWNER_ADMIN}:
            return True

        # Controllo permessi specifici del ruolo
        role_perms = ROLE_PERMISSIONS_MATRIX.get(user.role, set())
        has_perm = (permission in role_perms) or (permission in user.custom_permissions)

        if not has_perm:
            return False

        # Se il permesso richiede che il progetto sia assegnato
        if permission in {
            ResourcePermission.PROJECTS_VIEW_ASSIGNED,
            ResourcePermission.PROJECTS_EDIT,
            ResourcePermission.WAR_ROOM_POST,
        }:
            if project_id and project_id not in user.assigned_projects:
                # Controlla se il ruolo ha accesso a tutti i progetti
                if ResourcePermission.PROJECTS_VIEW_ALL in role_perms:
                    return True
                return False

        return True

rbac_service = RBACService()
