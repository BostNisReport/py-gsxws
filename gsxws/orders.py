# -*- coding: utf-8 -*-

from core import GsxObject


class OrderLine(GsxObject):
    partNumber = None
    quantity = None


class APPOrder(GsxObject):
    """
    Description:
    The Create APP Order API is designed to create
    an AppleCare Protection Plan (APP) enrollment.
    Creation of an APP enrollment requires serial number of the unit
    for which service agreement is being ordered, customer information
    and the billing and ship-to information.
    On successful submission, GSX assigns an AppleCare Protection Plan
    agreement number immediately.
    This agreement is valid as soon as it is sold to the customer.
    A quote is obtained for an APP and sent as part of the response.

    Context:
    The API can be invoked only after valid authentication.
    Authentication generates a session ID that needs to be passed while using this API.
    """


class StockingOrder(GsxObject):
    """
    Description:
    The Create Stocking Order API is used to create a stocking order.
    The purchase order number, ship-to number of the service provider
    and a list of parts are required.
    The service account number is obtained from the session.
    Quote is obtained for the parts and if it is processed successfully,
    a confirmation number, array of parts, sub-total, tax and total price are returned.
    The part details also contain the net price and availability.

    Context:
    The API can be invoked only after valid authentication.
    Authentication generates a session ID that needs to be passed while using this API.

    >>> StockingOrder(purchaseOrderNumber=111, shipToCode=677592).add_part('661-5097', 1).submit()
    """
    _namespace = "asp:"

    def __init__(self, *args, **kwargs):
        super(StockingOrder, self).__init__(*args, **kwargs)
        self.orderLines = list()

    def add_part(self, part_number, quantity):
        part = OrderLine(partNumber=part_number, quantity=quantity)
        self.orderLines.append(part)
        return self

    def submit(self):
        return self._submit("orderData", "CreateStockingOrder", "orderConfirmation")


if __name__ == '__main__':
    import sys
    import doctest
    import logging
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:5])
    doctest.testmod()
