"""test ocr

:copyright: Copyright (c) 2017-2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


def test_openai(monkeypatch):
    from pykern import pkio, pkunit
    import pykern.pkcli
    from rnutil.pkcli import ocr

    calls = []

    def _call_openai(pdf_path, prompt, model):
        calls.append((pdf_path.basename, prompt, model))
        return {"output_text": "hello"}

    monkeypatch.setattr(ocr, "_call_openai", _call_openai)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    with pkunit.save_chdir_work():
        pkio.py_path("x.pdf").write_binary(b"%PDF-1.4\n")
        assert "x.txt" in str(ocr.openai("x.pdf"))
        assert pkio.read_text("x.txt") == "hello\n"
        assert calls == [
            (
                "x.pdf",
                ocr._DEFAULT_PROMPT,
                "test-model",
            ),
        ]
        with pytest.raises(pykern.pkcli.CommandError):
            ocr.openai("x.pdf")
        assert len(calls) == 1


def test_magick():
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
        ocr.magick("x.pdf")
        out = subprocess.check_output(["gs", "-sDEVICE=txtwrite", "-o", "-", "x.pdf"])
        assert t.encode() in out
