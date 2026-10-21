"""What a ``qr`` block encodes: the text as written, or a contact card, a calendar entry, a Wi-Fi network, an
e-mail, a phone number, a text message or a place, written in the standard form that phones read.

The structured types take ``key: value`` lines, so a poster never needs the vCard or iCalendar syntax and its
escaping. A line may be repeated where that makes sense (two ``tel:`` lines are two numbers).
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote

TYPES = ("url", "text", "vcard", "event", "wifi", "email", "phone", "sms", "geo")
ALIASES = {
    "contact": "vcard",
    "vcf": "vcard",
    "ical": "event",
    "ics": "event",
    "calendar": "event",
    "tel": "phone",
    "mail": "email",
    "mailto": "email",
}
EXTENSIONS = {".vcf": "vcard", ".vcard": "vcard", ".ics": "event", ".ical": "event"}
KEYS = {
    "vcard": ("name", "first", "last", "org", "title", "tel", "mobile", "email", "url", "address", "note"),
    "event": ("title", "start", "end", "location", "description", "url"),
    "wifi": ("ssid", "password", "security", "hidden"),
    "email": ("to", "subject", "body"),
    "phone": ("number",),
    "sms": ("number", "body"),
    "geo": ("lat", "lon"),
}
_LINE = re.compile(r"^\s*([A-Za-z][\w-]*)\s*:\s?(.*)$")


class QrError(ValueError):
    """The block's lines do not make the type it asks for. The message says what is wrong."""


def kind_of(value: str | None) -> str:
    kind = ALIASES.get((value or "url").lower(), (value or "url").lower())
    if kind not in TYPES:
        raise QrError(f"type must be one of {', '.join(TYPES)}, not '{value}'")
    return kind


def payload(kind: str, text: str) -> str:
    """The text to put in the code for a block of ``kind`` whose lines are ``text``."""
    text = text.strip("\n")
    if not text.strip():
        raise QrError("a qr block needs the text or address to encode")
    if kind in ("url", "text"):
        return text.strip() if kind == "url" else text
    if re.match(r"^\s*(BEGIN:V|WIFI:|MAILTO:|TEL:|SMSTO:|GEO:)", text, re.IGNORECASE):
        return text.strip()  # already in the standard form, such as a .vcf file's text
    fields = _fields(kind, text)
    return {
        "vcard": _vcard,
        "event": _event,
        "wifi": _wifi,
        "email": _email,
        "phone": _phone,
        "sms": _sms,
        "geo": _geo,
    }[kind](fields)


def _fields(kind: str, text: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        match = _LINE.match(line)
        if not match:
            raise QrError(f"line {number} of a type={kind} block is not 'key: value': '{line.strip()}'")
        key, value = match.group(1).lower(), match.group(2).strip()
        if key not in KEYS[kind]:
            raise QrError(f"type={kind} has no '{key}'. Keys: {', '.join(KEYS[kind])}")
        fields.setdefault(key, []).append(value)
    return fields


def _one(fields: dict, key: str, kind: str, required: bool = False) -> str:
    values = fields.get(key, [])
    if len(values) > 1:
        raise QrError(f"type={kind} takes one '{key}', not {len(values)}")
    if required and not (values and values[0]):
        raise QrError(f"type={kind} needs a '{key}:' line")
    return values[0] if values else ""


# --- vCard 3.0 -----------------------------------------------------------------------------------


def _v(text: str) -> str:
    """A vCard or iCalendar text value: backslash, comma, semicolon and new lines escaped."""
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def _vcard(fields: dict) -> str:
    name = _one(fields, "name", "vcard")
    first, last = _one(fields, "first", "vcard"), _one(fields, "last", "vcard")
    if not name and not (first or last):
        if not _one(fields, "org", "vcard"):
            raise QrError("type=vcard needs a 'name:' line (or first: and last:, or org: for a company)")
    if name and not (first or last):
        *given, family = name.split()
        first, last = " ".join(given), family
    full = name or " ".join(p for p in (first, last) if p) or _one(fields, "org", "vcard")
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"N:{_v(last)};{_v(first)};;;", f"FN:{_v(full)}"]
    if fields.get("org"):
        lines.append(f"ORG:{_v(_one(fields, 'org', 'vcard'))}")
    if fields.get("title"):
        lines.append(f"TITLE:{_v(_one(fields, 'title', 'vcard'))}")
    lines += [f"TEL;TYPE=WORK,VOICE:{n}" for n in fields.get("tel", [])]
    lines += [f"TEL;TYPE=CELL:{n}" for n in fields.get("mobile", [])]
    lines += [f"EMAIL;TYPE=INTERNET:{e}" for e in fields.get("email", [])]
    lines += [f"URL:{u}" for u in fields.get("url", [])]
    for address in fields.get(
        "address", []
    ):  # one line, its parts separated by commas: street, town, postcode, country
        parts = [p.strip() for p in address.split(",")]
        street, town, code, country = (
            (parts + ["", "", "", ""])[:4] if len(parts) <= 4 else (", ".join(parts[:-3]), *parts[-3:])
        )
        lines.append(f"ADR;TYPE=WORK:;;{_v(street)};{_v(town)};;{_v(code)};{_v(country)}")
    if fields.get("note"):
        lines.append(f"NOTE:{_v(_one(fields, 'note', 'vcard'))}")
    return "\r\n".join([*lines, "END:VCARD"])


# --- iCalendar event -----------------------------------------------------------------------------


def _when(text: str, key: str) -> tuple[datetime | date, bool]:
    """A date (an all-day event) or a date and time, as YYYY-MM-DD or YYYY-MM-DD HH:MM. A trailing Z is UTC."""
    value = text.strip().replace("T", " ")
    utc = value.endswith("Z")
    value = value.rstrip("Z").strip()
    for pattern, is_date in (("%Y-%m-%d", True), ("%Y-%m-%d %H:%M", False), ("%Y-%m-%d %H:%M:%S", False)):
        try:
            parsed = datetime.strptime(value, pattern)
        except ValueError:
            continue
        return (parsed.date() if is_date else parsed), utc
    raise QrError(f"type=event: {key} must be YYYY-MM-DD or YYYY-MM-DD HH:MM, not '{text.strip()}'")


def _ical(moment: datetime | date, utc: bool) -> str:
    if isinstance(moment, datetime):
        return moment.strftime("%Y%m%dT%H%M%S") + ("Z" if utc else "")
    return moment.strftime("%Y%m%d")


def _event(fields: dict) -> str:
    title = _one(fields, "title", "event", required=True)
    start, utc = _when(_one(fields, "start", "event", required=True), "start")
    if fields.get("end"):
        end, end_utc = _when(_one(fields, "end", "event"), "end")
        if type(end) is not type(start) or end_utc != utc:
            raise QrError("type=event: start and end must both be dates, or both dates and times in the same zone")
        if end < start:
            raise QrError("type=event: end is before start")
    else:
        end, end_utc = (
            (start + timedelta(days=1) if not isinstance(start, datetime) else start + timedelta(hours=1)),
            utc,
        )
    if isinstance(start, datetime):
        timing = [f"DTSTART:{_ical(start, utc)}", f"DTEND:{_ical(end, end_utc)}"]
    else:  # an all-day event ends on the day after its last day
        last = end + timedelta(days=1) if fields.get("end") else end
        timing = [f"DTSTART;VALUE=DATE:{_ical(start, False)}", f"DTEND;VALUE=DATE:{_ical(last, False)}"]
    stamp = start if isinstance(start, datetime) else datetime(start.year, start.month, start.day)
    uid = hashlib.sha256(f"{title}|{start}".encode()).hexdigest()[:16]  # the same poster gives the same event
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//py-doc//poster//EN", "BEGIN:VEVENT",
        f"UID:{uid}@py-doc", f"DTSTAMP:{stamp.strftime('%Y%m%dT%H%M%S')}Z", *timing, f"SUMMARY:{_v(title)}",
    ]  # fmt: skip
    for key, prop in (("location", "LOCATION"), ("description", "DESCRIPTION")):
        if fields.get(key):
            lines.append(f"{prop}:{_v(_one(fields, key, 'event'))}")
    if fields.get("url"):
        lines.append(f"URL:{_one(fields, 'url', 'event')}")
    return "\r\n".join([*lines, "END:VEVENT", "END:VCALENDAR"])


# --- the rest ------------------------------------------------------------------------------------


def _w(text: str) -> str:
    """A Wi-Fi field: backslash, semicolon, comma, colon and double quote escaped."""
    return re.sub(r'([\\;,:"])', r"\\\1", text)


def _wifi(fields: dict) -> str:
    ssid = _one(fields, "ssid", "wifi", required=True)
    password = _one(fields, "password", "wifi")
    security = (_one(fields, "security", "wifi") or ("WPA" if password else "nopass")).upper()
    if security in ("NONE", "OPEN", "NOPASS"):
        security = "nopass"
    if security not in ("WPA", "WPA2", "WPA3", "WEP", "SAE", "nopass"):
        raise QrError(f"type=wifi: security must be WPA, WEP or none, not '{security}'")
    if security != "nopass" and not password:
        raise QrError(f"type=wifi: security {security} needs a 'password:' line")
    security = "WPA" if security in ("WPA2", "WPA3", "SAE") else security  # what the WIFI: form names WPA2 and WPA3
    hidden = _one(fields, "hidden", "wifi").lower() in ("true", "yes", "1")
    text = (
        f"WIFI:T:{security};S:{_w(ssid)};" + (f"P:{_w(password)};" if password else "") + ("H:true;" if hidden else "")
    )
    return text + ";"


def _email(fields: dict) -> str:
    to = _one(fields, "to", "email", required=True)
    query = "&".join(f"{k}={quote(_one(fields, k, 'email'), safe='')}" for k in ("subject", "body") if fields.get(k))
    return f"mailto:{to}" + (f"?{query}" if query else "")


def _number(fields: dict, kind: str) -> str:
    number = re.sub(r"[\s().-]", "", _one(fields, "number", kind, required=True))
    if not re.fullmatch(r"\+?\d{3,}", number):
        raise QrError(f"type={kind}: '{fields['number'][0]}' is not a phone number")
    return number


def _phone(fields: dict) -> str:
    return f"tel:{_number(fields, 'phone')}"


def _sms(fields: dict) -> str:
    body = _one(fields, "body", "sms")
    return f"SMSTO:{_number(fields, 'sms')}:{body}"


def _geo(fields: dict) -> str:
    values = []
    for key, limit in (("lat", 90), ("lon", 180)):
        raw = _one(fields, key, "geo", required=True)
        try:
            value = float(raw)
        except ValueError:
            raise QrError(f"type=geo: {key} must be a number, not '{raw}'") from None
        if abs(value) > limit:
            raise QrError(f"type=geo: {key} must be between -{limit} and {limit}")
        values.append(raw)
    return f"geo:{values[0]},{values[1]}"
