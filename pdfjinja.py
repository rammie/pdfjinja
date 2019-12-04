# -*- coding: utf-8 -*-
""" Use jinja2 templates to fill and sign PDF forms. """

import argparse
import datetime
import logging
import sys
import os
import time

from fdfgen import forge_fdf
from jinja2 import Environment, TemplateSyntaxError
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.pdftypes import PDFObjRef
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from subprocess import Popen, PIPE
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    try:
        from StringIO import StringIO as BytesIO
    except ImportError:
        from io import BytesIO

PY3 = False
if sys.version_info[0] == 3:
    PY3 = True


try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass


logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class Attachment(object):

    label_x = 8

    label_y = 8

    font = None

    fontsize = 12

    def __init__(self, data, dimensions=None, text=None, font=None):
        img = Image.open(data)
        self.img = img
        self.dimensions = dimensions or (0, 0, img.size[0], img.size[1])

        if img.mode == "RGBA":
            self.img = Image.new("RGB", img.size, (255, 255, 255))
            mask = img.split()[-1]  # 3 is the alpha channel
            self.img.paste(img, mask=mask)

        if font is not None:
            self.font = font

        if text is not None:
            font = ImageFont.truetype(self.font, self.fontsize)
            lines = text.split(os.linesep)
            dims = [font.getsize(l) for l in lines]
            w = sum(w for w, h in dims)
            h = sum(h for w, h in dims)

            self.label = Image.new("RGB", (w, h), (255, 255, 255))
            draw = ImageDraw.Draw(self.label)

            y = 0
            for (lw, lh), line in zip(dims, lines):
                draw.text((0, y), line, (0, 0, 0), font=font)
                y += lh

    def pdf(self):
        stream = BytesIO()
        pdf = canvas.Canvas(stream)
        w, h = self.img.size
        pdf.drawImage(ImageReader(self.img), *self.dimensions)

        if hasattr(self, "label"):
            w, h = self.label.size
            x, y = self.label_x, self.label_y
            pdf.drawImage(ImageReader(self.label), x, y, w, h)

        pdf.save()
        return PdfFileReader(stream).getPage(0)


class PdfJinja(object):

    Attachment = Attachment

    def __init__(self, filename, jinja_env=None):
        self.jinja_env = Environment()
        self.context = None
        self.fields = {}
        self.watermarks = []
        self.filename = filename
        self.register_filters()
        with open(filename, "rb") as fp:
            self.parse_pdf(fp)

    def register_filters(self):
        self.jinja_env.filters.update(dict(
            date=self.format_date,
            paste=self.paste,
            check=self.check,
            X=lambda v: "Yes" if v else "Off",
            Y=lambda v: "Yes" if v else "Off",
        ))

    def check(self, data):
        self.rendered[self.context["name"]] = bool(data)
        return bool(data)

    def paste(self, data):
        rect = self.context["rect"]
        x, y = rect[0], rect[1]
        w, h = rect[2] - x, rect[3] - y
        pdf = self.Attachment(data, dimensions=(x, y, w, h)).pdf()
        self.watermarks.append((self.context["page"], pdf))
        return " "

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
            page.annots and self.parse_annotations(pgnum, page)

    def parse_annotations(self, pgnum, page):
        annots = page.annots
        if isinstance(page.annots, PDFObjRef):
            annots = page.annots.resolve()

        annots = (
            r.resolve() for r in annots if isinstance(r, PDFObjRef))

        widgets = (
            r for r in annots if r["Subtype"].name == "Widget")

        for ref in widgets:
            data_holder = ref
            try:
                name = ref["T"]
            except KeyError:
                ref = ref['Parent'].resolve()
                name = ref['T']
            field = self.fields.setdefault(name, {"name": name, "page": pgnum})
            if "FT" in data_holder and data_holder["FT"].name in ("Btn", "Tx", "Ch", "Sig"):
                field["rect"] = data_holder["Rect"]

            if "TU" in ref:
                tmpl = ref["TU"]

                try:
                    if ref["TU"].startswith(b"\xfe"):
                        tmpl = tmpl.decode("utf-16")
                    else:
                        tmpl = tmpl.decode("utf-8")
                    field["template"] = self.jinja_env.from_string(tmpl)
                except (UnicodeDecodeError, TemplateSyntaxError) as err:
                    logger.error("%s: %s %s", name, tmpl, err)


    def template_args(self, data):
        kwargs = {}
        today = datetime.datetime.today().strftime("%m/%d/%y")
        kwargs.update({"today": today})
        kwargs.update(data)
        return kwargs

    def format_date(self, datestr):
        if not datestr:
            return ""

        ts = time.strptime(datestr, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt = datetime.datetime.fromtimestamp(time.mktime(ts))
        return dt.strftime("%m/%d/%y")

    def exec_pdftk(self, data):
        fdf = forge_fdf("", data.items(), [], [], [], checkbox_checked_name="Yes")
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
        if stderr.strip():
            raise IOError(stderr)

        return BytesIO(stdout)

    def __call__(self, data, attachments=[], pages=None):
        self.rendered = {}
        for field, ctx in self.fields.items():
            if "template" not in ctx:
                continue

            self.context = ctx
            kwargs = self.template_args(data)
            template = self.context["template"]

            try:
                rendered_field = template.render(**kwargs)
            except Exception as err:
                logger.error("%s: %s %s", field, template, err)
            else:
                # Skip the field if it is already rendered by filter
                if field not in self.rendered:
                    if PY3:
                        field = field.decode('utf-8')
                    self.rendered[field] = rendered_field

        filled = PdfFileReader(self.exec_pdftk(self.rendered))
        for pagenumber, watermark in self.watermarks:
            page = filled.getPage(pagenumber)
            page.mergePage(watermark)

        output = PdfFileWriter()
        pages = pages or range(filled.getNumPages())
        for p in pages:
            output.addPage(filled.getPage(p))

        for attachment in attachments:
            output.addBlankPage().mergePage(attachment.pdf())

        return output


def parse_args(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "-f", "--font", type=str, default=None,
        help="TTF font for attachment labels.")

    parser.add_argument(
        "-j", "--json", type=argparse.FileType("rb"), default=sys.stdin,
        help="JSON format file with data.")

    parser.add_argument(
        "-p", "--page", type=str, default=None,
        help="Pages to select (Comma separated).")

    parser.add_argument(
        "pdf", type=str,
        help="PDF form with jinja2 tooltips.")

    parser.add_argument(
        "out", nargs="?", type=argparse.FileType("wb"), default=sys.stdout,
        help="PDF filled with the form data.")

    return parser.parse_args()


def main():
    logging.basicConfig()
    args = parse_args(__doc__)
    pdfparser = PdfJinja(args.pdf)
    pages = args.page and args.page.split(",")

    import json
    json_data = args.json.read().decode('utf-8')
    data = json.loads(json_data)
    Attachment.font = args.font
    attachments = [
        Attachment(**kwargs) for kwargs in data.pop("attachments", [])
    ]

    output = pdfparser(data, attachments, pages)
    output.write(args.out)


if __name__ == "__main__":
    main()
