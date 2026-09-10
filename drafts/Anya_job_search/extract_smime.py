#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract MIME payload and attachments from S/MIME .p7m (PKCS#7 signed)."""

from pathlib import Path
import email
from email import policy
import sys

SRC = Path(r"c:\Users\Acer\Downloads\smime.p7m")
OUT = Path(r"c:\1c\Cursor_1c\WIM_DEV\drafts\Anya_job_search\ok_test_extract")
OUT.mkdir(parents=True, exist_ok=True)


def extract_via_asn1(data: bytes):
    from asn1crypto import cms

    content_info = cms.ContentInfo.load(data)
    print("cms type:", content_info["content_type"].native)
    content = content_info["content"]
    if content_info["content_type"].native == "signed_data":
        eci = content["encap_content_info"]
        print("encap type:", eci["content_type"].native)
        raw = eci["content"]
        if raw is None:
            return None
        payload = raw.native
        if isinstance(payload, str):
            payload = payload.encode("utf-8", errors="replace")
        return bytes(payload)
    return None


def extract_heuristic(data: bytes):
    markers = [
        b"Content-Type: multipart/mixed",
        b"Content-Type: multipart/related",
        b"Content-Type: text/plain",
        b"Content-Type: text/html",
        b"MIME-Version:",
    ]
    idx = -1
    for m in markers:
        i = data.find(m)
        if i >= 0 and (idx < 0 or i < idx):
            idx = i
    if idx < 0:
        return None
    # Trim trailing PKCS#7 ASN.1 noise: cut at last reasonable MIME boundary end
    chunk = data[idx:]
    # Often MIME ends before certificate blob; keep full chunk and let email parser handle
    return chunk


def save_email_parts(mime_bytes: bytes):
    # Normalize to something email parser accepts
    text = None
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            text = mime_bytes.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = mime_bytes.decode("latin-1", errors="replace")

    # Ensure headers start at beginning for Parser
    if not text.lstrip().lower().startswith("content-type") and "Content-Type:" in text:
        text = text[text.find("Content-Type:") :]

    msg = email.message_from_string(text, policy=policy.default)
    (OUT / "message_headers.txt").write_text(
        "\n".join(f"{k}: {v}" for k, v in msg.items()), encoding="utf-8"
    )

    saved = []
    part_i = 0
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get_content_disposition() or "")
            fname = part.get_filename()
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            part_i += 1
            if fname:
                safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in fname)
                path = OUT / safe
            elif ctype.startswith("text/"):
                ext = "html" if "html" in ctype else "txt"
                path = OUT / f"part_{part_i:02d}.{ext}"
            else:
                path = OUT / f"part_{part_i:02d}.bin"
            path.write_bytes(payload)
            saved.append((path.name, ctype, disp, len(payload)))
            print(f"saved {path.name} | {ctype} | {disp} | {len(payload)} bytes")
    else:
        payload = msg.get_payload(decode=True) or text.encode("utf-8")
        path = OUT / "body.bin"
        path.write_bytes(payload if isinstance(payload, (bytes, bytearray)) else str(payload).encode())
        saved.append((path.name, msg.get_content_type(), "", len(path.read_bytes())))
        print("saved single body")

    return saved


def main():
    data = SRC.read_bytes()
    print("source size:", len(data))

    payload = None
    try:
        payload = extract_via_asn1(data)
        print("asn1 payload:", None if payload is None else len(payload))
    except Exception as e:
        print("asn1 failed:", type(e).__name__, e)

    if not payload:
        payload = extract_heuristic(data)
        print("heuristic payload:", None if payload is None else len(payload))

    if not payload:
        print("ERROR: could not extract payload")
        sys.exit(1)

    (OUT / "payload_raw.bin").write_bytes(payload)
    # Also try as .eml-ish text preview
    preview = "".join(chr(b) if 32 <= b < 127 or b in (9, 10, 13) else "." for b in payload[:1500])
    (OUT / "payload_preview.txt").write_text(preview, encoding="utf-8")
    print("--- preview ---")
    print(preview[:800])

    try:
        save_email_parts(payload)
    except Exception as e:
        print("email parse failed:", type(e).__name__, e)
        # Fallback: split by Content-Disposition filename patterns
        for m in __import__("re").finditer(
            br'filename="?([^"\r\n;]+)"?', payload, flags=__import__("re").I
        ):
            print("found filename mention:", m.group(1))


if __name__ == "__main__":
    main()
