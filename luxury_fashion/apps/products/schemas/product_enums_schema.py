from enum import Enum

from luxury_fashion.apps.products.models.product_model import Product


class ProductGenderEnum(str, Enum):
    MASCULINO = Product.ProductGender.MASCULINO.value
    FEMININO = Product.ProductGender.FEMININO.value
    UNISSEX = Product.ProductGender.UNISSEX.value


class ProductSizeEnum(str, Enum):
    PP = Product.ProductSize.PP.value
    P = Product.ProductSize.P.value
    M = Product.ProductSize.M.value
    G = Product.ProductSize.G.value
    GG = Product.ProductSize.GG.value
    XGG = Product.ProductSize.XGG.value
    G1 = Product.ProductSize.G1.value
    G2 = Product.ProductSize.G2.value
    G3 = Product.ProductSize.G3.value
    G4 = Product.ProductSize.G4.value
    G5 = Product.ProductSize.G5.value
    G6 = Product.ProductSize.G6.value
    SIZE_34 = Product.ProductSize.SIZE_34.value
    SIZE_36 = Product.ProductSize.SIZE_36.value
    SIZE_38 = Product.ProductSize.SIZE_38.value
    SIZE_40 = Product.ProductSize.SIZE_40.value
    SIZE_42 = Product.ProductSize.SIZE_42.value
    SIZE_44 = Product.ProductSize.SIZE_44.value
    SIZE_46 = Product.ProductSize.SIZE_46.value
    SIZE_48 = Product.ProductSize.SIZE_48.value
    SIZE_50 = Product.ProductSize.SIZE_50.value
    SIZE_52 = Product.ProductSize.SIZE_52.value
    SIZE_54 = Product.ProductSize.SIZE_54.value
    SIZE_56 = Product.ProductSize.SIZE_56.value
    SIZE_58 = Product.ProductSize.SIZE_58.value
    SIZE_60 = Product.ProductSize.SIZE_60.value
    SIZE_62 = Product.ProductSize.SIZE_62.value
    SIZE_64 = Product.ProductSize.SIZE_64.value


class ProductColorEnum(str, Enum):
    BLACK = Product.ProductColor.BLACK.value
    WHITE = Product.ProductColor.WHITE.value
    RED = Product.ProductColor.RED.value
    BLUE = Product.ProductColor.BLUE.value
    GREEN = Product.ProductColor.GREEN.value
    PINK = Product.ProductColor.PINK.value
    YELLOW = Product.ProductColor.YELLOW.value
    ORANGE = Product.ProductColor.ORANGE.value
    PURPLE = Product.ProductColor.PURPLE.value
    BROWN = Product.ProductColor.BROWN.value
    BEIGE = Product.ProductColor.BEIGE.value
    GRAY = Product.ProductColor.GRAY.value
    NAVY = Product.ProductColor.NAVY.value
    WINE = Product.ProductColor.WINE.value
    OFF_WHITE = Product.ProductColor.OFF_WHITE.value