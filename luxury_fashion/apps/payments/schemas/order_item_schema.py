"""
OrderItem é um snapshot imutável do que foi comprado — não existe endpoint
pra criar/editar item de pedido diretamente (isso quebraria a integridade
fiscal/contábil do pedido). Os itens só nascem via checkout do carrinho,
por isso aqui só tem schema de saída.
"""
import uuid
from decimal import Decimal

from ninja import Schema

from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.products.schemas.product_variant_schema import VariantOut


class OrderItemOut(Schema):
    order_item_id: uuid.UUID
    variant: VariantOut
    order_item_quantity: int
    order_item_price: Decimal
    subtotal: Decimal

    @classmethod
    def from_orm(cls, item: OrderItem) -> "OrderItemOut":
        return cls(
            order_item_id=item.order_item_id,
            variant=VariantOut.from_orm(item.variant_id),
            order_item_quantity=item.order_item_quantity,
            order_item_price=item.order_item_price,
            subtotal=item.subtotal(),
        )