#!/usr/bin/env python3
"""Обработчик заявок с сайта: Telegram + e-mail. Секреты только в .env."""
from __future__ import annotations

import json
import os
import smtplib
import time
import urllib.error
import urllib.parse
import urllib.request
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ENV_PATH = Path(os.environ.get("DUBOVIK_ENV", "/var/www/dubovik/.env"))
LEADS_PATH = Path(os.environ.get("DUBOVIK_LEADS", "/var/www/dubovik/data/leads.jsonl"))


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        # Always apply file values (empty keys in process must not block .env).
        os.environ[key.strip()] = value.strip()


load_env(ENV_PATH)

HOST = os.environ.get("CONTACT_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("CONTACT_API_PORT", "8099"))
MAX_BODY = 8192


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def send_telegram(text: str) -> tuple[bool, str]:
    token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False, "telegram_not_configured"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    ).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if body.get("ok"):
            return True, "ok"
        return False, str(body.get("description", "telegram_error"))
    except urllib.error.URLError as exc:
        return False, str(exc)


def send_email(subject: str, body: str) -> tuple[bool, str]:
    host = _env("SMTP_HOST")
    user = _env("SMTP_USER")
    password = _env("SMTP_PASSWORD")
    to_addr = _env("CONTACT_TO_EMAIL") or _env("SMTP_USER")
    port = int(_env("SMTP_PORT") or "587")
    use_tls = _env("SMTP_TLS").lower() not in ("0", "false", "no")
    if not host or not user or not password or not to_addr:
        return False, "email_not_configured"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(user, [to_addr], msg.as_string())
        return True, "ok"
    except OSError as exc:
        return False, str(exc)


def validate_payload(data: dict) -> tuple[str, str, str, str] | str:
    honeypot = (data.get("website") or "").strip()
    if honeypot:
        return "spam"
    name = (data.get("name") or "").strip()[:120]
    phone = (data.get("phone") or "").strip()[:40]
    message = (data.get("message") or "").strip()[:4000]
    lang = (data.get("lang") or "ru").strip()[:5]
    if not name or not phone:
        return "missing_fields"
    return name, phone, message, lang


def save_lead(name: str, phone: str, message: str, lang: str) -> tuple[bool, str]:
    """Локальная копия заявки — не теряем, даже если Telegram/почта сбойнули."""
    try:
        LEADS_PATH.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": int(time.time()),
            "name": name,
            "phone": phone,
            "message": message,
            "lang": lang,
        }
        with LEADS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return True, "ok"
    except OSError as exc:
        return False, str(exc)


class ContactHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            tg = bool(_env("TELEGRAM_BOT_TOKEN") and _env("TELEGRAM_CHAT_ID"))
            em = bool(_env("SMTP_HOST") and _env("SMTP_USER") and _env("SMTP_PASSWORD"))
            try:
                LEADS_PATH.parent.mkdir(parents=True, exist_ok=True)
                file_ok = True
            except OSError:
                file_ok = False
            self._json(200, {"ok": True, "telegram": tg, "email": em, "file": file_ok})
            return
        self._json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/contact":
            self._json(404, {"ok": False, "error": "not_found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            self._json(400, {"ok": False, "error": "bad_body"})
            return
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(400, {"ok": False, "error": "invalid_json"})
            return
        if not isinstance(data, dict):
            self._json(400, {"ok": False, "error": "invalid_json"})
            return

        validated = validate_payload(data)
        if isinstance(validated, str):
            self._json(400, {"ok": False, "error": validated})
            return
        name, phone, message, lang = validated

        text = (
            f"📩 Заявка с сайта ({lang})\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Сообщение:\n{message or '—'}"
        )
        file_ok, file_err = save_lead(name, phone, message, lang)
        tg_ok, tg_err = send_telegram(text)
        em_ok, em_err = send_email(
            f"Заявка с сайта — {name}",
            text,
        )

        # Успех для посетителя — только если ушло в Telegram и/или на почту.
        # Файл всегда пишем как резервная копия на сервере.
        if tg_ok or em_ok:
            channels = []
            if tg_ok:
                channels.append("telegram")
            if em_ok:
                channels.append("email")
            if file_ok:
                channels.append("file")
            self._json(200, {"ok": True, "channels": channels})
            return

        self._json(
            503,
            {
                "ok": False,
                "error": "delivery_failed",
                "telegram": tg_err,
                "email": em_err,
                "file": file_err if not file_ok else "ok",
            },
        )


def main() -> None:
    server = HTTPServer((HOST, PORT), ContactHandler)
    print(f"contact_api listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
