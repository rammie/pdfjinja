import json
import os
import cStringIO as StringIO
import sys
import unittest

from contextlib import contextmanager
from pdfjinja import PdfJinja


class PdfJinjaTestCase(unittest.TestCase):

    datadir = os.path.join(os.path.dirname(__file__), "examples")

    def setUp(self):
        pdffile = os.path.join(self.datadir, "sample.pdf")
        jsonfile = os.path.join(self.datadir, "sample.json")
        self.data = json.loads(open(jsonfile).read())
        self.pdfjinja = PdfJinja(pdffile)

    def tearDown(self):
        del self.data
        del self.pdfjinja

    def assertIsNone(self, value):
        self.assertTrue(value is None, '%r is not None' % value)

    def assertIsNotNone(self, value):
        self.assertFalse(value is None)

    def test_init(self):
        output = self.pdfjinja(self.data)
        outfile = StringIO.StringIO()
        output.write(outfile)
        outfile.seek(0)
        self.assertTrue(len(outfile.read()) > 0, "Output PDF is not empty.")

    @contextmanager
    def assertRaisesCtx(self, exc_class):
        try:
            yield
        except exc_class:
            return
        else:
            raise AssertionError('Exception %s not raised.' % exc_class)


if __name__ == '__main__':
    unittest.main(argv=sys.argv)
