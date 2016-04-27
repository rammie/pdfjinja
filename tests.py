import json
import os
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    try:
        from StringIO import StringIO as BytesIO
    except ImportError:
        from io import BytesIO
import sys
import unittest

from pdfjinja import Attachment, PdfJinja


class PdfJinjaTestCase(unittest.TestCase):

    datadir = os.path.join(os.path.dirname(__file__), "examples")

    def setUp(self):
        pdffile = os.path.join(self.datadir, "sample.pdf")
        jsonfile = os.path.join(self.datadir, "sample.json")
        Attachment.font = "examples/open-sans/regular.ttf"
        self.data = json.loads(open(jsonfile).read())
        self.attachments = [
            Attachment(**kwargs) for kwargs in self.data.pop("attachments")
        ]
        self.pdfjinja = PdfJinja(pdffile)

    def tearDown(self):
        del self.data
        del self.pdfjinja

    def test_render(self):
        output = self.pdfjinja(self.data, self.attachments)
        outfile = BytesIO()
        output.write(outfile)
        outfile.seek(0)
        self.assertTrue(len(outfile.read()) > 0, "Output PDF is not empty.")


if __name__ == '__main__':
    unittest.main(argv=sys.argv)
