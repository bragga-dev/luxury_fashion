from typing import TypeVar, Generic, List
from ninja import Schema

T = TypeVar("T")

class PageOut(Schema, Generic[T]):
    items: List[T]
    total: int     
    page: int      
    page_size: int 
    pages: int     


class MessageOut(Schema):
    detail: str


class FieldErrorOut(Schema):
    field: str     
    message: str
    type: str      


class ValidationErrorOut(Schema):
    detail: str
    errors: List[FieldErrorOut]