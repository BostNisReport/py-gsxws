# -*- coding: utf-8 -*-
"""
https://gsxwsut.apple.com/apidocs/ut/html/WSAPIChangeLog.html?user=asp
"""

import re
import urllib

from lookups import Lookup
from diagnostics import Diagnostics
from core import GsxObject, GsxError, validate


def models():
    """
    >>> models() # doctest: +ELLIPSIS
    {'IPODCLASSIC': {'models': ['iPod 5th Generation (Late 2006)', ...
    """
    import os
    import yaml
    filepath = os.path.join(os.path.dirname(__file__), "products.yaml")
    return yaml.load(open(filepath, 'r'))


class Product(object):
    """
    Something serviceable made by Apple
    """
    sn          = ''  # serialNumber
    description = ''  # configDescription

    def __init__(self, sn, **kwargs):
        if validate(sn, 'alternateDeviceId'):
            self.alternateDeviceId = sn
            self._gsx = GsxObject(alternateDeviceId=sn)
        else:
            self.serialNumber = sn
            self._gsx = GsxObject(serialNumber=sn)

        self._gsx._namespace = "glob:"

    def model(self):
        """
        Returns the model description of this Product

        >>> Product('DGKFL06JDHJP').model().configDescription
        'iMac (27-inch, Mid 2011)'
        """
        result = self._gsx._submit("productModelRequest", "FetchProductModel")
        self.configDescription = result.configDescription
        self.productLine = result.productLine
        self.configCode = result.configCode
        return result

    def warranty(self, parts=[], date_received=None, ship_to=None):
        """
        The Warranty Status API retrieves the same warranty details
        displayed on the GSX Coverage screen.
        If part information is provided, the part warranty information is returned.
        If you do not provide the optional part information in the
        warranty status request, the unit level warranty information is returned.

        >>> Product('DGKFL06JDHJP').warranty().warrantyStatus
        'Out Of Warranty (No Coverage)'
        >>> Product('DGKFL06JDHJP').warranty().estimatedPurchaseDate.pyval
        '06/02/11'
        >>> Product('WQ8094DW0P1').warranty().blaa  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        AttributeError: no such child: blaa
        >>> Product('WQ8094DW0P1').warranty([(u'661-5070', u'Z26',)]).warrantyStatus
        'Out Of Warranty (No Coverage)'
        """
        if self.should_check_activation:
            ad = self.activation()
            self._gsx.serialNumber = ad.serialNumber
            # "Please enter either a serial number or an IMEI number but not both."
            self._gsx.unset('alternateDeviceId')

        if ship_to is not None:
            self._gsx.shipTo = ship_to
            
        try:
            self._gsx.partNumbers = []
            for k, v in parts:
                part = GsxObject(partNumber=k, comptiaCode=v)
                self._gsx.partNumbers.append(part)
        except Exception:
            pass

        if date_received is not None:
            self._gsx.unitReceivedDate = date_received

        self._gsx._submit("unitDetail", "WarrantyStatus", "warrantyDetailInfo")

        self.warrantyDetails = self._gsx._req.objects
        self.imageURL = self.warrantyDetails.imageURL
        self.productDescription = self.warrantyDetails.productDescription
        self.description = self.productDescription.lstrip('~VIN,')

        self.repair_strategies = []

        try:
            for i in self.warrantyDetails.availableRepairStrategies:
                self.repair_strategies.append(i.availableRepairStrategy)
        except (AttributeError, TypeError):
            pass

        return self.warrantyDetails

    def parts(self):
        """
        >>> Product('DGKFL06JDHJP').parts() # doctest: +ELLIPSIS
        <Element parts at...
        >>> Product(productName='MacBook Pro (17-inch, Mid 2009)').parts() # doctest: +ELLIPSIS
        <Element parts at...
        """
        try:
            return Lookup(serialNumber=self.serialNumber).parts()
        except AttributeError:
            return Lookup(productName=self.productName).parts()

    def repairs(self):
        """
        >>> Product(serialNumber='DGKFL06JDHJP').repairs() # doctest: +ELLIPSIS
        <Element lookupResponseData at...
        """
        return Lookup(serialNumber=self.serialNumber).repairs()

    def diagnostics(self):
        """
        >>> Product('DGKFL06JDHJP').diagnostics()
        """
        if hasattr(self, "alternateDeviceId"):
            diags = Diagnostics(alternateDeviceId=self.alternateDeviceId)
        else:
            diags = Diagnostics(serialNumber=self.serialNumber)
            
        return diags.fetch()

    def fetch_image(self, url=None):
        """
        >>> Product('DGKFL06JDHJP').fetch_image() # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        GsxError: No URL to fetch product image
        """
        url = url or self.imageURL

        if url is None:
            raise GsxError("No URL to fetch product image")

        try:
            return urllib.urlretrieve(url)[0]
        except Exception as e:
            raise GsxError("Failed to fetch product image: %s" % e)

    def activation(self):
        """
        The Fetch iOS Activation Details API is used to
        fetch activation details of iOS Devices.

        >>> Product('013348005376007').activation().unlocked
        True
        >>> Product('W874939YX92').activation().unlocked # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        GsxError: Provided serial number does not belong to an iOS Device...
        """
        self._gsx._namespace = "glob:"
        return self._gsx._submit("FetchIOSActivationDetailsRequest",
                                 "FetchIOSActivationDetails",
                                 "activationDetailsInfo")

    @property
    def fmip_status(self, wty=None):
        if wty is None:
            wty = self.warrantyDetails

        if wty is None:
            raise GsxError('Must run warranty status before FMiP status check')

        return wty.activationLockStatus or ''

    @property
    def fmip_is_active(self):
        """
        Returns True if FMiP status is active, False otherwise
        """
        return 'Find My iPhone is active' in self.fmip_status

    def is_unlocked(self, ad=None):
        """
        Returns true if this iOS device is unlocked
        """
        policy = ad.nextTetherPolicyDetails or ''
        return ad.unlocked or ("unlock" in policy)

    @property
    def is_locked(self):
        return not self.is_unlocked()

    @property
    def should_check_activation(self):
        """
        Returns True if activation check should be run.
        This is mainly for WarrantyStatus which does not accept IMEI.
        """
        return hasattr(self, "alternateDeviceId") and not hasattr(self, "serialNumber")

    @property
    def is_mac(self):
        return re.match(r'^i?Mac', self.description)

    @property
    def is_iphone(self):
        return self.description.startswith('iPhone')

    @property
    def is_ipad(self):
        return self.description.startswith('iPad')

    @property
    def is_ios(self):
        return self.is_iphone or self.is_ipad

    @property
    def is_valid(self):
        return self.is_ios or self.is_mac

    @property
    def has_warranty(self):
        return self.warrantyDetails.limitedWarranty

    @property
    def is_vintage(self):
        title = self.warrantyDetails.productDescription or ''
        return title.startswith('~VIN,')

    @property
    def parts_covered(self):
        return self.warrantyDetails.partCovered is True

    @property
    def labor_covered(self):
        return self.warrantyDetails.laborCovered is True

    @property
    def parts_and_labor_covered(self):
        return self.parts_covered and self.labor_covered

    @property
    def has_onsite(self):
        from datetime import date
        try:
            return date.today() < self.warrantyDetails.onsiteEndDate
        except Exception:
            return False


if __name__ == '__main__':
    import sys
    import doctest
    import logging
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:])
    doctest.testmod()
