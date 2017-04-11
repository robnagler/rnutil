# -*- coding: utf-8 -*-
u"""test ocr

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_default_command():
    from pykern import pkunit
    from rnutil.pkcli import ocr
    import random
    import string
    import subprocess
    
    with pkunit.save_chdir_work():
        t = ''.join(random.choice(string.ascii_uppercase) for _ in range(16))
        subprocess.check_call(
            [
                'convert',
                '-size',
                '900x900',
                'xc:White',
                '-gravity',
                'Center',
                '-pointsize',
                '50',
                '-annotate',
                '0',
                # Need enough text to test
                t + ' Lorem ipsum\ndolor sit amet, consectetur\nadipiscing elit, sed do\neiusmod tempor incididunt',
                'x.pdf',
            ],
        )
        
        out = subprocess.check_output(['gs', '-sDEVICE=txtwrite', '-o', '-', 'x.pdf'])
        assert not t in out
        ocr.default_command('x.pdf')
        out = subprocess.check_output(['gs', '-sDEVICE=txtwrite', '-o', '-', 'x.pdf'])
        assert t in out

