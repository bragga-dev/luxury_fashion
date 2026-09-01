from luxury_fashion.apps.products.services.product_category_service import (
    activate_category_for_admin,
    create_category_for_admin,
    deactivate_category_for_admin,
    delete_category_for_admin,
    get_category_for_all,
    list_categories_for_all,
    remove_category_image_for_admin,
    update_category_for_admin,
    upload_category_image_for_admin,
)

from luxury_fashion.apps.products.services.product_service import (
    activate_product_for_admin,
    create_product_for_amdin,
    deactivate_product_for_admin,
    delete_product_for_admin,
    get_product_for_all,
    list_products_for_all,
    search_products_for_all,
    update_product_for_admin,
)

from luxury_fashion.apps.products.services.product_variant_service import (
    activate_variant_for_admin,
    adjust_variant_stock_for_admin,
    create_variant_for_admin,
    deactivate_variant_for_admin,
    delete_variant_for_admin,
    get_variant_for_all,
    list_variants_for_all,
    set_variant_stock_for_admin,
    update_variant_for_admin,
)

from luxury_fashion.apps.products.services.product_image_service import (
    delete_image_for_admin,
    get_image_for_all,
    list_images_for_all,
    reorder_image_for_admin,
    set_cover_image_for_admin,
    update_image_for_admin,
    upload_image_for_admin,
)

from luxury_fashion.apps.products.services.product_shipping_service import (
    create_shipping_for_admin,
    delete_shipping_for_admin,
    get_shipping_for_all,
    get_shipping_payload,
    update_shipping_for_admin,
)

from luxury_fashion.apps.products.services.frenet_service import   quote_shipping_for_variant

__all__ = [

    "activate_category_for_admin",
    "create_category_for_admin",
    "deactivate_category_for_admin",
    "delete_category_for_admin",
    "get_category_for_all",
    "list_categories_for_all",
    "remove_category_image_for_admin",
    "update_category_for_admin",
    "upload_category_image_for_admin",

    "activate_product_for_admin",
    "create_product_for_amdin",
    "deactivate_product_for_admin",
    "delete_product_for_admin",
    "get_product_for_all",
    "list_products_for_all",
    "search_products_for_all",
    "update_product_for_admin",

    "activate_variant_for_admin",
    "adjust_variant_stock_for_admin",
    "create_variant_for_admin",
    "deactivate_variant_for_admin",
    "delete_variant_for_admin",
    "get_variant_for_all",
    "list_variants_for_all",
    "set_variant_stock_for_admin",
    "update_variant_for_admin",

    "delete_image_for_admin",
    "get_image_for_all",
    "list_images_for_all",
    "reorder_image_for_admin",
    "set_cover_image_for_admin",
    "update_image_for_admin",
    "upload_image_for_admin",

    "create_shipping_for_admin",
    "delete_shipping_for_admin",
    "get_shipping_for_all",
    "get_shipping_payload",
    "update_shipping_for_admin",

    "quote_shipping_for_variant",

]