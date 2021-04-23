# -*- coding: utf-8 -*-
"gsxws/repairs.py"

import sys
import logging

from core import GsxObject, GsxError, validate
from lookups import Lookup

REPAIR_TYPES = (
    ('CA', 'Carry-In/Non-Replinished'),
    ('NE', 'Return Before Replace'),
    ('NT', 'No Trouble Found'),
    ('ON', 'Onsite (Indirect/Direct)'),
    ('RR', 'Repair Or Replace/Whole Unit Mail-In'),
    ('WH', 'Mail-In'),
)

REPAIR_STATUSES = (
    ('AWTP', 'Awaiting Parts'),
    ('AWTR', 'Parts Allocated'),
    ('BEGR', 'In Repair'),
    ('RFPU', 'Ready for Pickup'),
)

COVERAGE_STATUSES = (
    ('CC', 'Custom Bid Contracts'),
    ('CS', 'Customer Satisfaction'),
    ('DO', 'DOA Coverage'),
    ('LI', 'Apple Limited Warranty'),
    ('MU', 'Missing Upon First Use'),
    ('OO', 'Out of Warranty (no coverage)'),
    ('PA', 'AppleCare Parts Agreement'),
    ('PP', 'AppleCare Protection Plan'),
    ('QP', 'Quality Program'),
    ('RA', 'AppleCare Repair Agreement'),
    ('RE', 'Repeat Service'),
    ('G9', 'Pending Coverage Check'),
    ('TC', 'Edu/Govt Warranty (Australia)'),
    ('PT', 'Additional Part Coverage'),
    ('EC', 'Additional Service Coverage'),
    ('C1', 'NEW - AppleCare Protection Plan'),
    ('VW', 'Consumer Law Coverage'),
)


class SymptomIssue(GsxObject):
    """
    The Reported Symptom/Issue API allows partners to fetch the information
    related to symptoms and issues. If all the validations go through,
    api returns a list of valid symptoms/issues according to the input data.
    Otherwise api returns appropriate error message.
    """

    _namespace = "asp:"

    def fetch(self):
        result = []
        self._submit("requestData", "ReportedSymptomIssue",
                     "ReportedSymptomIssueResponse")
        r = self._req.objects.reportedSymptomIssueResponse

        # This may sometimes come back empty...
        if r is None:
            raise GsxError('Symptom/Issue code search failed')

        if r.symptoms is not None:
            for s in r.symptoms:
                result.append((s.reportedSymptomCode, s.reportedSymptomDesc,))

        if r.issues is not None:
            for s in r.issues:
                result.append((s.reportedIssueCode, s.reportedIssueDesc,))

        return result


class CompTiaCode(GsxObject):
    """
    Data type used to provide comptia codes
    """
    comptiaCode = ""
    comptiaModifier = ""
    comptiaGroup = ""
    technicianNote = ""


class Customer(GsxObject):
    """
    Customer address for GSX

    >>> Customer(adressLine1='blaa')._data
    {'adressLine1': 'blaa'}
    """
    city = ""
    region = ""
    country = ""
    state = "ZZ"
    zipCode = ""
    lastName = ""
    firstName = ""
    adressLine1 = ""
    emailAddress = ""
    primaryPhone = ""


class RepairOrderLine(GsxObject):
    partNumber = ""
    comptiaCode = ""
    comptiaModifier = ""


class ComponentCheck(GsxObject):
    component = ""
    serialNumber = ""


class ServicePart(GsxObject):
    "A generic service part (for PartInfo and whatnot)"
    def __init__(self, number, *args, **kwargs):
        super(ServicePart, self).__init__(*args, **kwargs)

        if not validate(number, "partNumber"):
            raise ValueError("Invalid part number: %s" % number)

        self.partNumber = number


class Repair(GsxObject):
    "Base class for the different GSX Repair types"
    def __init__(self, number=None, **kwargs):
        self._namespace = "asp:"
        super(Repair, self).__init__(**kwargs)
        if number is not None:
            self.dispatchId = number

    def update_sn(self, parts):
        """
        Description
        The Update Serial Number API allows the service providers to update
        the module serial numbers.

        Context:
        The API is not applicable for whole unit replacement
        serial number entry (see KGB serial update).

        >>> Repair('G135762375').update_sn(ServicePart('661-4964', oldSerialNumber='W882300FK22YA'))
        Traceback (most recent call last):
        ...
        GsxError: This repair cannot be updated.
        """
        self.partInfo = parts
        if hasattr(self, "dispatchId"):
            self.repairConfirmationNumber = self.dispatchId
            del self._data['dispatchId']

        return self._submit("repairData", "UpdateSerialNumber", "repairConfirmation")

    def update_kgb_sn(self, sn):
        """
        Description:
        The KGB Serial Number Update API is always to be used on
        whole unit repairs that are in a released state.
        This API allows users to provide the KGB serial number for the
        whole unit exchange repairs. It also checks for the privilege
        to create/ update whole unit exchange repairs
        before updating the whole unit exchange repair.

        Context:
        The API is to be used on whole unit repairs that are in a released state.
        This API can be invoked only after carry-in repair creation API.
        """
        self.serialNumber = sn
        if hasattr(self, "dispatchId"):
            self.repairConfirmationNumber = self.dispatchId
            del self._data['dispatchId']

        return self._submit("UpdateKGBSerialNumberRequest",
                            "UpdateKGBSerialNumber",
                            "UpdateKGBSerialNumberResponse")

    def lookup(self):
        """
        Description:
        The Repair Lookup API mimics the front-end repair search functionality.
        It fetches up to 2500 repairs in a given criteria.
        Subsequently, the extended Repair Status API can be used
        to retrieve more details of the repair.

        >>> Repair(repairStatus='Open').lookup() #doctest: +ELLIPSIS
        {'customerName': 'Lepalaan,Filipp',...
        """
        self._namespace = "core:"
        return Lookup(**self._data).repairs()

    def delete(self):
        """
        The Delete Repair API allows the service providers to delete
        the existing GSX Initiated Carry-In, Return Before Replace & Onsite repairs
        which are in Declined-Rejected By TSPS Approver state,
        that do not have an active repair id.
        """
        pass

    def mark_complete(self, numbers=None):
        """
        The Mark Repair Complete API allows a single or an array of
        repair confirmation numbers to be submitted to GSX to be marked as complete.
        """
        self.repairConfirmationNumbers = numbers or self.dispatchId
        return self._submit("MarkRepairCompleteRequest",
                            "MarkRepairComplete",
                            "MarkRepairCompleteResponse")

    def status(self, numbers=None):
        """
        The Repair Status API retrieves the status
        for the submitted repair confirmation number(s).

        >>> Repair('G135773004').status().repairStatus
        u'Closed and Completed'
        """
        self.repairConfirmationNumbers = self.dispatchId
        status = self._submit("RepairStatusRequest", "RepairStatus", "repairStatus")
        self.repairStatus = status.repairStatus
        self._status = status
        return status

    def details(self):
        """
        The Repair Details API includes the shipment information
        similar to the Repair Lookup API.

        >>> Repair('G135773004').details() #doctest: +ELLIPSIS
        {'isACPlusConsumed': 'N', 'configuration': 'IPAD 3RD GEN,WIFI+CELLULAR,16GB,BLACK',...
        """
        self._namespace = "core:"
        details = self._submit("RepairDetailsRequest", "RepairDetails", "lookupResponseData")

        # fix tracking URL, if available
        for i, p in enumerate(details.partsInfo):
            try:
                url = p.carrierURL.replace('<<TRKNO>>', str(p.deliveryTrackingNumber))
                details.partsInfo[i].carrierURL = url
            except AttributeError:
                pass

        self._details = details
        return details


class CannotDuplicateRepair(Repair):
    """
    The Create CND Repair API allows Service Providers to create a repair
    whenever the reported issue cannot be duplicated, and the repair
    requires no parts replacement.
    N01 Unable to Replicate
    N02 Software Update/Issue
    N03 Cable/Component Reseat
    N05 SMC Reset
    N06 PRAM Reset
    N07 Third Party Part
    N99 Other
    """


class CarryInRepair(Repair):
    """
    GSX validates the information and if all of the validations go through,
    it obtains a quote for the repair and creates the carry-in repair

    >>> CarryInRepair(requestReviewByApple=True).requestReviewByApple
    'Y'
    """
    def create(self):
        """
        GSX validates the information and if all of the validations go through,
        it obtains a quote for the repair and creates the carry-in repair.
        """
        self._namespace = "emea:"
        result = self._submit("repairData", "CreateCarryIn", "repairConfirmation")

        if hasattr(result, 'repairConfirmation'):
            if hasattr(result.repairConfirmation, 'messages'):
                raise GsxError(result.repairConfirmation.messages)

        self.dispatchId = result.confirmationNumber
        return result

    def update(self, newdata):
        """
        The Update Carry-In Repair API allows the service providers
        to update the existing  open carry-in repairs.
        This API assists in addition/deletion of parts and addition of notes
        to a repair. On successful update, the repair confirmation number and
        quote for any newly added parts  would be returned.
        In case of any validation error or unsuccessful update, a fault code is issued.
        """
        self._namespace = "asp:"

        if not hasattr(self, "repairConfirmationNumber"):
            self.repairConfirmationNumber = self.dispatchId
            del self._data['dispatchId']

        # Merge old and new data (old data should have Dispatch ID)
        self._data.update(newdata)
        return self._submit("repairData", "UpdateCarryIn", "repairConfirmation")

    def set_techid(self, new_techid):
        return self.update({'technicianId': new_techid})

    def set_status(self, new_status):
        return self.update({'statusCode': new_status})


class IndirectOnsiteRepair(Repair):
    """
    The Create Indirect Onsite Repair API is designed to create the indirect onsite repairs.
    When a service provider travels to the customer location to perform repair
    on a unit eligible for onsite service, they create an indirect repair.
    Once the repair is submitted, it is assigned a confirmation number,
    which is a reference number to identify the repair.
    """
    def create(self):
        self._namespace = "asp:"
        if hasattr(self, "shipTo"):  # Carry-In and OnSite use different field names!
            self.shippingLocation = self.shipTo
            del(self._data['shipTo'])

        if hasattr(self, "poNumber"):
            self.purchaseOrderNumber = self.poNumber
            del(self._data['poNumber'])

        if hasattr(self, "diagnosedByTechId"):
            self.technicianName = self.diagnosedByTechId
            del(self._data['diagnosedByTechId'])

        if hasattr(self, "requestReviewByApple"):
            self.requestReview = self.requestReviewByApple
            del(self._data['requestReviewByApple'])

        return self._submit("repairData", "CreateIndirectOnsiteRepair",
                            "repairConfirmation")


class RepairOrReplace(Repair):
    """
    The Create Repair or Replace API allows users to submit Repair-Or-Replace information to GSX.
    The submissions creates a GSX RoR Repair in the system.
    """
    COVERAGE_OPTIONS = (
        ('N',   'No Damage'),
        ('A1',  'Battery Service'),
        ('A2',  'Returnable Damage'),
        ('A3',  'Non-returnable Damage'),
        ('X',   'Non-returnable damage covered by AppleCare+'),
        ('RPL', 'Replace'),
        ('Z',   'Override to Out of Warranty when part is covered by Variable Warranty'),
    )

    def create(self):
        self._namespace = "asp:"
        return self._submit("repairData", "CreateRepairOrReplace", "repairConfirmation")


class WholeUnitExchange(Repair):
    """
    The Create Whole Unit Exchange API allows the service providers to send
    all the information required to create a whole unit exchange repair.
    GSX validates the information and if all the validations go through,
    it obtains a quote for repair and creates the whole unit exchange repair.
    The quote is sent as part of the response.
    If a validation error occurs, a fault code is issued.
    """
    def create(self):
        self._namespace = "asp:"
        return self._submit("repairData", "CreateWholeUnitExchange", "repairConfirmation")


class MailInRepair(Repair):
    """
    This API allows the submission of Mail-In Repair information into GSX,
    resulting in the creation of a GSX Mail-In Repair. 
    """
    def create(self):
        self._namespace = "asp:"
        return self._submit("repairData", "CreateMailInRepair", "repairConfirmation")
        

if __name__ == '__main__':
    import doctest
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:])
    doctest.testmod()
