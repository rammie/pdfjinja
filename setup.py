#!/usr/bin/env python
""" Package install script. """

import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


f = open(os.path.join(os.path.dirname(__file__), "README.rst"))
readme = f.read()
f.close()

setup(
    name="pdfjinja",
    version="1.0.0",
    author="Ram Mehta",
    author_email="ram.mehta@gmail.com",
    url="http://github.com/rammie/pdfjinja/",
    description='Use jinja templates to fill and sign pdf forms.',
    long_description=readme,
    py_modules=["pdfjinja"],
    entry_points={"console_scripts": ["pdfjinja = pdfjinja:main"]},
    install_requires=[
        "fdfgen>=0.13.0",
        "jinja2>=2.8",
        "pdfminer.six==20160202",
        "Pillow>=3.2.0",
        "PyPDF2>=1.25.1",
        "reportlab>=3.3.0"
    ])
