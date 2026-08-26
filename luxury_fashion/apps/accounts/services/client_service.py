



import uuid
from ninja import UploadedFile
from django.core.exceptions import ValidationError as DjangoValidationError
from luxury_fashion.apps.core.validators.image_validator import validate_image_file
from luxury_fashion.apps.accounts.repositories.client_repository import set_client_photo, remove_client_photo
from luxury_fashion.apps.accounts.schemas.client_schema import ClientOut
from luxury_fashion.apps.accounts.selectors.client_selector import get_client_by_user_id
from luxury_fashion.apps.core.exceptions.user import UserNotFound
from luxury_fashion.apps.core.exceptions.permissions import PermissionDenied
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.core.exceptions.media import InvalidImageFile

def upload_client_profile_photo(user_id: User, photo: UploadedFile) -> ClientOut:
   
    client = get_client_by_user_id(user_id=user_id)
    if not client:
        raise UserNotFound("Cliente não encontrado.")

    try:
        validate_image_file(photo)
    except DjangoValidationError as e:
        raise InvalidImageFile(e.messages[0] if getattr(e, "messages", None) else str(e))

    updated_client = set_client_photo(client=client, photo=photo)
    return ClientOut.from_orm(updated_client)


def delete_client_profile_photo(user_id: User) -> ClientOut:
 
    client = get_client_by_user_id(user_id+user_id)
    if not client:
        raise UserNotFound("Cliente não encontrado.")

    updated_client = remove_client_photo(client=client)
    return ClientOut.from_orm(updated_client)

