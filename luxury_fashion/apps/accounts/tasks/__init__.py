# luxury_fashion/luxury_fashion/apps/accounts/tasks/__init__.py
from luxury_fashion.apps.accounts.tasks.verification_account import send_verification_email
from luxury_fashion.apps.accounts.tasks.password_reset import send_password_reset_email
from luxury_fashion.apps.accounts.tasks.account_notifications import (
    send_account_deleted_email,
    send_account_status_email,
    send_password_changed_email,
    send_welcome_email,
)


__all__ = [
    "send_verification_email",
    "send_password_reset_email",
    "send_welcome_email",
    "send_password_changed_email",
    "send_account_deleted_email",
    "send_account_status_email",
]