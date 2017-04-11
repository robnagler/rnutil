# -*- coding: utf-8 -*-
u"""ocr utility

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


def default_command(file_pdf):
    """Run tesseract on file_pdf

    See http://kiirani.com/2013/03/22/tesseract-pdf.html

    Args:
        file_pdf (str): file to convert
    """
    import os
    import os.path
    import random
    import subprocess

    assert os.path.isfile(file_pdf), \
        '{}: not found'.format(file_pdf)
    p = 'ocr-{}'.format(random.randint(100000,999999))
    t = '{}.tif'.format(p)
    n = '{}.pdf'.format(p)
    z = 'zz-{}'.format(file_pdf)
    for f in t, n, z:
        assert not os.path.exists(f), \
            '{}: must not exist'
    subprocess.check_call(['convert', '-density', '300', file_pdf, '-depth', '8', t])
    subprocess.check_call(['tesseract', t, p, 'pdf'])
    os.remove(t)
    os.rename(file_pdf, z)
    os.rename(n, file_pdf)
