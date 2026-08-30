from django.utils.translation import gettext_lazy as _


class ProductNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Produto não encontrado.")
        super().__init__(self.message)


class ProductNameAlreadyExists(Exception):
    def __init__(self, message=None):
        self.message = message or _("Já existe um produto com esse nome.")
        super().__init__(self.message)


class CategoryNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Categoria não encontrada.")
        super().__init__(self.message)


class CategoryNameAlreadyExists(Exception):
    def __init__(self, message=None):
        self.message = message or _("Já existe uma categoria com esse nome.")
        super().__init__(self.message)


class CategoryHasProducts(Exception):
    def __init__(self, message=None):
        self.message = message or _("Não é possível excluir uma categoria que possui produtos vinculados.")
        super().__init__(self.message)


class VariantNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Variante não encontrada.")
        super().__init__(self.message)


class VariantAlreadyExists(Exception):
    def __init__(self, message=None):
        self.message = message or _("Já existe uma variante com esse tamanho, cor e gênero para este produto.")
        super().__init__(self.message)


class ImageNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Imagem não encontrada.")
        super().__init__(self.message)


class ShippingNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Dados de frete não encontrados para esta variante.")
        super().__init__(self.message)


class ShippingAlreadyExists(Exception):
    def __init__(self, message=None):
        self.message = message or _("Esta variante já possui dados de frete cadastrados.")
        super().__init__(self.message)