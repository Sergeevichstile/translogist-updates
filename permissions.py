"""
Permission system for multi-user access control.
Owner can set per-user permissions.
"""

DEFAULT_PERMISSIONS = {
    "view_finances":   True,
    "view_profit":     True,
    "add_trips":       True,
    "edit_trips":      True,
    "delete_trips":    True,
    "manage_trucks":   True,
    "manage_drivers":  True,
    "manage_docs":     True,
    "view_reports":    True,
    "manage_users":    False,  # Only owner
}

OWNER_PERMISSIONS = {k: True for k in DEFAULT_PERMISSIONS}
OWNER_PERMISSIONS["manage_users"] = True

PERMISSION_LABELS = {
    "view_finances":  "Просмотр финансов",
    "view_profit":    "Видеть прибыль компании",
    "add_trips":      "Добавлять рейсы",
    "edit_trips":     "Редактировать рейсы",
    "delete_trips":   "Удалять рейсы",
    "manage_trucks":  "Управлять фурами",
    "manage_drivers": "Управлять водителями",
    "manage_docs":    "Работать с документами",
    "view_reports":   "Просматривать отчёты",
    "manage_users":   "Управлять пользователями",
}


class PermissionManager:
    def __init__(self, session):
        self.session   = session
        self.role      = session.get("role", "employee")
        self._perms    = OWNER_PERMISSIONS.copy() if self.role == "owner" else DEFAULT_PERMISSIONS.copy()
        self._custom   = session.get("permissions", {})
        if self._custom:
            self._perms.update(self._custom)

    def can(self, permission: str) -> bool:
        if self.role == "owner":
            return True
        return self._perms.get(permission, False)

    def is_owner(self) -> bool:
        return self.role == "owner"
