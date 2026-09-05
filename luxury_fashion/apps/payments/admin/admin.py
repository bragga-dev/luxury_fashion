from django.contrib import admin

from luxury_fashion.apps.payments.models.asaas_customer_model import AsaasCustomer
from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("variant_id", "order_item_quantity", "order_item_price")
    can_delete = False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("billing_type", "status", "value", "asaas_payment_id", "created_at")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("code", "user_id", "order_status", "total_geral", "created_at")
    list_filter = ("order_status", "created_at")
    search_fields = ("code", "user_id__email")
    readonly_fields = ("order_id", "code", "created_at", "updated_at")
    inlines = [OrderItemInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "order_id", "billing_type", "status", "value", "due_date")
    list_filter = ("billing_type", "status")
    search_fields = ("asaas_payment_id", "order_id__code")
    readonly_fields = ("payment_id", "created_at", "updated_at")


@admin.register(AsaasCustomer)
class AsaasCustomerAdmin(admin.ModelAdmin):
    list_display = ("client_id", "asaas_customer_id", "created_at")
    search_fields = ("asaas_customer_id", "client_id__first_name", "client_id__last_name")
    readonly_fields = ("customer_id", "created_at", "updated_at")