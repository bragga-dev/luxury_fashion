__all__ = [
    # Por ID
    'get_client_by_id',
    'get_client_or_404',
    'get_client_by_user_id',
    
    # Por Username
    'get_client_by_username',
    'get_clients_by_username_partial',
    
    # Por Nome
    'get_clients_by_first_name',
    'get_clients_by_last_name',
    'get_clients_by_full_name',
    
    # Por Email
    'get_client_by_email',
    'get_clients_by_email_partial',
    
    # Por Telefone
    'get_client_by_phone',
    'get_clients_by_phone_partial',
    'normalize_phone_for_search',
    
    # Por Data de Nascimento
    'get_clients_by_birth_date',
    'get_clients_by_birth_date_range',
    'get_clients_with_birthday_today',
    'get_clients_with_birthday_in_month',
    
    # Por Gênero
    'get_clients_by_gender',
    'get_gender_statistics',
    
    # Buscas combinadas
    'search_clients',
    'get_clients_by_name_and_username',
    
    # Filtros avançados
    'filter_clients',
        
    # Utilitários
    'validate_client_exists',
    'get_client_full_name_display',
    'get_client_contact_info',
    
    # Bulk Operations
    'get_clients_by_ids',
    'get_clients_without_phone',
    'get_clients_without_instagram',
]