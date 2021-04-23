# -*- coding: utf-8 -*-

import logging
from core import GsxObject, GsxCache

MODIFIERS = (
    ("A", "Not Applicable"),
    ("B", "Continuous"),
    ("C", "Intermittent"),
    ("D", "Fails After Warm Up"),
    ("E", "Environmental"),
    ("F", "Configuration: Peripheral"),
    ("G", "Damaged"),
    ("H", "Apple Review"),
)

GROUPS = (
    ('0', "General"),
    ('1', "Visual"),
    ('2', "Displays"),
    ('3', "Mass Storage"),
    ('4', "Input Devices"),
    ('5', "Boards"),
    ('6', "Power"),
    ('7', "Printer"),
    ('8', "Multi-function Device"),
    ('9', "Communication Devices"),
    ('A', "Share"),
    ('B', "iPhone"),
    ('E', "iPod"),
    ('F', "iPad"),
    ('G', "Beats Products"),
    ('W', "Apple Watch"),
)


class CompTIA(GsxObject):
    "Stores and accesses CompTIA codes."
    _namespace = "glob:"

    def __init__(self):
        """
        Initialize CompTIA symptoms from the local JSON file
        """
        self._comptia = {}
        self._cache = GsxCache("comptia")

    def fetch(self):
        """
        Description:
        The CompTIA Codes Lookup API retrieves a list of CompTIA groups and modifiers.

        Context:
        The CompTIA Codes (Symptom Codes) are the current available selections 
        based on the component group code for parts.
        The API can be executed only after valid Authentication.
        Users can use the API at any point to retrieve the CompTIA code and 
        modifier details, in order to create or update repairs.

        >>> CompTIA().fetch() # doctest: +ELLIPSIS
        {u'A': {'989': u'Remote Inoperable', ...
        """
        if self._cache.get('comptia'):
            return self._cache.get('comptia')

        doc = self._submit("ComptiaCodeLookupRequest", "ComptiaCodeLookup",
                           "comptiaInfo", raw=True)
        root = doc.find('.//comptiaInfo')

        for el in root.findall(".//comptiaGroup"):
            group = []
            comp_id = unicode(el[0].text)
            for ci in el.findall("comptiaCodeInfo"):
                group.append((ci[0].text, unicode(ci[1].text)),)

            self._comptia[comp_id] = group

        self._cache.set('comptia', self._comptia)
        return self._comptia

    def symptoms(self, component=None):
        """
        Returns all known CompTIA symptom codes or just the ones
        belonging to the given component code.

        >>> CompTIA().symptoms(0) # doctest: +ELLIPSIS
        {u'B': [(u'B0A', u'Any Camera issue'), ...
        """
        r = dict()

        for g, codes in self._comptia.items():
            r[g] = list()
            for k, v in codes.items():
                r[g].append((k, v,))

        return r[component] if component else r


def fetch():
    """Shortcut for fetching CompTIA data from GSX"""
    return CompTIA().fetch()


if __name__ == '__main__':
    import sys
    import doctest
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:4])
    doctest.testmod()
