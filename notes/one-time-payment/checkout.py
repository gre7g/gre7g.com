import logging
import os
from paypalserversdk.api_helper import APIHelper
from paypalserversdk.configuration import Environment
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.logging.configuration.api_logging_configuration import (
    LoggingConfiguration,
    RequestLoggingConfiguration,
    ResponseLoggingConfiguration,
)
from paypalserversdk.models.amount_breakdown import AmountBreakdown
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.controllers.orders_controller import OrdersController
from paypalserversdk.models.item import Item
from paypalserversdk.models.item_category import ItemCategory
from paypalserversdk.models.money import Money
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient

# Constants:
LOG = logging.getLogger(__name__)
CURRENCY = "USD"

logging.basicConfig(level=logging.INFO)

item_list = [Item(
    name="name",
    unit_amount=Money(CURRENCY, 1.99),
    quantity="2",
    description="description",
    sku="sku",
    category=ItemCategory.PHYSICAL_GOODS,
)]

breakdown = AmountBreakdown(Money(CURRENCY, 3.98), Money(CURRENCY, 2.50))

order_dict = {
    "body": OrderRequest(
        CheckoutPaymentIntent.CAPTURE,
        [
            PurchaseUnitRequest(
                AmountWithBreakdown(CURRENCY, 6.48, breakdown), "order_id", items=item_list
            )
        ],
    )
}

paypal_client_id = os.getenv("PAYPAL_CLIENT_ID")
paypal_client_secret = os.getenv("PAYPAL_CLIENT_SECRET")

log_config = LoggingConfiguration(
    log_level=logging.INFO,
    mask_sensitive_headers=False,
    request_logging_config=RequestLoggingConfiguration(
        log_body=True,
        log_headers=True,
    ),
    response_logging_config=ResponseLoggingConfiguration(
        log_body=True,
        log_headers=True,
    ),
)

paypal = PaypalServersdkClient(
    logging_configuration=log_config,
    environment=Environment.SANDBOX,
    client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
        paypal_client_id, paypal_client_secret
    ),
)

orders_controller: OrdersController = paypal.orders
result = orders_controller.create_order(order_dict)
from pprint import pprint
pprint(APIHelper.to_dictionary(result.body))
