# -*- coding: utf-8 -*-

import os.path
from core import GsxObject
from lookups import Lookup

STATUS_OPEN = 'O'
STATUS_CLOSED = 'C'
STATUS_ESCALATED = 'E'

STATUSES = (
    (STATUS_OPEN, 'Open'),
    (STATUS_CLOSED, 'Closed'),
    (STATUS_ESCALATED, 'Escalated'),
)

CONTEXTS = (
    ('1', 'Serial Number'),
    ('2', 'Alternate Device Id'),
    ('3', 'Dispatch Id'),
    ('4', 'SRO Number'),
    ('5', 'Invoice Number'),
    ('6', 'Order Number'),
    ('7', 'SSO number'),
    ('8', 'Part Number'),
    ('9', 'EEE Code'),
    ('10', 'Tracking Number'),
    ('11', 'Module Serial Number'),
    ('12', 'Escalation Id'),
    ('13', 'Consignment Increase Order'),
    ('14', 'Consignment Return Order'),
)

ISSUE_TYPES = (
    ('AMQ', 'Account Management Question'),
    ('UQ', 'GSX Usage Question'),
    ('OSI', 'Order Status Issue'),
    ('PRI', 'Part Return Issue'),
    ('PPOR', 'Problem Placing Order/Repair'),
    ('PUR', 'Problem Updating Repair'),
    ('SCI', 'Shipping Carrier Issue'),
    ('SES', 'Service Excellence Scoring'),
    ('ARF', 'Apple Retail Feedback'),
    ('DF', 'Depot Feedback'),
    ('FS', 'GSX Feedback/Suggestion'),
    ('WS', 'GSX Web Services (API)'),
    ('SEPI', 'Service Excellence Program Information'),
    ('TTI', 'Technical or Troubleshooting Issue'),
    ('DTA', 'Diagnostic Tool Assistance'),
    ('BIQ', 'Billing or Invoice Question'),
    ('SESC', 'Safety Issue'),
)


class FileAttachment(GsxObject):
    def __init__(self, fp):
        super(FileAttachment, self).__init__()
        self.fileName = os.path.basename(fp)
        self.fileData = open(fp, 'r')


class Escalation(GsxObject):
    _namespace = 'asp:'

    def create(self):
        """
        The Create General Escalation API allows users to create
        a general escalation in GSX. The API was earlier known as GSX Help.
        """
        return self._submit("escalationRequest", "CreateGeneralEscalation",
                            "escalationConfirmation")

    def update(self):
        """
        The Update General Escalation API allows Depot users to
        update a general escalation in GSX.
        """
        return self._submit("escalationRequest", "UpdateGeneralEscalation",
                            "escalationConfirmation")

    def lookup(self):
        """
        The General Escalation Details Lookup API allows to fetch details
        of a general escalation created by AASP or a carrier.
        """
        return Lookup(escalationId=self.escalationId).lookup("GeneralEscalationDetailsLookup")

    def get_notes(self):
        """
        Returns all the notes of this escalation.
        Should probably be run after a lookup()
        """
        return self.objects.escalationNotes.iterchildren()


class Context(GsxObject):
    def __init__(self, ctype, cid):
        super(Context, self).__init__()
        self.contextType = ctype
        self.contextID = cid

