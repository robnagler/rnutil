"""ocr utility

:copyright: Copyright (c) 2017-2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio, pkjson
import base64
import os
import pykern.pkcli
import requests
import textwrap


_DEFAULT_MODEL = "gpt-5-mini"
_DEFAULT_PROMPT = textwrap.dedent(
    """
    Transcribe this PDF into clean, readable plain text.

    Focus on the sender's written message. For handwritten letters, greeting
    cards, notes, or postcards, include the date, salutation, body,
    postscripts, addresses, phone numbers, and signoff. Omit decorative
    artwork, printed greeting-card slogans, copyright notices, product codes,
    blank pages, and bleed-through from the reverse side unless they are part
    of the sender's message.

    Preserve the author's wording, spelling, punctuation, ampersands, dashes,
    names, numbers, and dates as closely as readability allows. Do not
    summarize, modernize, explain, or translate. If text is unclear, use
    [illegible] rather than guessing.

    Formatting matters:
    - Use a blank line between logical paragraphs.
    - Reflow continuous prose into readable plain-text paragraphs with actual
      newline characters in the returned text.
    - Do not put an entire paragraph on one physical line and rely on the
      viewer to wrap it.
    - Hard rule: every output line must be 80 characters or fewer, except for
      a single unbreakable token such as a URL. Break long prose lines at a
      natural space before column 80; do not split words.
    - Preserve original line breaks for addresses, phone-number blocks,
      postscripts, signoffs, lists, calculations, and intentionally short
      handwritten lines.
    - Before returning, check the transcription line by line and fix any line
      longer than 80 characters.

    Return only the transcription.
    """,
).strip()


def openai(file_pdf):
    """Send file_pdf to OpenAI vision and write same-basename .txt.

        Args:
    n        file_pdf (str): PDF path
    """

    def _pdf_path(file_pdf):
        p = pkio.py_path(file_pdf)
        if not p.check(file=1):
            pykern.pkcli.command_error("{}: not found", p)
        if p.ext.lower() != ".pdf":
            pykern.pkcli.command_error("{}: not a PDF", p)
        return p

    p = _pdf_path(file_pdf)
    o = p.new(ext="txt")
    if o.exists():
        pykern.pkcli.command_error("refusing to overwrite existing file={}", o)
    return pkio.write_text(
        o,
        _extract_output_text(
            _call_openai(
                p,
                _DEFAULT_PROMPT,
                os.environ.get("OPENAI_MODEL") or _DEFAULT_MODEL,
            )
        ),
    )


def magick(file_pdf):
    """Run tesseract on file_pdf

    See http://kiirani.com/2013/03/22/tesseract-pdf.html

    Args:
        file_pdf (str): file to convert
    """
    import os
    import os.path
    import random
    import subprocess

    assert os.path.isfile(file_pdf), "{}: not found".format(file_pdf)
    p = "ocr-{}".format(random.randint(100000, 999999))
    t = "{}.tif".format(p)
    n = "{}.pdf".format(p)
    z = "zz-{}".format(file_pdf)
    for f in t, n, z:
        assert not os.path.exists(f), "{}: must not exist"
    subprocess.check_call(["magick", "-density", "300", file_pdf, "-depth", "8", t])
    subprocess.check_call(["tesseract", t, p, "pdf"])
    os.remove(t)
    os.rename(file_pdf, z)
    os.rename(n, file_pdf)
    os.remove(z)


def _call_openai(pdf_path, prompt, model):
    def _prompt():
        return {
            "model": model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": pdf_path.basename,
                            "file_data": "data:application/pdf;base64,{}".format(
                                base64.b64encode(pkio.read_binary(pdf_path)).decode(
                                    "ascii"
                                ),
                            ),
                        },
                        {
                            "type": "input_text",
                            "text": prompt,
                        },
                    ],
                },
            ],
        }

    def _response_text(response):
        try:
            return pkjson.dump_pretty(response.json()).rstrip()
        except ValueError:
            return response.text

    if not (k := os.environ.get("OPENAI_API_KEY")):
        pykern.pkcli.command_error("OPENAI_API_KEY is not set")
    r = requests.post(
        "{}/responses".format(
            os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip(
                "/",
            ),
        ),
        headers={
            "Authorization": f"Bearer {k}",
            "Content-Type": pkjson.CONTENT_TYPE,
        },
        json=_prompt(),
        timeout=300,
    )
    if not r.ok:
        pykern.pkcli.command_error(
            "OpenAI API error {}: {}",
            r.status_code,
            _response_text(r),
        )
    try:
        return r.json()
    except ValueError:
        pykern.pkcli.command_error("OpenAI API returned non-JSON response: {}", r.text)


def _extract_output_text(response):
    def _newline(text):
        return text if text.endswith("\n") else text + "\n"

    if isinstance(response.get("output_text"), str):
        return _newline(response["output_text"])
    rv = []
    for o in response.get("output", []):
        if o.get("type") == "message":
            for c in o.get("content", []):
                if c.get("type") in ("output_text", "text"):
                    rv.append(c.get("text", ""))
        elif o.get("type") == "output_text":
            rv.append(o.get("text", ""))
    if rv:
        return _newline("".join(rv))
    pykern.pkcli.command_error(
        "OpenAI response did not contain output text: {}",
        pkjson.dump_pretty(response).rstrip(),
    )
