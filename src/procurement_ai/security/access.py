"""Access scope and row-level authorization helpers.

The open-ended agent is the primary read path. Restricted users (currently the
``specialist`` role by default) receive department-scoped data access. Global
read roles can query across departments. This is an application-layer control;
production deployments should also enforce PostgreSQL row-level security with a
dedicated read-only role.
"""

from dataclasses import dataclass
from uuid import UUID

from procurement_ai.config.settings import get_settings


def _global_roles() -> set[str]:
    raw = get_settings().row_level_global_roles
    return {role.strip().lower() for role in raw.split(",") if role.strip()}


@dataclass(frozen=True)
class AccessScope:
    user_id: str | None
    role: str
    department_id: str | None = None
    can_read_all: bool = True

    @property
    def restricted(self) -> bool:
        return not self.can_read_all

    @property
    def department_uuid(self) -> UUID | None:
        if not self.department_id:
            return None
        try:
            return UUID(self.department_id)
        except (ValueError, TypeError):
            return None

    def allows_department(self, department_id: str | UUID | None) -> bool:
        if self.can_read_all:
            return True
        if not self.department_id or department_id is None:
            return False
        return str(department_id) == str(self.department_id)


def build_access_scope(
    user_id: str | None,
    role: str | None,
    department_id: str | None,
    *,
    enabled: bool | None = None,
) -> AccessScope:
    settings = get_settings()
    active = settings.row_level_access_enabled if enabled is None else enabled
    normalized_role = (role or "").lower()
    can_read_all = (not active) or normalized_role in _global_roles()
    return AccessScope(
        user_id=user_id,
        role=normalized_role or "unknown",
        department_id=department_id,
        can_read_all=can_read_all,
    )


def scope_from_state(state: dict) -> AccessScope:
    return build_access_scope(
        state.get("user_id"),
        state.get("user_role"),
        state.get("department_id"),
    )
