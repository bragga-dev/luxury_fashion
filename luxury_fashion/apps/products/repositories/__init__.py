from luxury_fashion.apps.products.repositories.product_category_repository import (
    create_category,
    update_category,
    delete_category,
    activate_category,
    deactivate_category,
    set_category_image,
    remove_category_image,
)

from luxury_fashion.apps.products.repositories.product_repository import (
    create_product,
    update_product,
    delete_product,
    activate_product,
    deactivate_product,
)

from luxury_fashion.apps.products.repositories.product_variant_repository import (
    create_variant,
    update_variant,
    delete_variant,
    activate_variant,
    deactivate_variant,
    adjust_variant_stock,
    set_variant_stock,
)

from luxury_fashion.apps.products.repositories.product_image_repository import (
    create_image,
    update_image,
    delete_image,
    set_cover_image,
    reorder_image,
)

from luxury_fashion.apps.products.repositories.product_shipping_repository import (
    create_shipping,
    update_shipping,
    delete_shipping,
    get_or_create_shipping,
)


__all__ = [

    "create_category",
    "update_category",
    "delete_category",
    "activate_category",
    "deactivate_category",
    "set_category_image",
    "remove_category_image",

    "create_product",
    "update_product",
    "delete_product",
    "activate_product",
    "deactivate_product",

    "create_variant",
    "update_variant",
    "delete_variant",
    "activate_variant",
    "deactivate_variant",
    "adjust_variant_stock",
    "set_variant_stock",

    "create_image",
    "update_image",
    "delete_image",
    "set_cover_image",
    "reorder_image",

    "create_shipping",
    "update_shipping",
    "delete_shipping",
    "get_or_create_shipping",

]