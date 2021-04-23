# -*- coding: utf-8 -*-

"""
Copyright (c) 2013, Filipp Lepalaan All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os
import re
import json
import base64
import shelve
import os.path
import hashlib
import logging
import requests
import tempfile
import objectify
import xml.etree.ElementTree as ET

from datetime import date, time, datetime, timedelta

VERSION     = "0.92"

GSX_ENV     = "ut" # it, ut or pr
GSX_LANG    = "en"
GSX_REGION  = "emea"
GSX_LOCALE  = "en_XXX"
GSX_TIMEOUT = 30 # session timeout (expiration) in minutes

GSX_SESSION = None

GSX_REGIONS = (
    ('002', "Asia/Pacific"),
    ('003', "Japan"),
    ('004', "Europe"),
    ('005', "United States"),
    ('006', "Canadia"),
    ('007', "Latin America"),
)

GSX_TIMEZONE = 'CEST'

GSX_TIMEZONES = (
    ('PST',     "UTC - 8h (Pacific Standard Time)"),
    ('PDT',     "UTC - 7h (Pacific Daylight Time)"),
    ('CST',     "UTC - 6h (Central Standard Time)"),
    ('CDT',     "UTC - 5h (Central Daylight Time)"),
    ('EST',     "UTC - 5h (Eastern Standard Time)"),
    ('EDT',     "UTC - 4h (Eastern Daylight Time)"),
    ('GMT',     "UTC (Greenwich Mean Time)"),
    ('CET',     "UTC + 1h (Central European Time)"),
    ('CEST',    "UTC + 2h (Central European Summer Time)"),
    ('USZ1',    "UTC + 3h (Kaliningrad Time)"),
    ('MSK',     "UTC + 4h (Moscow Time)"),
    ('IST',     "UTC + 5.5h (Indian Standard Time)"),
    ('YEKST',   "UTC + 6h (Yekaterinburg Time)"),
    ('OMSST',   "UTC + 7h (Omsk Time)"),
    ('KRAST',   "UTC + 8h (Krasnoyarsk Time)"),
    ('CCT',     "UTC + 8h (Chinese Coast Time)"),
    ('IRKST',   "UTC + 9h (Irkutsk Time)"),
    ('JST',     "UTC + 9h (Japan Standard Time)"),
    ('YAKST',   "UTC + 10h (Yakutsk Time)"),
    ('AEST',    "UTC + 10h (Australian Eastern Standard Time)"),
    ('VLAST',   "UTC + 11h (Vladivostok Time)"),
    ('AEDT',    "UTC + 11h (Australian Eastern Daylight Time)"),
    ('ACST',    "UTC + 9.5h (Austrailian Central Standard Time)"),
    ('ACDT',    "UTC + 10.5h (Australian Central Daylight Time)"),
    ('NZST',    "UTC + 12h (New Zealand Standard Time)"),
    ('MAGST',   "UTC + 12h (Magadan Time)"),
)

REGION_CODES = ('apac', 'am', 'la', 'emea',)

ENVIRONMENTS = (
    ('pr', "Production"),
    ('ut', "Development"),
    ('it', "Testing"),
)

GSX_HOSTS = {'pr': '', 'it': 'it', 'ut': 'ut'}
GSX_URL = "https://gsxapi{env}.apple.com/gsx-ws/services/{region}/asp"


def validate(value, what=None):
    """
    Tries to guess the meaning of value or validate that
    value looks like what it's supposed to be.

    >>> validate('XD368Z/A', 'partNumber')
    True
    >>> validate('XGWL2Z/A', 'partNumber')
    True
    >>> validate('ZM661-5883', 'partNumber')
    True
    >>> validate('661-01234', 'partNumber')
    True
    >>> validate('B661-6909', 'partNumber')
    True
    >>> validate('G143111400', 'dispatchId')
    True
    >>> validate('R164323085', 'dispatchId')
    True
    >>> validate('blaa', 'serialNumber')
    False
    >>> validate('MacBook Pro (Retina, Mid 2012)', 'productName')
    True
    """
    result = None

    if not isinstance(value, basestring):
        raise ValueError('%s is not valid input (%s != string)' % (value, type(value)))

    rex = {
        'partNumber':       r'^([A-Z]{1,4})?\d{1,3}\-?(\d{1,5}|[A-Z]{1,2})(/[A-Z])?$',
        'serialNumber':     r'^[A-Z0-9]{11,12}$',
        'eeeCode':          r'^[A-Z0-9]{3,4}$',
        'returnOrder':      r'^7\d{9}$',
        'repairNumber':     r'^\d{12}$',
        'dispatchId':       r'^[A-Z]+\d{9,15}$',
        'alternateDeviceId': r'^\d{15}$',
        'diagnosticEventNumber': r'^\d{23}$',
        'productName':      r'^i?Mac',
    }

    for k, v in rex.items():
        if re.match(v, value):
            result = k

    return (result == what) if what else result


def get_format(locale=GSX_LOCALE):
    filepath = os.path.join(os.path.dirname(__file__), 'langs.json')
    df = open(filepath, 'r')
    return json.load(df).get(locale)


class GsxError(Exception):
    """A generic GSX-related error."""

    def __init__(self, message=None, xml=None, url=None, code=None, status=None):
        """Initialize a GsxError."""
        self.codes = []
        self.messages = []

        if isinstance(message, basestring):
            self.messages.append(message)

        if status == 403:
            self.messages.append('Access denied')

        if xml is not None:
            logging.debug(url)
            logging.debug(xml)

            try:
                root = ET.fromstring(xml)
            except Exception:
                return  # This may also be HTML

            # Collect all the info we have on the error
            for el in root.findall('*//faultcode'):
                self.codes.append(el.text)
            for el in root.findall('*//faultstring'):
                self.messages.append(el.text)
            for el in root.findall('*//code'):
                self.codes.append(el.text)
            for el in root.findall('*//message'):
                self.messages.append(el.text)

    def __str__(self):
        return repr(self.message)

    @property
    def code(self):
        try:
            return self.codes[0]
        except IndexError:
            return u'XXX'

    @property
    def message(self):
        return unicode(self)

    @property
    def errors(self):
        return dict(zip(self.codes, self.messages))

    def __unicode__(self):
        if len(self.messages) < 1:
            return u'Unknown GSX error'

        return u' '.join(self.messages)


class GsxCache(object):
    """The cache creates a separate shelf for each GSX session."""

    shelf = None
    tmpdir = tempfile.gettempdir()

    def __init__(self, key, expires=timedelta(minutes=20)):
        self.key = key
        self.expires = expires
        self.now = datetime.now()
        self.fp = os.path.join(self.tmpdir, "gsxws_%s" % key)
        self.shelf = shelve.open(self.fp, protocol=-1)

        if not self.shelf.get(key):
            # Initialize the key
            self.set(key, None)

    def get(self, key):
        """Get a value from the cache."""
        try:
            d = self.shelf[key]
            if d['expires'] > self.now:
                return d['value']
            else:
                del self.shelf[key]
        except KeyError:
            return None

    def set(self, key, value):
        """Set a value in the cache."""
        d = {
            'value'     : value,
            'expires'   : self.now + self.expires
        }

        self.shelf[key] = d
        return self

    def nuke(self):
        """Delete this cache."""
        os.remove(self.fp)


class GsxRequest(object):
    """Creates and submits the SOAP envelope."""

    env     = None
    obj     = None # The GsxObject being submitted
    data    = None # The GsxObject payload in XML format
    body    = None # The Body part of the SOAP envelope

    _request = ""
    _response = ""

    def __init__(self, **kwargs):
        "Construct the SOAP envelope."
        self.objects = []
        self.env = ET.Element("soapenv:Envelope")
        self.env.set("xmlns:core", "http://gsxws.apple.com/elements/core")
        self.env.set("xmlns:glob", "http://gsxws.apple.com/elements/global")
        self.env.set("xmlns:asp", "http://gsxws.apple.com/elements/core/asp")
        self.env.set("xmlns:soapenv", "http://schemas.xmlsoap.org/soap/envelope/")
        self.env.set("xmlns:emea", "http://gsxws.apple.com/elements/core/asp/emea")

        ET.SubElement(self.env, "soapenv:Header")
        self.body = ET.SubElement(self.env, "soapenv:Body")
        self.xml_response = ''

        for k, v in kwargs.items():
            self.obj = v
            self._request = k
            self.data = v.to_xml(self._request)
            self._response = k.replace("Request", "Response")

    def _send(self, method, xmldata):
        "Send the final SOAP message"
        global GSX_ENV, GSX_REGION, GSX_HOSTS, GSX_URL, GSX_TIMEOUT

        try:
            self._url = GSX_URL.format(env=GSX_HOSTS[GSX_ENV], region=GSX_REGION)
        except KeyError:
            raise GsxError('GSX environment (%s) must be one of: %s' % (GSX_ENV,
                           ', '.join(GSX_HOSTS.keys())))

        logging.debug(self._url)
        logging.debug(xmldata)

        headers = {
            'User-Agent'    : "py-gsxws %s" % VERSION,
            'Content-type'  : 'text/xml; charset="UTF-8"',
            'SOAPAction'    : '"%s"' % method
        }

        # Send GSX client certs with every request
        try:
            self.gsx_cert = os.environ['GSX_CERT']
            self.gsx_key  = os.environ['GSX_KEY']
        except KeyError as e:
            raise GsxError('SSL configuration error: %s' % e)

        try:
            return requests.post(self._url, cert=(self.gsx_cert, self.gsx_key),
                                 data=xmldata,
                                 headers=headers,
                                 timeout=GSX_TIMEOUT)
        except Exception as e:
            raise GsxError('GSX connection failed: %s' % e)

    def _submit(self, method, response=None, raw=False):
        "Constructs and submits the final SOAP message"
        root = ET.SubElement(self.body, self.obj._namespace + method)

        if method is "Authenticate":
            root.append(self.data)
        else:
            request_name = method + "Request"

            # @hack for Reported Symptom/Issue API which nests two ReportedSymptomIssueRequest elements
            if method.endswith("Request"):
                request_name = method

            # @hack FetchDiagnosticDetails doesn't follow the naming conventions
            if method.endswith('FetchDiagnosticDetails'):
                request_name = 'FetchDiagnosticDetailsRequestData'

            # @hack FetchDiagnosticSuites doesn't follow the naming conventions
            if method.endswith('FetchDiagnosticSuites'):
                request_name = 'FetchDiagnosticSuitesRequestData'

            # @hack RunDiagnosticTest doesn't follow the naming conventions
            if method.endswith('RunDiagnosticTest'):
                request_name = 'RunDiagnosticTestRequestData'

            request = ET.SubElement(root, request_name)
            request.append(GSX_SESSION)

            if self._request == request_name:
                # Some requests lack a top-level container
                request.extend(self.data)
            else:
                request.append(self.data)

        data = ET.tostring(self.env, "UTF-8")
        res = self._send(method, data)
        xml = res.text.encode('utf-8')
        self.xml_response = xml

        logging.debug("Response: %s %s %s" % (res.status_code, res.reason, xml))

        if res.status_code > 200:
            raise GsxError(xml=xml, url=self._url, status=res.status_code)

        if raw is True:
            return ET.fromstring(self.xml_response)

        response = response or self._response
        self.objects = objectify.parse(xml, response)
        return self.objects

    def __unicode__(self):
        return ET.tostring(self.env)

    def __str__(self):
        return unicode(self).encode('utf-8')


class GsxResponse:
    def __init__(self, http_response, xml, el_method, el_response, raw=False):
        self.result = None          # result status
        self.response = None        # objectified result
        self.el_method = el_method
        self.el_response = el_response

        if http_response.status_code > 200:
            raise GsxError(xml=xml, url=self._url)

        self.response = objectify.parse(xml, self.el_response)

        logging.debug("Response: %s %s %s" % (http_response.status_code, http_response.reason, xml))

        if raw is True:
            return ET.fromstring(self.xml_response)

        if hasattr(self.response, 'outCome'):
            self.result = self.response.outCome
            if self.result == 'STOP':
                raise GsxError(message=self.response.messages, code=self.result)

    def get_response(self):
        if self.response is None:
            raise GsxError('GSX request returned empty result')

        return self.response if len(self.response) > 1 else self.response[0]


class GsxObject(object):
    """XML/SOAP representation of a GSX object."""

    _data = {}

    def __init__(self, *args, **kwargs):
        self._data = {}
        self._formats = get_format()

        for a in args:
            k = validate(a)
            if k is not None:
                kwargs[k] = a

        for k, v in kwargs.items():
            self.__setattr__(k, v)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super(GsxObject, self).__setattr__(name, value)
            return

        # Kind of a lame way to identify files, but it's the best
        # we have for Django's File class right now...
        if hasattr(value, "fileno"):
            if not hasattr(self, "fileName"):
                self.fileName = value.name

            value = base64.b64encode(value.read())

        if isinstance(value, bool):
            value = "Y" if value else "N"

        if isinstance(value, int):
            value = str(value)

        if isinstance(value, date):
            value = value.strftime(self._formats['df'])

        if isinstance(value, time):
            value = value.strftime(self._formats['tf'])

        self._data[name] = value

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError("Invalid attribute: %s" % name)

    def unset(self, prop):
        del(self._data[prop])

    def _submit(self, arg, method, ret=None, raw=False):
        """Shortcut for submitting a GsxObject."""
        self._req = GsxRequest(**{arg: self})
        result = self._req._submit(method, ret, raw)
        if result is None:
            raise GsxError('GSX request returned empty result')
        return result if len(result) > 1 else result[0]

    def to_xml(self, root):
        """
        Returns this object as an XML Element

        >>> GsxObject(spam='eggs', spices=[{'salt': 'pepper'}]) #doctest: +ELLIPSIS
        <__main__.GsxObject object at 0x...
        >>> GsxObject(spam='eggs', spices=[{'salt': 'pepper'}]).to_xml('blaa') #doctest: +ELLIPSIS
        <Element 'blaa' at 0x...
        """
        root = ET.Element(root)
        for k, v in self._data.items():
            if isinstance(v, list):
                for e in v:
                    if isinstance(e, GsxObject):
                        i = ET.SubElement(root, k)
                        i.extend(e.to_xml(k))
            else:
                el = ET.SubElement(root, k)
                if isinstance(v, basestring):
                    el.text = v
                if isinstance(v, GsxObject):
                    el.extend(v.to_xml(k))

        return root

    def dumps(self):
        req = GsxRequest(**{'GsxObject': self})
        return ET.tostring(req.data, encoding='utf-8')

    def __str__(self):
        return str(self._data)


class GsxRequestObject(GsxObject):
    "The GSX-friendly representation of this GsxObject"
    pass


class GsxSession(GsxObject):

    _cache = None
    _namespace = "glob:"

    def __init__(self, user_id, sold_to, language, timezone):
        global GSX_ENV

        self.userId = user_id
        self.languageCode = language
        self.userTimeZone = timezone
        self.serviceAccountNo = str(sold_to)

        self._session_id = ""

        md5 = hashlib.md5()
        md5.update(user_id + self.serviceAccountNo + GSX_ENV)

        self._cache_key = md5.hexdigest()
        self._cache = GsxCache(self._cache_key)

    def get_session(self):
        session = ET.Element("userSession")
        session_id = ET.SubElement(session, "userSessionId")
        session_id.text = self._session_id
        return session

    def login(self):
        global GSX_SESSION
        session = self._cache.get("session")

        if session is not None:
            GSX_SESSION = session
        else:
            self._req = GsxRequest(AuthenticateRequest=self)
            result = self._req._submit("Authenticate")
            self._session_id = str(result.userSessionId)
            GSX_SESSION = self.get_session()
            self._cache.set("session", GSX_SESSION)

        return GSX_SESSION

    def logout(self):
        return GsxRequest(LogoutRequest=self)


def connect(user_id, sold_to,
            environment=GSX_ENV,
            language=GSX_LANG,
            timezone="CEST",
            region=GSX_REGION,
            locale=GSX_LOCALE):
    """
    Establish connection with GSX Web Services.

    Returns the session ID of the new connection.
    """
    global GSX_ENV
    global GSX_LANG
    global GSX_LOCALE
    global GSX_REGION

    GSX_ENV     = environment
    GSX_LANG    = language
    GSX_REGION  = region
    GSX_LOCALE  = locale

    act = GsxSession(user_id, sold_to, language, timezone)
    return act.login()


if __name__ == '__main__':
    import doctest
    import argparse

    parser = argparse.ArgumentParser(description="Communicate with GSX Web Services")

    parser.add_argument("user_id")
    parser.add_argument("sold_to")
    parser.add_argument("--language", default=GSX_LANG)
    parser.add_argument("--timezone", default=GSX_TIMEZONE)
    parser.add_argument("--environment", default=GSX_ENV)
    parser.add_argument("--region", default=GSX_REGION)

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    connect(**vars(args))
    doctest.testmod()
