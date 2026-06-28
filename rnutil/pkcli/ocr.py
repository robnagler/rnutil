"""ocr utility

:copyright: Copyright (c) 2017-2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio, pkjson
import base64
import os
import pykern.pkcli
import requests


_DEFAULT_MODEL = "gpt-5-mini"
_DEFAULT_PROMPT = """Transcribe this PDF into plain text. Include
    visible text from images, tables, forms, and handwriting when
    present. Preserve the logical reading order and useful line
    breaks. Format paragraphs at about 80 characters.  Return only the
    transcription."""


def openai(file_pdf, model=None, prompt=None, prompt_file=None, max_output_tokens=None):
    """Send file_pdf to OpenAI vision and write same-basename .txt.

    Args:
        file_pdf (str): PDF path
        model (str): OpenAI model [$OPENAI_MODEL or gpt-5-mini]
        prompt (str): prompt to send with the PDF [transcription prompt]
        prompt_file (str): read prompt from this UTF-8 file
        max_output_tokens (int): optional Responses API max_output_tokens
    """
    p = _pdf_path(file_pdf)
    out = p.new(ext="txt")
    if out.exists():
        pykern.pkcli.command_error("{}: refusing to overwrite existing file", out)
    r = _call_openai(
        p,
        _prompt(prompt, prompt_file),
        model or os.environ.get("OPENAI_MODEL") or _DEFAULT_MODEL,
        max_output_tokens,
    )
    _write_no_overwrite(out, _extract_output_text(r))
    return "Wrote {}".format(out)


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


def _call_openai(pdf_path, prompt, model, max_output_tokens):
    k = os.environ.get("OPENAI_API_KEY")
    if not k:
        pykern.pkcli.command_error("OPENAI_API_KEY is not set")
    p = {
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
    if max_output_tokens is not None:
        p["max_output_tokens"] = int(max_output_tokens)
    try:
        r = requests.post(
            "{}/responses".format(
                os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip(
                    "/",
                ),
            ),
            headers={
                f"Authorization": "Bearer {k}",
                "Content-Type": pkjson.CONTENT_TYPE,
            },
            json=p,
            timeout=300,
        )
    except requests.exceptions.RequestException as e:
        pykern.pkcli.command_error("OpenAI API request failed: {}", e)
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
    if isinstance(response.get("output_text"), str):
        return _text_with_final_newline(response["output_text"])
    res = []
    for o in response.get("output", []):
        if o.get("type") == "message":
            for c in o.get("content", []):
                if c.get("type") in ("output_text", "text"):
                    res.append(c.get("text", ""))
        elif o.get("type") == "output_text":
            res.append(o.get("text", ""))
    if res:
        return _text_with_final_newline("".join(res))
    pykern.pkcli.command_error(
        "OpenAI response did not contain output text: {}",
        pkjson.dump_pretty(response).rstrip(),
    )


def _pdf_path(file_pdf):
    p = pkio.py_path(file_pdf)
    if not p.check(file=1):
        pykern.pkcli.command_error("{}: not found", p)
    if p.ext.lower() != ".pdf":
        pykern.pkcli.command_error("{}: not a PDF", p)
    return p


def _prompt(prompt, prompt_file):
    if prompt and prompt_file:
        pykern.pkcli.command_error("use prompt or prompt_file, not both")
    if prompt_file:
        return pkio.read_text(prompt_file)
    return prompt or _DEFAULT_PROMPT


def _response_text(response):
    try:
        return pkjson.dump_pretty(response.json()).rstrip()
    except ValueError:
        return response.text


def _text_with_final_newline(text):
    return text if text.endswith("\n") else text + "\n"


def _write_no_overwrite(path, text):
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pykern.pkcli.command_error("{}: refusing to overwrite existing file", path)
    with os.fdopen(fd, "w", encoding=pkio.TEXT_ENCODING) as f:
        f.write(text)
