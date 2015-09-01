pdfjinja
========

.. image:: https://api.travis-ci.org/rammie/pdfjinja.png?branch=master
  :target: https://travis-ci.org/rammie/pdfjinja


Use jinja templates to fill and sign PDF forms.

You would like to fill out a PDF form using data from an external source such as a database or an excel file. Use a PDF editing software to edit the form. Use the tooltip field to specifiy a jinja template.


Dependencies
------------

OSX::

    brew install pdftk libtiff libjpeg webp little-cms2


Ubuntu::

    apt-get install python-dev python-pip libtiff5-dev libjpeg8-dev \
        zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev \
        tk8.6-dev python-tk pdftk libmagickwand-dev


Installation
------------

You can install pdfjinja with pip::

    $ pip install pdfjinja
    $ pdfjinja -h


Usage:
------

Command Line::

    $ pdfjinja -j input.json form.pdf filled.pdf


Python::

    from pdfjinja import PdfJinja

    pdfjinja = PdfJinja('form.pdf')
    pdfout = pdfjinja(dict(firstName='Faye', lastName='Valentine'))
    pdfout.write(open('filled.pdf', 'wb'))


If you are using this with Flask as a webserver::

    from flask import current_app
    pdfjinja = PdfJinja('form.pdf', current_app.jinja_env)

See examples/sample.form and examples/sample.json.
