import secrets
import string


def generate_random_code(length: int = 12) -> str:
    alphabet = string.ascii_uppercase + string.digits

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )