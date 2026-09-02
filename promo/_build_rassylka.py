# -*- coding: utf-8 -*-
"""Build mailing contact table from rabota.by OT/PB vacancy searches."""
from __future__ import annotations

import csv
import html as html_lib
import json
import re
import time
import urllib.request
from pathlib import Path

PROMO = Path(r"c:\Users\Labuh\.vscode\sites\dubovik-safety\promo")
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html_lib.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_serp(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    # Prefer splitting by serp vacancy cards
    chunks = raw.split('data-qa="vacancy-serp__vacancy"')[1:]
    rows = []
    for chunk in chunks:
        # Limit chunk size to avoid eating next card markup loosely
        piece = chunk[:12000]
        m_url = re.search(
            r'data-qa="serp-item__title"[^>]*href="(https://rabota\.by/vacancy/\d+[^"]*)"',
            piece,
        )
        if not m_url:
            m_url = re.search(r'href="(https://rabota\.by/vacancy/\d+[^"]*)"', piece)
        if not m_url:
            continue
        url = m_url.group(1).split("?")[0]
        vac_id = url.rstrip("/").split("/")[-1]
        m_title = re.search(
            r'data-qa="serp-item__title"[^>]*>(.*?)</a>',
            piece,
            re.DOTALL | re.IGNORECASE,
        )
        title = strip_tags(m_title.group(1)) if m_title else ""
        m_emp = re.search(
            r'data-qa="vacancy-serp__vacancy-employer"[^>]*(?:href="([^"]*)")?[^>]*>(.*?)</a>',
            piece,
            re.DOTALL | re.IGNORECASE,
        )
        company = strip_tags(m_emp.group(2)) if m_emp else ""
        emp_href = m_emp.group(1) if m_emp and m_emp.group(1) else ""
        if emp_href and emp_href.startswith("/"):
            emp_href = "https://rabota.by" + emp_href.split("?")[0]
        m_addr = re.search(
            r'data-qa="vacancy-serp__vacancy-address"[^>]*>(.*?)</(?:span|div|p|a)>',
            piece,
            re.DOTALL | re.IGNORECASE,
        )
        city = strip_tags(m_addr.group(1)) if m_addr else ""
        rows.append(
            {
                "vac_id": vac_id,
                "title": title,
                "company": company,
                "city": city,
                "vacancy_url": url,
                "employer_url": emp_href or "не указан",
            }
        )
    return rows


def note_for_title(title: str) -> str:
    t = (title or "").lower()
    ot = any(x in t for x in ("охран", "от ", "охраны труда", "технике безопасности", "тб"))
    pb = any(x in t for x in ("промышленн", "пб", "пожарн"))
    if ot and pb:
        return "Нужен специалист ОТ и промышленной безопасности"
    if pb:
        return "Нужен специалист по промышленной безопасности"
    if ot:
        return "Нужен инженер/специалист по охране труда"
    return "Вакансия связана с ОТ/безопасностью"


def is_relevant(title: str) -> bool:
    t = (title or "").lower()
    keys = (
        "охран",
        "промышленн",
        "технике безопасности",
        "пожар",
        "эколог",
        "охраны труда",
    )
    # Exclude pure sales of safety products unless title is OT/PB engineer
    if "менеджер по продаж" in t and "инженер" not in t and "специалист" not in t:
        return False
    return any(k in t for k in keys)


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.read().decode("utf-8", errors="replace")


_SITE_EMAIL_BLOCK = (
    "hh.by",
    "hh.ru",
    "rabota.by",
    "tut.by",
    "sentry",
    "example.com",
    "yandex.",
    "google.",
    "cloudflare",
)


def _is_site_noise_email(em: str) -> bool:
    low = em.lower()
    return any(x in low for x in _SITE_EMAIL_BLOCK)


def extract_contacts(page: str) -> dict:
    contact = "не указан"
    phone = "не указан"
    email = "не указан"
    notes_extra = []
    employer_url = ""

    # Lux JSON: contacts usually hidden until login / «показать контакты»
    contacts_hidden = False
    tpl = re.search(r'id="HH-Lux-InitialState">(.*?)</template>', page, re.S)
    if tpl:
        try:
            lux = json.loads(html_lib.unescape(tpl.group(1)))
            vv = lux.get("vacancyView") or {}
            ci = vv.get("contactInfo") or {}
            if isinstance(ci, dict) and ci.get("contactsHidden"):
                contacts_hidden = True
            # Rare public fields if present
            for key in ("fio", "name", "fullName"):
                if isinstance(ci, dict) and ci.get(key):
                    contact = str(ci.get(key)).strip() or contact
            if isinstance(ci, dict):
                emails = ci.get("email") or ci.get("emails") or []
                if isinstance(emails, str):
                    emails = [emails]
                if isinstance(emails, list):
                    clean = [
                        str(e).strip()
                        for e in emails
                        if e and "@" in str(e) and not _is_site_noise_email(str(e))
                    ]
                    if clean:
                        email = "; ".join(clean[:3])
                phones = ci.get("phones") or ci.get("phone") or []
                if isinstance(phones, str):
                    phones = [phones]
                if isinstance(phones, dict):
                    phones = [phones.get("formatted") or phones.get("number") or ""]
                phone_vals = []
                for p in phones:
                    if isinstance(p, dict):
                        v = p.get("formatted") or p.get("number") or ""
                    else:
                        v = str(p)
                    v = v.strip()
                    if v and v not in phone_vals:
                        phone_vals.append(v)
                if phone_vals:
                    phone = "; ".join(phone_vals[:3])
            company = vv.get("company") or {}
            if isinstance(company, dict):
                eid = company.get("id") or company.get("mainEmployerId")
                if eid:
                    employer_url = f"https://rabota.by/employer/{eid}"
        except Exception:
            pass

    # Contact person in HTML (only if publicly rendered)
    m = re.search(
        r'data-qa="vacancy-contacts__fio"[^>]*>(.*?)</(?:p|div|span|a)>',
        page,
        re.DOTALL | re.IGNORECASE,
    )
    if m and contact == "не указан":
        contact = strip_tags(m.group(1)) or contact

    # Phones from visible markup / tel:
    phone_vals = []
    for p in re.findall(
        r'data-qa="vacancy-contact__phone[^"]*"[^>]*>(.*?)</(?:a|span|div|p)>',
        page,
        re.DOTALL | re.IGNORECASE,
    ):
        v = strip_tags(p)
        if v and v not in phone_vals:
            phone_vals.append(v)
    for tel in re.findall(r'href="tel:([^"]+)"', page):
        v = html_lib.unescape(tel).strip()
        if v and v not in phone_vals:
            phone_vals.append(v)
    if phone_vals and phone == "не указан":
        phone = "; ".join(phone_vals[:3])

    # Emails from vacancy-contacts only (never site-wide mailto)
    email_vals = []
    for e in re.findall(
        r'data-qa="vacancy-contacts__email"[^>]*>(.*?)</(?:a|span|div|p)>',
        page,
        re.DOTALL | re.IGNORECASE,
    ):
        v = strip_tags(e)
        if "@" in v and not _is_site_noise_email(v) and v not in email_vals:
            email_vals.append(v)
    for mailto in re.findall(
        r'data-qa="vacancy-contacts__email"[^>]*href="mailto:([^"]+)"',
        page,
        re.I,
    ):
        v = html_lib.unescape(mailto).split("?")[0].strip()
        if "@" in v and not _is_site_noise_email(v) and v not in email_vals:
            email_vals.append(v)
    if email_vals and email == "не указан":
        email = "; ".join(email_vals[:3])

    if contacts_hidden or re.search(
        r"data-qa=\"show-employer-contacts|показать контакт",
        page,
        re.I,
    ):
        if phone == "не указан" and email == "не указан":
            notes_extra.append(
                "контакты скрыты («показать контакты» на rabota.by) — откройте вакансию вручную"
            )

    # Company name fallback from vacancy page
    company = ""
    m = re.search(
        r'data-qa="vacancy-company-name"[^>]*>(.*?)</(?:a|span|div)>',
        page,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        company = strip_tags(m.group(1))
    if not employer_url:
        m = re.search(r'href="(/employer/\d+)', page)
        if m:
            employer_url = "https://rabota.by" + m.group(1)
    title = ""
    m = re.search(
        r'data-qa="vacancy-title"[^>]*>(.*?)</(?:h1|div|span)>',
        page,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.DOTALL | re.IGNORECASE)
    if m:
        title = strip_tags(m.group(1))
    city = ""
    m = re.search(
        r'data-qa="vacancy-view-location"[^>]*>(.*?)</(?:span|div|p|a)>',
        page,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        city = strip_tags(m.group(1))

    return {
        "contact": contact,
        "phone": phone,
        "email": email,
        "company_page": company,
        "title_page": title,
        "city_page": city,
        "employer_url": employer_url or "не указан",
        "notes_extra": notes_extra,
    }


def main() -> None:
    serp_files = [
        PROMO / "_tmp_ot_search.html",
        PROMO / "_tmp_ot_search_p1.html",
        PROMO / "_tmp_pb_search.html",
        PROMO / "_tmp_spec_ot_search.html",
        PROMO / "_tmp_resume_search.html",
    ]
    by_id: dict[str, dict] = {}
    for f in serp_files:
        if not f.exists():
            continue
        for row in parse_serp(f):
            if not is_relevant(row["title"]):
                continue
            by_id.setdefault(row["vac_id"], row)

    # Prefer OT/PB titled roles; keep order stable
    items = list(by_id.values())
    items.sort(key=lambda r: (r["company"].lower(), r["title"].lower()))

    # Cap polite scrape: first page results (~25-40). Delay between pages.
    # Do not aggressively spam.
    max_detail = min(len(items), 45)
    results = []
    for i, row in enumerate(items[:max_detail]):
        print(f"fetch {i+1}/{max_detail} {row['vac_id']}...", flush=True)
        detail = {
            "contact": "не указан",
            "phone": "не указан",
            "email": "не указан",
            "notes_extra": ["страница вакансии не загружена"],
        }
        try:
            page = fetch(row["vacancy_url"])
            detail = extract_contacts(page)
            # cache page briefly for debug of first few
            if i < 3:
                (PROMO / f"_tmp_vac_{row['vac_id']}.html").write_text(page, encoding="utf-8")
        except Exception as e:
            detail["notes_extra"] = [f"ошибка загрузки страницы: {type(e).__name__}"]
        company = row["company"] or detail.get("company_page") or "не указан"
        title = row["title"] or detail.get("title_page") or "не указан"
        city = row["city"] or detail.get("city_page") or "не указан"
        note = note_for_title(title)
        extras = detail.get("notes_extra") or []
        if extras:
            note = note + "; " + "; ".join(extras)
        emp = detail.get("employer_url") or row.get("employer_url") or "не указан"
        if emp and emp != "не указан" and "employer" in emp:
            note = note + f"; страница компании: {emp}"
        results.append(
            {
                "Организация": company,
                "Вакансия": title,
                "Город": city,
                "Контактное лицо": detail.get("contact") or "не указан",
                "Телефон": detail.get("phone") or "не указан",
                "Email": detail.get("email") or "не указан",
                "Ссылка на вакансию": row["vacancy_url"],
                "Примечание": note,
                "employer_url": emp,
            }
        )
        time.sleep(1.2)  # polite delay

    # Deduplicate by organization+vacancy title keep first
    seen = set()
    unique = []
    for r in results:
        key = (r["Организация"].lower(), r["Вакансия"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    csv_path = PROMO / "rassylka-kontakty-rabota-by.csv"
    html_path = PROMO / "rassylka-kontakty-rabota-by.html"
    fields = [
        "№",
        "Организация",
        "Вакансия",
        "Город",
        "Контактное лицо",
        "Телефон",
        "Email",
        "Ссылка на вакансию",
        "Примечание",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", delimiter=";")
        w.writeheader()
        for i, r in enumerate(unique, 1):
            row = {k: r.get(k, "не указан") for k in fields if k != "№"}
            row["№"] = i
            w.writerow(row)

    # HTML table
    rows_html = []
    for i, r in enumerate(unique, 1):
        link = html_lib.escape(r["Ссылка на вакансию"])
        rows_html.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{html_lib.escape(r['Организация'])}</td>"
            f"<td>{html_lib.escape(r['Вакансия'])}</td>"
            f"<td>{html_lib.escape(r['Город'])}</td>"
            f"<td>{html_lib.escape(r['Контактное лицо'])}</td>"
            f"<td>{html_lib.escape(r['Телефон'])}</td>"
            f"<td>{html_lib.escape(r['Email'])}</td>"
            f'<td><a href="{link}" target="_blank" rel="noopener">открыть</a></td>'
            f"<td>{html_lib.escape(r['Примечание'])}</td>"
            "</tr>"
        )

    html_out = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Контакты для рассылки — rabota.by (ОТ / ПБ)</title>
  <style>
    body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 24px; color: #1a1a1a; background: #f7f7f5; }}
    h1 {{ font-size: 1.4rem; margin-bottom: 0.3rem; }}
    .meta {{ color: #555; margin-bottom: 1rem; line-height: 1.45; }}
    .warn {{ background: #fff6e6; border: 1px solid #e6c27a; padding: 12px 14px; border-radius: 8px; margin-bottom: 16px; }}
    table {{ border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
    th, td {{ border: 1px solid #ddd; padding: 8px 10px; font-size: 0.92rem; vertical-align: top; }}
    th {{ background: #1f4e79; color: #fff; text-align: left; position: sticky; top: 0; }}
    tr:nth-child(even) {{ background: #f3f6fa; }}
    a {{ color: #0b57d0; }}
  </style>
</head>
<body>
  <h1>Организации, которым нужны специалисты по охране труда / промышленной безопасности</h1>
  <p class="meta">
    Источник: публичный поиск на <a href="https://rabota.by" target="_blank" rel="noopener">rabota.by</a>
    (запросы «инженер по охране труда», «промышленная безопасность»).<br />
    Визитка для письма:
    <a href="http://ot-pb.by/promo/vizitka-rassylka.html" target="_blank" rel="noopener">vizitka-rassylka.html</a><br />
    Записей в таблице: <strong>{len(unique)}</strong>. Дата сбора: 23.08.2026.
  </p>
  <div class="warn">
    <strong>Важно:</strong> телефоны и e-mail часто скрыты кнопкой «показать контакты» —
    в таблице стоит «не указан», но есть ссылка на вакансию. Не выдумывайте контакты.
    Рассылайте только реальное предложение услуг, без массового спама.
  </div>
  <table>
    <thead>
      <tr>
        <th>№</th><th>Организация</th><th>Вакансия</th><th>Город</th>
        <th>Контактное лицо</th><th>Телефон</th><th>Email</th>
        <th>Ссылка на вакансию</th><th>Примечание</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows_html)}
    </tbody>
  </table>
</body>
</html>
"""
    html_path.write_text(html_out, encoding="utf-8")

    summary = {
        "total": len(unique),
        "csv": str(csv_path),
        "html": str(html_path),
        "with_phone": sum(1 for r in unique if r["Телефон"] != "не указан"),
        "with_email": sum(1 for r in unique if r["Email"] != "не указан"),
        "with_contact": sum(1 for r in unique if r["Контактное лицо"] != "не указан"),
        "sample": unique[:5],
    }
    (PROMO / "_tmp_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: summary[k] for k in summary if k != "sample"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
