def get_client_ip(request) -> str | None:
    """
    IP do cliente para registro de consentimento (evidência LGPD). Atrás de proxy/Nginx
    usa o primeiro IP do X-Forwarded-For; sem proxy, o REMOTE_ADDR.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None