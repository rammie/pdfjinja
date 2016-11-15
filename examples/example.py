# -*- coding: utf-8 -*-
""" Example python script that fills out a pdf based on a jinja templates. """

import os

from pdfjinja import PdfJinja


dirname = os.path.dirname(__file__)
template_pdf_file = os.path.join(dirname, 'sample.pdf')
template_pdf = PdfJinja(template_pdf_file)

rendered_pdf = template_pdf({
    'firstName': 'Faye',
    'lastName': 'Valentine',
    'address': {
        'street': '223B Baker Street',
        'apt': '6F',
        'city': 'London',
        'zipcode': 94455
    },
    'sig': os.path.join(dirname, 'sig.png'),
    'spirit': 'Panda',
    'evil': True,
    'language': {
        'english': True
    },
    'attachments': [{
        'data': os.path.join(dirname, 'attachment.png'),
        'text': 'Tux\nFriendly Penguin\nMascot :)',
        'dimensions': [100, 200, 400, 400]
    }]
})

output_file = os.path.join(dirname, 'output.pdf')
rendered_pdf.write(open(output_file, 'wb'))
