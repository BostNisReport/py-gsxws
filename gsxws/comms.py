# -*- coding: utf-8 -*-

from core import GsxObject


class Communication(GsxObject):

    _namespace = "glob:"

    def get_content(self):
        """
        The Fetch Communication Content API allows the service providers/depot/carriers
        to fetch the communication content by article ID from the service news channel.
        """
        return self._submit("lookupRequestData", "FetchCommunicationContent",
                            "communicationMessage")

    def get_articles(self):
        """
        The Fetch Communication Articles API allows the service partners
        to fetch all the active communication message IDs.
        """
        return self._submit("lookupRequestData", "FetchCommunicationArticles",
                            "communicationMessage")

    def acknowledge(self):
        """
        The Acknowledge Communication API allows the service providers/depot/carriers to 
        update the status as Read/UnRead. 
        """
        return self._submit("communicationRequest", "AcknowledgeCommunication",
                            "communicationResponse")


def fetch(**kwargs):
    return Communication(**kwargs).get_articles()


def content(id):
    return Communication(articleID=id).get_content()


def ack(id, status):
    ack = GsxObject(articleID=id)
    ack.acknowledgeType = status
    return Communication(acknowledgement=ack).acknowledge()


if __name__ == '__main__':
    import sys
    import doctest
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:4])
    doctest.testmod()
