# -*- coding: utf-8 -*-

import os
import re
import base64
import tempfile

from lxml import objectify
from datetime import datetime

DATETIME_TYPES  = ('dispatchSentDate',)
STRING_TYPES    = ('alternateDeviceId', 'imeiNumber',)
BASE64_TYPES    = ('packingList', 'proformaFileData', 'returnLabelFileData',)
FLOAT_TYPES     = ('totalFromOrder', 'exchangePrice', 'stockPrice', 'netPrice',)
DIAGS_TIMESTAMP_TYPES = ('startTimeStamp', 'endTimeStamp',)

TZMAP = {
    'GMT'   : '',      # Greenwich Mean Time
    'PDT'   : '-0700', # Pacific Daylight Time
    'PST'   : '-0800', # Pacific Standard Time
    'CDT'   : '-0700', # Central Daylight Time
    'CST'   : '-0600', # Central Standard Time
    'EDT'   : '-0400', # Eastern Daylight Time
    'EST'   : '-0500', # Eastern Standard Time
    'CEST'  : '+0200', # Central European Summer Time
    'CET'   : '+0100', # Central European Time
    'JST'   : '+0900', # Japan Standard Time
    'IST'   : '+0530', # Indian Standard Time
    'CCT'   : '+0800', # Chinese Coast Time
    'AEST'  : '+1000', # Australian Eastern Standard Time
    'AEDT'  : '+1100', # Australian Eastern Daylight Time
    'ACST'  : '+0930', # Austrailian Central Standard Time
    'ACDT'  : '+1030', # Australian Central Daylight Time
    'NZST'  : '+1200', # New Zealand Standard Time
    'USZ1'  : '+0300', # Kaliningrad Time
    'MSK'   : '+0400', # Moscow Time
    'YEKST' : '+0600', # Yekaterinburg Time
    'OMSST' : '+0700', # Omsk Time
    'KRAST' : '+0800', # Krasnoyarsk Time
    'IRKST' : '+0900', # Irkutsk Time
    'YAKST' : '+1000', # Yakutsk Time
    'VLAST' : '+1100', # Vladivostok Time
    'MAGST' : '+1200', # Magadan Time
    'EET'   : '+0200', # Eastern European Standard Time
    'EEST'  : '+0300', # Eastern European Summer Time
}


def gsx_date(value):
    try:
        # standard GSX format: "mm/dd/yy"
        return datetime.strptime(value, "%m/%d/%y").date()
    except ValueError:
        pass

    try:
        # some dates are formatted as "yyyy-mm-dd"
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        pass


def gsx_boolean(value):
    return value in ('Y', 'true',)


def gsx_price(value):
    # Strips currency from price
    return float(re.sub(r'[A-Z ,]', '', value))


def gsx_attachment(value):
    v = base64.b64decode(value)
    of = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    of.write(v)
    return of.name


def gsx_datetime(value):
    # 2011-01-27 11:45:01 PST
    # Unfortunately we have to chomp off the TZ info...
    m = re.search(r'^(\d+\-\d+\-\d+ \d+:\d+:\d+) (\w+)$', value)
    ts, tz = m.groups()
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")


def gsx_timestamp(value):
    # 03/06/14 09:01 PM
    return datetime.strptime(value, "%m/%d/%y %I:%M %p")


def gsx_diags_timestamp(value):
    # It is always in GMT and in format DD-MMM-YY HH24:MM:SS
    return datetime.strptime(value, "%d-%b-%y %I:%M:%S")


class GsxElement(objectify.ObjectifiedElement):
    """
    Each element in the GSX response tree should be a GsxElement
    """
    def __getattribute__(self, name):
        try:
            result = super(GsxElement, self).__getattribute__(name)
        except AttributeError:
            """
            The XML returned by GSX can be pretty inconsistent, especially
            between the different environments. It's therefore more
            practical to return None than to expect AttributeErrors all
            over your application.
            """
            return

        # Work around lxml chomping leading zeros off of IMEI numbers
        if name in STRING_TYPES:
            return unicode(result.text or '')

        if isinstance(result, objectify.NumberElement):
            return result.pyval

        if isinstance(result, objectify.StringElement):
            name = result.tag
            result = result.text or ''
            result = unicode(result)

            if not result:
                return

            if name in DATETIME_TYPES:
                return gsx_datetime(result)
            if name in DIAGS_TIMESTAMP_TYPES:
                return gsx_diags_timestamp(result)
            if name in BASE64_TYPES:
                return gsx_attachment(result)
            if name in FLOAT_TYPES:
                return gsx_price(result)
            if name.endswith('Date'):
                return gsx_date(result)
            if name.endswith('Timestamp'):
                return gsx_timestamp(result)
            if re.search(r'^[YN]$', result):
                return gsx_boolean(result)

        return result


def parse(root, response):
    """
    >>> parse('tests/fixtures/warranty_status.xml', 'warrantyDetailInfo').warrantyStatus
    'Apple Limited Warranty'
    >>> parse('tests/fixtures/warranty_status.xml', 'warrantyDetailInfo').estimatedPurchaseDate
    datetime.date(2010, 8, 25)
    >>> parse('tests/fixtures/warranty_status.xml', 'warrantyDetailInfo').limitedWarranty
    True
    >>> parse('tests/fixtures/warranty_status.xml', 'warrantyDetailInfo').isPersonalized
    """
    parser = objectify.makeparser(remove_blank_text=True)
    lookup = objectify.ObjectifyElementClassLookup(tree_class=GsxElement)
    parser.set_element_class_lookup(lookup)

    if isinstance(root, basestring) and os.path.exists(root):
        root = objectify.parse(root, parser)
    else:
        root = objectify.fromstring(root, parser)

    return root.find('*//%s' % response)


if __name__ == '__main__':
    import doctest
    import logging
    logging.basicConfig(level=logging.DEBUG)
    doctest.testmod()

