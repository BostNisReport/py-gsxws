# -*- coding: utf-8 -*-

from core import GsxObject, validate

RETURN_TYPES = (
    (1, "Dead On Arrival"),
    (2, "Good Part Return"),
    (3, "Convert To Stock"),
    (4, "Transfer to Out of Warranty"),
)

CARRIERS = (
    ('XAER',    "Aero 2000"),
    ('XAIRBEC', "Airborne"),
    ('XAIRB',   "Airborne"),
    ('XARM',    "Aramex"),
    ('XOZP',    "Australia Post"),
    ('XBAX',    "BAX GLOBAL PTE LTD"),
    ('XCPW',    "CPW Internal"),
    ('XCL',     "Citylink"),
    ('XDHL',    "DHL"),
    ('XDHLC',   "DHL"),
    ('XDZNA',   "Danzas-AEI"),
    ('XEAS',    "EAS"),
    ('XEGL',    "Eagle ASIA PACIFIC HOLDINGS"),
    ('XEXXN',   "Exel"),
    ('XFEDE',   "FedEx"),
    ('XFDE',    "FedEx Air"),
    ('XGLS',    "GLS-General Logistics Systems"),
    ('XHNF',    "H and Friends"),
    ('XNGLN',   "Nightline"),
    ('XPL',     "Parceline"),
    ('XPRLA',   "Purolator"),
    ('SDS',     "SDS An Post"),
    ('XSNO',    "Seino Transportation Co. Ltd."),
    ('XSTE',    "Star Track Express"),
    ('XTNT',    "TNT"),
    ('XUPSN',   "UPS"),
    ('XUTI',    "UTi (Japan) K.K."),
    ('XYMT',    "YAMATO"),
)


class Return(GsxObject):

    _namespace = "asp:"

    def __init__(self, order_number=None, *args, **kwargs):
        super(Return, self).__init__(*args, **kwargs)

        if order_number is not None:
            self.returnOrderNumber = order_number

    def get_pending(self):
        """
        The Parts Pending Return API returns a list of all parts that
        are pending for return, based on the search criteria.

        >>> Return(repairType='CA').get_pending()  # doctest: +SKIP
        """
        dt = self._make_type('ns1:partsPendingReturnRequestType')
        dt.repairData = self.data

        return self._submit('PartsPendingReturn', dt, 'partsPendingResponse')

    def get_report(self):
        """
        The Return Report API returns a list of all parts that are returned
        or pending for return, based on the search criteria.
        """
        dt = self._make_type('ns1:returnReportRequestType')
        dt.returnRequestData = self.data

        return self.submit('ReturnReport', dt, 'returnResponseData')

    def get_label(self, part_number):
        """
        The Return Label API retrieves the Return Label for a given Return Order Number.

        >>> Return('7458231326').get_label('661-5852')
        """
        if not validate(part_number, 'partNumber'):
            raise ValueError("%s is not a valid part number" % part_number)

        self.partNumber = part_number
        self._submit("ReturnLabelRequest", "ReturnLabel", "returnLabelData")
        return self._req.objects

    def get_proforma(self):
        """
        The View Bulk Return Proforma API allows you to view the proforma label
        for a given Bulk Return Id. You can create a parts bulk return
        by using the Register Parts for Bulk Return API.
        """
        pass

    def register_parts(self, parts):
        """
        The Register Parts for Bulk Return API creates a bulk return for
        the registered parts.
        The API returns the Bulk Return Id with the packing list.

        >>> Return(shipToCode=123456).register_parts([ServicePart('661-5852')])
        """
        self.bulkReturnOrder = parts
        self._submit("bulkPartsRegistrationRequest",
                     "RegisterPartsForBulkReturn",
                     "bulkPartsRegistrationData")

        return self._req.objects

    def update_parts(self, confirmation, parts):
        """
        The Parts Return Update API allows you to mark a part
        with the status GPR(2), DOA(1), CTS(3), or TOW(4).
        The API can be used only by ASP.

        >>> Return().update_parts('G135877430',\    # doctest: +SKIP
        [{'partNumber': '661-5174',\
        'comptiaCode': 'Z29',\
        'comptiaModifier': 'A',\
        'returnType': 2}])
        """
        self.repairConfirmationNumber = confirmation
        self.orderLines = parts
        self._submit("repairData", "PartsReturnUpdate", "PartsReturnUpdateResponse")
        return self._req.objects


if __name__ == '__main__':
    import sys
    import doctest
    import logging
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:])
    doctest.testmod()
