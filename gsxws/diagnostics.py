# -*- coding: utf-8 -*-

from core import GsxObject, GsxError


class Diagnostics(GsxObject):
    _namespace = "glob:"

    def initiate(self):
        """
        The Initiate iOS Diagnostic API allows users to initiate 
        Diagnostic Request for iOS Device.
        Then it sends the diagnostic URL (diags://<Ticket Number >) as an email or SMS 
        to the email address or phone number based on the information provided 
        in the request. The ticket is generated within GSX system.
        """
        self._submit("initiateRequestData", "InitiateIOSDiagnostic",
                     "initiateResponseData")

        return self._req.objects.ticketNumber

    def fetch(self):
        """
        The Fetch Diagnostic Details API allows users to fetch diagnostic test details 
        of all Devices. This API will retrieve diagnostic tests performed on 
        the device as well as profile and report data for the tests. 

        >>> Diagnostics(diagnosticEventNumber='12942008007242012052919').fetch()
        """
        self._submit("diagnosticDetailsRequestData", "FetchDiagnosticDetails",
                     "diagnosticDetailsResponseData")
        return self._req.objects

    def fetch_suites(self):
        """
        The Fetch Diagnostic Suite API allows user to fetch associated 
        Diagnostic Suite IDs for a given serial number 
        from Apple Diagnostic Repository irrespective of Service Account. 
        """
        suites = []
        self._submit("diagnosticSuitesRequestData", "FetchDiagnosticSuites",
                     "diagnosticSuitesResponseData")
        for i in self._req.objects.diagnosticSuiteDetails:
            suites.append((i.suiteId, i.suiteName,))

        return suites

    def fetch_dc_url(self):
        """
        The Fetch Diagnostic Console URL API provides the technician with 
        the AST 2 Diagnostic Console URL, so the technician 
        can easily access the interactive diagnostic suites.
        """
        self._submit("fetchDCURLRequestData", "FetchDiagnosticConsoleURL",
                     "fetchDCURLResponseData")
        return self._req.objects.diagnosticConsoleURL

    def events(self):
        """
        The Fetch Diagnostic Event Numbers API allows users to retrieve all
        diagnostic event numbers associated with provided input
        (serial number or alternate device ID).
        """
        self._submit("lookupRequestData", "FetchDiagnosticEventNumbers",
                     "diagnosticEventNumbers")
        return self._req.objects

    def run_test(self):
        """
        The Run Diagnostic Test API allows users to run a specific or 
        all the diagnostic tests on a device.
        User has to first invoke Fetch Diagnostic Suite API 
        to fetch associated suite ID's for given serial number.
        """
        self._submit("diagnosticTestRequestData", "RunDiagnosticTest",
                     "diagnosticTestResponseData")
        return self._req.objects
        