# -*- coding: utf-8 -*-

import base64
import logging
import tempfile
from datetime import date

from core import GsxObject, connect


class Lookup(GsxObject):
    def __init__(self, *args, **kwargs):
        super(Lookup, self).__init__(*args, **kwargs)
        self._namespace = "asp:"

    def lookup(self, method, response="lookupResponseData"):
        result = self._submit("lookupRequestData", method, response)
        return [result] if isinstance(result, dict) else result

    def parts(self):
        """
        The Parts Lookup API allows users to access part and part pricing data prior to
        creating a repair or order. Parts lookup is also a good way to search for
        part numbers by various attributes of a part
        (config code, EEE code, serial number, etc.).
        """
        self._namespace = "core:"
        return self.lookup("PartsLookup", "parts")

    def repairs(self):
        """
        The Repair Lookup API mimics the front-end repair search functionality.
        It fetches up to 2500 repairs in a given criteria.
        Subsequently, the extended Repair Status API can be used
        to retrieve more details of the repair.

        >>> Lookup(serialNumber='DGKFL06JDHJP').repairs() # doctest: +ELLIPSIS
        [{'customerName': 'Lepalaan,Filipp',...
        """
        return self.lookup("RepairLookup")

    def invoices(self):
        """
        The Invoice ID Lookup API allows AASP users
        to fetch the invoice generated for last 24 hrs

        >>> Lookup(shipTo=677592, invoiceDate=date(2012,2,6)).invoices().invoiceID
        '9670348809'
        """
        return self.lookup("InvoiceIDLookup")

    def invoice_details(self):
        """
        The Invoice Details Lookup API allows AASP users to
        download invoice for a given invoice id.
        >>> Lookup(invoiceID=9670348809).invoice_details()
        """
        result = self.lookup("InvoiceDetailsLookup")
        pdf = base64.b64decode(result.invoiceData)
        outfile = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        outfile.write(pdf)
        result.invoiceData = outfile.name
        return result

    def component_check(self, parts=[]):
        """
        The Component Check API allows service providers to send 
        the information required to create a repair and check if 
        the repair is eligible for component serial number verification 
        for certain components listed in response.
        """
        if parts:
            self.orderLines = parts

        return self._submit("repairData", "ComponentCheck", "componentCheckDetails")


if __name__ == '__main__':
    import sys
    import doctest
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:])
    doctest.testmod()
