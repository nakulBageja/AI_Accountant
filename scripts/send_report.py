#!/usr/bin/env python3
"""Email the latest AI Accountant report via Gmail SMTP.

Usage:
    python3 scripts/send_report.py reports/snapshot_2026_07_18/report.md

The report (Markdown) is converted to mobile-friendly HTML. The email is sent as a
multipart message: an HTML body that renders cleanly in phone mail apps, a plaintext
fallback, and an .html attachment that opens in any phone browser.

Configuration is read from scripts/.env (see scripts/.env.example). Required keys:
    GMAIL_ADDRESS      the sending Gmail account
    GMAIL_APP_PASSWORD a Gmail App Password (NOT your normal password)
    REPORT_RECIPIENT   where to send the report (can be the same address)
"""

import html
import re
import smtplib
import sys
from datetime import date
from email.message import EmailMessage
from pathlib import Path


def load_env(env_path: Path) -> dict:
    """Minimal .env loader so we don't need external dependencies."""
    values = {}
    if not env_path.exists():
        sys.exit(f"Missing config: {env_path}. Copy .env.example to .env and fill it in.")
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def _inline(text: str) -> str:
    """Escape HTML then apply inline Markdown (bold, italic, code)."""
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def markdown_to_html(md: str) -> str:
    """Convert a subset of Markdown (headings, tables, lists, paragraphs) to HTML.

    Self-contained so the script has no external dependencies. Covers what the
    accountant reports use: #/##/### headings, - bullet lists, | pipe tables |,
    and paragraphs, plus inline bold/italic/code.
    """
    lines = md.splitlines()
    out = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Blank line
        if not stripped:
            i += 1
            continue

        # Headings
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            i += 1
            continue

        # Tables: a header row followed by a |---|---| separator row
        if "|" in stripped and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]):
            def cells(row):
                row = row.strip().strip("|")
                return [c.strip() for c in row.split("|")]

            headers = cells(stripped)
            out.append('<table role="presentation">')
            out.append("<thead><tr>" + "".join(f"<th>{_inline(h)}</th>" for h in headers) + "</tr></thead>")
            out.append("<tbody>")
            i += 2  # skip header + separator
            while i < n and "|" in lines[i] and lines[i].strip():
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells(lines[i])) + "</tr>")
                i += 1
            out.append("</tbody></table>")
            continue

        # Unordered lists
        if re.match(r"^[-*]\s+", stripped):
            out.append("<ul>")
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                item = re.sub(r"^[-*]\s+", "", lines[i].strip())
                out.append(f"<li>{_inline(item)}</li>")
                i += 1
            out.append("</ul>")
            continue

        # Ordered lists
        if re.match(r"^\d+\.\s+", stripped):
            out.append("<ol>")
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                item = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                out.append(f"<li>{_inline(item)}</li>")
                i += 1
            out.append("</ol>")
            continue

        # Paragraph (gather consecutive non-blank, non-structural lines)
        para = []
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|[-*]\s|\d+\.\s)", lines[i].strip()) and "|" not in lines[i]:
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
        else:
            i += 1

    return "\n".join(out)


def wrap_html(body_html: str, title: str) -> str:
    """Wrap converted HTML in a responsive, mobile-friendly document."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.55; color: #1a1a1a; background: #f5f5f7;
    margin: 0; padding: 16px;
  }}
  .card {{
    max-width: 640px; margin: 0 auto; background: #ffffff;
    border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  }}
  h1 {{ font-size: 1.5rem; margin: 0 0 12px; }}
  h2 {{ font-size: 1.2rem; margin: 24px 0 8px; border-bottom: 1px solid #eee; padding-bottom: 4px; }}
  h3 {{ font-size: 1.05rem; margin: 18px 0 6px; }}
  p, li {{ font-size: 1rem; }}
  ul, ol {{ padding-left: 1.3em; }}
  code {{ background: #f0f0f2; padding: 1px 5px; border-radius: 4px; font-size: 0.9em; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.95rem; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #eaeaea; }}
  th {{ background: #fafafa; }}
  /* On narrow phone screens let wide tables scroll horizontally. */
  .card {{ overflow-x: auto; }}
  @media (max-width: 480px) {{
    body {{ padding: 8px; }}
    .card {{ padding: 14px; border-radius: 8px; }}
    th, td {{ padding: 6px 7px; }}
  }}
</style>
</head>
<body>
  <div class="card">
{body_html}
  </div>
</body>
</html>"""


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 scripts/send_report.py <path/to/report.md>")

    report_path = Path(sys.argv[1])
    if not report_path.exists():
        sys.exit(f"Report not found: {report_path}")

    env = load_env(Path(__file__).parent / ".env")
    sender = env.get("GMAIL_ADDRESS")
    app_password = env.get("GMAIL_APP_PASSWORD")
    recipient = env.get("REPORT_RECIPIENT", sender)

    if not sender or not app_password:
        sys.exit("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in scripts/.env")

    md_body = report_path.read_text()
    subject = f"Your money report — {date.today().isoformat()}"
    html_doc = wrap_html(markdown_to_html(md_body), subject)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    # Plaintext fallback for clients that don't render HTML; HTML body for phones.
    msg.set_content(md_body)
    msg.add_alternative(html_doc, subtype="html")
    # Attach a phone-readable .html file (opens in any mobile browser).
    msg.add_attachment(
        html_doc.encode("utf-8"),
        maintype="text",
        subtype="html",
        filename=report_path.stem + ".html",
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, app_password)
        server.send_message(msg)

    print(f"Sent '{report_path.name}' to {recipient} (HTML body + .html attachment)")


if __name__ == "__main__":
    main()
