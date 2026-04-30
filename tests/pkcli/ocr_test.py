"""test ocr

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

    import shutil

    if not shutil.which("magick"):
        pytest.skip("ImageMagick not available")
    r = subprocess.run(["fc-match", "--format=%{file}"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        pytest.skip("no font available via fc-match")
    f = r.stdout.strip()
    with pkunit.save_chdir_work():
        t = "".join(random.choice(string.ascii_uppercase) for _ in range(16))
        subprocess.check_call(
            [
                "magick",
                "-size",
                "900x900",
                "xc:White",
                "-gravity",
                "Center",
                "-font",
                f,
                "-pointsize",
                "24",
                "-annotate",
                "0",
                # Need enough text to test
                t
                + " Lorem ipsum\ndolor sit amet, consectetur\nadipiscing elit, sed do\neiusmod tempor incididunt",
                "x.pdf",
            ],
        )

        out = subprocess.check_output(["gs", "-sDEVICE=txtwrite", "-o", "-", "x.pdf"])
        assert t.encode() not in out
        ocr.default_command("x.pdf")
        out = subprocess.check_output(["gs", "-sDEVICE=txtwrite", "-o", "-", "x.pdf"])
        assert t.encode() in out
