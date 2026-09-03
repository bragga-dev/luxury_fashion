from luxury_fashion.apps.accounts.api.admin import (
    detail_user_router,
    list_users_router,

)


from luxury_fashion.apps.accounts.api.auth import (
    change_password_router,
    deactivate_account_router,
    delete_client_photo_router,
    me_router,
    login_router,
    logout_all_router,
    logout_router,
    google_login_router,
    list_sessions_router,
    password_reset_confirm_router,
    password_reset_request_router,
    update_profile_client_router,
    revoke_session_router,
    reactivate_user_router,
    register_router,
    refresh_router,
    resend_verification_email_router,
    delete_account_router,
    verify_email_endpoint_router,
    export_my_data_router,
    upload_client_photo_router,

)

from luxury_fashion.apps.accounts.api.address import (
    check_my_address_exists_router,
    count_my_addresses_router,
    create_my_address_router,
    deactivate_my_address_router,
    detail_my_address_router,
    get_addresses_count_for_client,
    get_my_default_address_router,
    get_my_preferential_address_router,
    activate_my_address_router,
    set_preferential_address_router,
    update_my_address_router,
    list_my_addresses_router,


)


__all__ = [

    "detail_user_router",
    "list_users_router",

    "change_password_router",
    "deactivate_account_router",
    "delete_client_photo_router",
    "me_router",
    "login_router",
    "logout_all_router",
    "logout_router",
    "google_login_router",
    "list_sessions_router",
    "password_reset_confirm_router",
    "password_reset_request_router",
    "update_profile_client_router",
    "revoke_session_router",
    "reactivate_user_router",
    "register_router",
    "refresh_router",
    "resend_verification_email_router",
    "delete_account_router",
    "verify_email_endpoint_router",
    "export_my_data_router",
    "upload_client_photo_router",
    
    "check_my_address_exists_router",
    "count_my_addresses_router",
    "create_my_address_router",
    "deactivate_my_address_router",
    "detail_my_address_router",
    "get_addresses_count_for_client",
    "get_my_default_address_router",
    "get_my_preferential_address_router",
    "activate_my_address_router",
    "set_preferential_address_router",
    "update_my_address_router",
    "list_my_addresses_router",

]