from luxury_fashion.apps.products.api.frenet import (
 quote_shipping_router,   
)



from luxury_fashion.apps.products.api.category import (
    create_category_router,
    delete_category_router,
    detail_category_router,
    list_categories_router,
    remove_category_image_router,
    upload_category_image_router,
    deactivate_category_router,
    activate_category_router,
    update_category_router,
)
from luxury_fashion.apps.products.api.product import (
    list_products_admin_router,
    create_product_full_router,
    deactivate_product_router,
    activate_product_router,
    update_product_router,
    detail_product_router,
    delete_product_router,
    list_products_router,
)


__all__ = [


    "quote_shipping_router", 

    "create_category_router",
    "delete_category_router",
    "detail_category_router",
    "list_categories_router",
    "remove_category_image_router",
    "upload_category_image_router",
    "deactivate_category_router",
    "activate_category_router",
    "update_category_router",

    "list_products_admin_router",
    "create_product_full_router",
    "deactivate_product_router",
    "activate_product_router",
    "update_product_router",
    "detail_product_router",
    "delete_product_router",
    "list_products_router",

]