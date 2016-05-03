pdfjinja
========

.. image:: https://img.shields.io/badge/License-MIT%20License-blue.svg
  :target: https://raw.githubusercontent.com/rammie/pdfjinja/master/LICENSE

.. image:: https://api.travis-ci.org/rammie/pdfjinja.png?branch=master
  :target: https://travis-ci.org/rammie/pdfjinja


Use jinja templates to fill and sign PDF forms.

You can use this library to fill out a PDF form using data from an external
source such as a database or an excel file. Use a PDF editing software to edit
the form and specifiy a jinja template in the tooltip property of the form
field.


Dependencies
------------

You'll need the pdftk library. If you want to paste images, you'll need whatever
dependencies are necessary for Pillow to load your preferred image format.
Most of the packages below are taken from the Pillow documentation. You don't
need all of them. In most cases, just pdftk will do.


Ubuntu::

    apt-get install python-dev python-pip libtiff5-dev libjpeg8-dev \
        zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev \
        tk8.6-dev python-tk pdftk libmagickwand-dev


OSX::

  * Install pdftk (https://www.pdflabs.com/tools/pdftk-server/).
  * Install dependencies for Pillow if you want to paste images.


Windows::

  * Install pdftk (https://www.pdflabs.com/tools/pdftk-server/).
  * Install dependencies for Pillow if you want to paste images.


Installation
------------

You can install pdfjinja with pip::

    $ pip install pdfjinja
    $ pdfjinja -h


Usage:
------

See examples/sample.pdf for an example of a pdf file with jinja templates.
The template strings are placed in the tooltip property for each form field
in the pdf.

See examples/output.pdf for the output. The data that the form is filled with
comes from examples/sample.json.


Basic::


    $ pdfjinja -j examples/simple.json examples/sample.pdf examples/output.pdf

Attachments::

    $ pdfjinja --font examples/open-sans/regular.ttf \
               --json examples/sample.json \
               examples/sample.pdf \
               examples/output.pdf


Python::

    from pdfjinja import PdfJinja

    pdfjinja = PdfJinja('form.pdf')
    pdfout = pdfjinja(dict(firstName='Faye', lastName='Valentine'))
    pdfout.write(open('filled.pdf', 'wb'))


If you are using this with Flask as a webserver::

    from flask import current_app
    from pdfjinja import PdfJinja
    pdf = PdfJinja('form.pdf', current_app.jinja_env)
