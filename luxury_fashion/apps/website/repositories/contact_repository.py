"""
Contact Repository — persistência de Contact.
"""

from luxury_fashion.apps.website.models.contact_model import Contact


def create_contact(**fields) -> Contact:
    contact = Contact(**fields)
    contact.full_clean()
    contact.save()
    return contact


def update_contact(contact: Contact, **fields) -> Contact:
    for attr, value in fields.items():
        setattr(contact, attr, value)
    contact.full_clean()
    contact.save()
    return contact


def delete_contact(contact: Contact) -> None:
    contact.delete()


def update_contact_status(contact: Contact, status: str) -> Contact:
    contact.status = status
    contact.save(update_fields=["status"])
    return contact