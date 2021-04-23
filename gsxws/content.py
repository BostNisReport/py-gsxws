# -*- coding: utf-8 -*-

class Content(GsxObject):
    def fetch_image(self, url):
        """
        The Fetch Image API allows users to get the image file from GSX,
        for the content articles, using the image URL.
        The image URLs will be obtained from the image html tags
        in the data from all content APIs.
        """
        dt = self._make_type('ns3:fetchImageRequestType')
        dt.imageRequest = {'imageUrl': url}

        return self.submit('FetchImage', dt, 'contentResponse')
