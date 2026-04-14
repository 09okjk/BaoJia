from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


class PdfRenderError(RuntimeError):
    pass


PDF_RENDER_TIMEOUT_SECONDS = 30


def render_pdf(
    *,
    html: str,
    output_pdf_path: Path,
    base_url: str | None = None,
    prefer: str = "weasyprint",
) -> Path:
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if prefer == "weasyprint":
        try:
            return _render_with_weasyprint(
                html=html,
                output_pdf_path=output_pdf_path,
                base_url=base_url,
            )
        except Exception as e:
            weasyprint_error = str(e)
        else:
            weasyprint_error = ""
    else:
        weasyprint_error = ""

    try:
        return _render_with_chromium(html=html, output_pdf_path=output_pdf_path)
    except Exception as e:
        chromium_error = str(e)

    try:
        return _render_with_wkhtmltopdf(html=html, output_pdf_path=output_pdf_path)
    except Exception as e:
        wkhtml_error = str(e)

    raise PdfRenderError(
        f"PDF render failed: weasyprint={weasyprint_error}; chromium={chromium_error}; wkhtmltopdf={wkhtml_error}"
    )


def _render_with_weasyprint(
    *, html: str, output_pdf_path: Path, base_url: str | None
) -> Path:
    try:
        from weasyprint import HTML
    except Exception as exc:
        raise PdfRenderError(f"Failed to import weasyprint: {exc}") from exc

    HTML(string=html, base_url=base_url).write_pdf(target=str(output_pdf_path))
    return output_pdf_path


def _render_with_wkhtmltopdf(*, html: str, output_pdf_path: Path) -> Path:
    exe = shutil.which("wkhtmltopdf")
    if not exe:
        raise PdfRenderError("wkhtmltopdf executable not found")

    args: list[str] = [
        exe,
        "--quiet",
        "--enable-local-file-access",
        "-",
        str(output_pdf_path),
    ]
    proc = subprocess.run(
        args,
        input=html.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=PDF_RENDER_TIMEOUT_SECONDS,
    )
    if proc.returncode != 0:
        err_text = _safe_decode(proc.stderr) or _safe_decode(proc.stdout)
        raise PdfRenderError(f"wkhtmltopdf failed: {err_text}")

    return output_pdf_path


def _render_with_chromium(*, html: str, output_pdf_path: Path) -> Path:
    exe = _find_chromium_executable()
    if not exe:
        raise PdfRenderError("No Chrome/Edge executable found")

    output_pdf_path = output_pdf_path.resolve()
    temp_html = output_pdf_path.with_suffix(".tmp.html")
    temp_html.write_text(html, encoding="utf-8")
    try:
        args = [
            exe,
            "--headless=new",
            f"--print-to-pdf={output_pdf_path}",
            "--disable-gpu",
            "--allow-file-access-from-files",
            temp_html.resolve().as_uri(),
        ]
        proc = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=PDF_RENDER_TIMEOUT_SECONDS,
        )
        if proc.returncode != 0 or not output_pdf_path.exists():
            err_text = _safe_decode(proc.stderr) or _safe_decode(proc.stdout)
            raise PdfRenderError(f"Chromium print-to-pdf failed: {err_text}")
        return output_pdf_path
    except subprocess.TimeoutExpired as exc:
        raise PdfRenderError(
            f"Chromium print-to-pdf timed out after {PDF_RENDER_TIMEOUT_SECONDS}s"
        ) from exc
    finally:
        temp_html.unlink(missing_ok=True)


def _find_chromium_executable() -> str | None:
    candidates = [
        shutil.which("chrome"),
        shutil.which("msedge"),
        shutil.which("chromium"),
        shutil.which("MicrosoftEdge"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def _safe_decode(data: Any) -> str:
    if not data:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace").strip()
    return str(data).strip()
