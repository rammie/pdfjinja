# -*- coding: utf-8 -*-
""" Use jinja2 templates to fill and sign PDF forms. """

__version__ = "0.0.1"


import argparse
import datetime
import logging
import cStringIO as StringIO
import os
import sys
import time

from fdfgen import forge_fdf
from jinja2 import Environment
from jinja2.exceptions import UndefinedError
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.pdftypes import PDFObjRef
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from PIL import Image, ImageDraw, ImageFont
from pyPdf import PdfFileWriter, PdfFileReader
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from subprocess import Popen, PIPE


try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass


logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class Attachment(object):

    def __init__(self, data, text):
        self.data = data
        self.text = text

    @property
    def lines(self):
        if self.text:
            return self.text.split(os.linesep)
        return []


class PdfJinja(object):

    def __init__(self, filename, jinja_env=None):
        self.jinja_env = Environment()
        self.fields = {}
        self.watermarks = []
        self.filename = filename
        self.register_filters()
        with open(filename, "rb") as fp:
            self.parse_pdf(fp)

    def register_filters(self):
        self.jinja_env.filters.update(dict(
            date=self.format_date,
            X=lambda v: "X" if v else " ",
            Y=lambda v: "Y" if v else "N",
        ))

    def parse_pdf(self, fp):
        parser = PDFParser(fp)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        device = PDFDevice(rsrcmgr)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        for pgnum, page in enumerate(PDFPage.create_pages(doc)):
            interpreter.process_page(page)
            page.annots and self.parse_annotations(page)

    def parse_annotations(self, page):
        annots = page.annots
        if isinstance(page.annots, PDFObjRef):
            annots = page.annots.resolve()

        annots = (
            r.resolve() for r in annots if isinstance(r, PDFObjRef))

        widgets = (
            r for r in annots if r["Subtype"].name == "Widget" and "T" in r)

        for ref in widgets:
            name = ref["T"]
            field = self.fields.setdefault(name, {})
            if "FT" in ref and ref["FT"].name in ("Btn", "Tx", "Ch"):
                field["rect"] = ref["Rect"]
            if "TU" in ref:
                try:
                    tmpl = ref["TU"]
                    field["template"] = self.jinja_env.from_string(tmpl)
                except UnicodeDecodeError as err:
                    logger.error("%s: %s %s", name, tmpl, err)

    def get_watermark(self, data, pdffield):
        img = Image.open(data)
        img = img.crop((22, 0, 278, 70))
        img.load()

        background = Image.new("RGB", img.size, (255, 255, 255))
        mask = img.split()[-1]  # 3 is the alpha channel
        background.paste(img, mask=mask)

        stream = StringIO.StringIO()
        imgpdf = canvas.Canvas(stream)
        rect = pdffield["rect"]
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        imgpdf.drawImage(ImageReader(background), rect[0], rect[1], w, h)
        imgpdf.save()

        stream.seek(0)
        return PdfFileReader(stream).getPage(0)

    def template_args(self, data):
        kwargs = {}
        kwargs.update({
            "paste": self.paste,
            "today": datetime.datetime.today().strftime("%m/%d/%y")
        })
        kwargs.update(data)
        return kwargs

    def format_date(self, datestr):
        if not datestr:
            return ""

        ts = time.strptime(datestr, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt = datetime.datetime.fromtimestamp(time.mktime(ts))
        return dt.strftime("%m/%d/%y")

    def paste(self, fieldname, data, pagenumber):
        try:
            pdffield = self.fields[fieldname]
        except (KeyError, UndefinedError):
            logger.error("Unable to watermark %s", fieldname, exc_info=True)
            return " "
        else:
            watermark = self.get_watermark(data, pdffield)
            self.watermarks.append((pagenumber, watermark))

    def exec_pdftk(self, data):
        fdf = forge_fdf("", data.items(), [], [], [])
        args = [
            "pdftk",
            self.filename,
            "fill_form", "-",
            "output", "-",
            "dont_ask",
            "flatten"
        ]

        p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate(fdf)
        if stderr:
            logger.error(stderr)

        return StringIO.StringIO(stdout)

    def attach(self, attachment):
        docimage = Image.open(attachment.data)

        labelimg = Image.new("RGB", (400, 100), (255, 255, 255))
        draw = ImageDraw.Draw(labelimg)
        font = ImageFont.truetype(attachment.font, 12)

        y_text, w = 0, 400
        for line in attachment.lines:
            width, height = font.getsize(line)
            draw.text((0, y_text), line, (0, 0, 0), font=font)
            y_text += height

        docstream = StringIO.StringIO()
        docpdf = canvas.Canvas(docstream)
        w, h = docimage.size
        docpdf.drawImage(ImageReader(docimage), 8, 200, w, h)

        w, h = labelimg.size
        docpdf.drawImage(ImageReader(labelimg), 8, 675, w, h)

        docpdf.save()
        return PdfFileReader(docstream).getPage(0)

    def __call__(self, data, attachments=[], pages=None):
        rendered = {}
        for field, v in self.fields.items():
            if "template" in v:
                try:
                    template = v["template"]
                    kwargs = self.template_args(data)
                    rendered[field] = template.render(**kwargs)
                except UndefinedError as err:
                    logger.error("%s: %s %s", field, template, err)

        filled = PdfFileReader(self.exec_pdftk(rendered))
        for pagenumber, watermark in self.watermarks:
            page = filled.getPage(pagenumber)
            page.mergePage(watermark)

        output = PdfFileWriter()
        pages = pages or xrange(filled.getNumPages())
        for p in pages:
            output.addPage(filled.getPage(p))

        for attachment in attachments or []:
            page = output.addBlankPage()
            page.mergePage(self.attach(data, attachment))

        return output


def parse_args(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-j', '--json', type=argparse.FileType('rb'), default=sys.stdin,
        help="JSON format file with data.")

    parser.add_argument(
        '-p', '--page', type=str, default=None,
        help="Pages to select (Comma separated).")

    parser.add_argument(
        'pdf', type=str,
        help="PDF form with jinja2 tooltips.")

    parser.add_argument(
        'out', nargs='?', type=argparse.FileType('wb'), default=sys.stdout,
        help="PDF filled with the form data.")

    return parser.parse_args()


def main():
    logging.basicConfig()
    args = parse_args(__doc__)
    pdfparser = PdfJinja(args.pdf)
    pages = args.page and args.page.split(",")

    import json
    data = json.loads(args.json.read())

    output = pdfparser(data, pages)
    output.write(args.out)


if __name__ == "__main__":
    main()
