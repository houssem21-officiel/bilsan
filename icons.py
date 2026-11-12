# -*- coding: utf-8 -*-
"""رموز البرنامج (أيقونات خطية مرسومة يدويًا، 24×24، بلون ذهبي/أخضر حسب المكان).

كل رمز = مسارات SVG. تُجمع كلها مرة واحدة في الصفحة (sprite) ثم تُستعمل بـ <use>.
"""
from markupsafe import Markup

I = {
    # ---------------- التنقل والصفحات
    "home": '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h5v-6h4v6h5V10"/>',
    "queue": '<circle cx="8" cy="7" r="3"/><path d="M2 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.4"/><path d="M15.5 14.3A5 5 0 0 1 22 19"/>',
    "reception": '<path d="M4 17h16"/><path d="M6 17a6 6 0 0 1 12 0"/><path d="M12 8V6"/><circle cx="12" cy="5" r="1"/><path d="M3 20h18"/>',
    "cash": '<rect x="2.5" y="6" width="19" height="12" rx="2"/><circle cx="12" cy="12" r="2.8"/><path d="M6 9.5v5M18 9.5v5"/>',
    "send": '<path d="M21 3L10 14"/><path d="M21 3l-7 18-4-7-7-4z"/>',
    "cart": '<path d="M3 4h2l2.4 11h11l2-8H6.3"/><circle cx="9" cy="19.5" r="1.4"/><circle cx="17" cy="19.5" r="1.4"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M8 14h2M14 14h2M8 17.5h2"/>',
    "plans": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/><path d="M3 17.5l9 5 9-5" opacity=".55"/>',
    "clients": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"/>',
    "more": '<rect x="3.5" y="3.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.6"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.6"/>',
    "rooms": '<path d="M5 21V4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v17"/><path d="M3 21h18"/><circle cx="15" cy="12.5" r="1"/>',
    "visits": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1"/><path d="M8.5 10h7M8.5 13.5h7M8.5 17h4"/>',
    "card": '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 9.5h19"/><path d="M6 15h4"/>',
    "debt": '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 11h6"/>',
    "lock": '<rect x="4.5" y="10.5" width="15" height="10.5" rx="2"/><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/><circle cx="12" cy="15.7" r="1.3"/>',
    "expense": '<path d="M20 7H5.5A2.5 2.5 0 0 1 3 4.5v0A2.5 2.5 0 0 1 5.5 2H18v5"/><path d="M3 4.5V19a2 2 0 0 0 2 2h15V7"/><path d="M16 14h4"/>',
    "invoice": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h6"/>',
    "course": '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c0 1.7 2.7 3 6 3s6-1.3 6-3v-5"/><path d="M22 9v6"/>',
    "staff": '<rect x="4" y="3" width="16" height="18" rx="2"/><circle cx="12" cy="10" r="3"/><path d="M7.5 18c.6-2.3 2.4-3.5 4.5-3.5s3.9 1.2 4.5 3.5"/><path d="M10 3v2h4V3"/>',
    "alert": '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4.5"/><circle cx="12" cy="17.3" r=".6"/>',
    "shield": '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "safe": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="12" cy="12" r="4"/><path d="M12 8v1.5M12 14.5V16M8 12h1.5M14.5 12H16"/><path d="M6 20v1.5M18 20v1.5"/>',
    "vault": '<path d="M3 10l9-6 9 6"/><path d="M5 10v8M9.5 10v8M14.5 10v8M19 10v8"/><path d="M3 21h18"/>',
    "reports": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/><path d="M4 10l6-6 6 9 5-5" opacity=".5"/>',
    "key": '<circle cx="8" cy="15" r="4.5"/><path d="M11.2 11.8L20 3"/><path d="M16.5 6.5l2.5 2.5M14.5 8.5l2 2"/>',
    "audit": '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1.2"/><circle cx="4.5" cy="12" r="1.2"/><circle cx="4.5" cy="18" r="1.2"/>',
    "backup": '<ellipse cx="12" cy="5.5" rx="8" ry="2.7"/><path d="M4 5.5v6c0 1.5 3.6 2.7 8 2.7s8-1.2 8-2.7v-6"/><path d="M4 11.5v6c0 1.5 3.6 2.7 8 2.7s8-1.2 8-2.7v-6"/>',
    "products": '<path d="M12 2.5l8.5 4.7v9.6L12 21.5l-8.5-4.7V7.2z"/><path d="M3.5 7.2L12 12l8.5-4.8M12 12v9.5"/><path d="M7.8 4.8l8.5 4.8" opacity=".6"/>',
    "truck": '<path d="M2 6h12v10H2z"/><path d="M14 9h4l3.5 3.5V16H14"/><circle cx="6" cy="18" r="1.8"/><circle cx="17.5" cy="18" r="1.8"/>',
    "services": '<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M19 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8zM5 16l.6 1.4 1.4.6-1.4.6L5 20l-.6-1.4L3 18l1.4-.6z"/>',
    "branch": '<path d="M3 21h18"/><path d="M5 21V9l7-5 7 5v12"/><path d="M9.5 21v-5h5v5"/><path d="M9 11h1.5M13.5 11H15"/>',
    "monitor": '<rect x="2.5" y="4" width="19" height="12.5" rx="1.8"/><path d="M8 21h8M12 16.5V21"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6.5 6.5-6.5s6.5 2.9 6.5 6.5"/><path d="M17 4.5a3.5 3.5 0 0 1 0 7M21.5 20a6.5 6.5 0 0 0-3.5-5.8"/>',
    "sms": '<path d="M4 4h16a1.5 1.5 0 0 1 1.5 1.5v10A1.5 1.5 0 0 1 20 17H9l-5 4v-4H4a1.5 1.5 0 0 1-1.5-1.5v-10A1.5 1.5 0 0 1 4 4z"/><path d="M7.5 10.5h.01M12 10.5h.01M16.5 10.5h.01" stroke-width="2.6"/>',
    "settings": '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v2.6M12 18.9v2.6M2.5 12h2.6M18.9 12h2.6M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/><circle cx="12" cy="12" r="6.6"/>',
    "logout": '<path d="M10 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h5"/><path d="M15 8l4 4-4 4M19 12H9"/>',
    "sync": '<path d="M20 11a8 8 0 0 0-14.3-4.9L4 8"/><path d="M4 3v5h5"/><path d="M4 13a8 8 0 0 0 14.3 4.9L20 16"/><path d="M20 21v-5h-5"/>',
    "medical": '<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z"/>',
    "camera": '<path d="M3 8a2 2 0 0 1 2-2h2.5L9 4h6l1.5 2H19a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><circle cx="12" cy="13" r="3.8"/>',
    "sign": '<path d="M3 17c3-1 4-6 6-6s-1 7 2 7 3-4 5-4 2 2 5 2"/><path d="M3 21h18"/>',
    "phone": '<path d="M5 3h3.5l1.8 4.5-2.3 1.4a11 11 0 0 0 7.1 7.1l1.4-2.3L21 15.5V19a2 2 0 0 1-2 2A16 16 0 0 1 3 5a2 2 0 0 1 2-2z"/>',
    "gift": '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M5 12v9h14v-9M12 8v13"/><path d="M12 8C10 4 6.5 4.5 7 6.5S12 8 12 8zM12 8c2-4 5.5-3.5 5-1.5S12 8 12 8z"/>',
    "print": '<path d="M7 9V3h10v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/>',
    # ---------------- الخدمات
    "hijama": '<path d="M7 9h10v3a5 5 0 0 1-10 0z"/><path d="M9 9V6.5a3 3 0 0 1 6 0V9"/><path d="M5 20c2-1.5 4-1.5 7 0s5 1.5 7 0"/>',
    "needle": '<path d="M14.5 3.5l6 6"/><path d="M17.5 6.5L8 16l-2.5.5L6 14l9.5-9.5"/><path d="M11 8l1.5 1.5M9 10l1.5 1.5"/><path d="M6 18l-3 3"/>',
    "bee": '<ellipse cx="12" cy="14" rx="4" ry="5.5"/><path d="M8.3 12h7.4M8.3 15.5h7.4"/><path d="M12 8.5c-1-2.5-4-3.5-6-2.5s-1 4 2.5 4.5M12 8.5c1-2.5 4-3.5 6-2.5s1 4-2.5 4.5"/><path d="M12 19.5v2"/>',
    "plasma": '<path d="M12 3c3.5 4.3 6 7.6 6 11a6 6 0 0 1-12 0c0-3.4 2.5-6.7 6-11z"/><path d="M9.3 14.5a2.8 2.8 0 0 0 2.7 2.8"/>',
    "face": '<path d="M12 3c-4.4 0-7 3.4-7 8 0 5.2 3.3 10 7 10s7-4.8 7-10c0-4.6-2.6-8-7-8z"/><path d="M9 11h.01M15 11h.01" stroke-width="2.4"/><path d="M9.5 15.5c1.4 1.2 3.6 1.2 5 0"/><path d="M5.5 9C8 9 11 7 12 4.5" opacity=".6"/>',
    "laser": '<path d="M4 20l7-7"/><rect x="2" y="17.5" width="5" height="3.5" rx="1" transform="rotate(-45 4.5 19.25)"/><path d="M13 11l7-7"/><path d="M16 12.5l3 1M11.5 8l-1-3M17.5 9.5l3.5-.5" opacity=".7"/>',
    "hair": '<path d="M6 21c0-7 1-13 6-18"/><path d="M11 21c0-6 1.5-11 6-16"/><path d="M16 21c0-5 1.5-8 4-11"/>',
    "bolt": '<path d="M13 2L4.5 13.5H12L11 22l8.5-11.5H12z"/>',
    "slim": '<path d="M9 3c-1 3-1 6 1 9s2 6 1 9M15 3c1 3 1 6-1 9s-2 6-1 9"/><path d="M5 12h3M16 12h3"/>',
    "glow": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    "leaf": '<path d="M5 19c0-8 5-14 15-15-1 10-7 15-15 15z"/><path d="M5 19c3-4 6-7 10-10"/>',
    # ---------------- المنتجات
    "oil": '<path d="M10 2.5h4v3h-4z"/><path d="M9 5.5h6l1 3v11a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-11z"/><path d="M12 12c1.4 1.7 2 2.7 2 3.6a2 2 0 0 1-4 0c0-.9.6-1.9 2-3.6z"/>',
    "spray": '<path d="M8 9h7v12H8z"/><path d="M9.5 9V6h4v3"/><path d="M9.5 6h-1.5V4.5h5"/><path d="M17 4l2-1M17 6.5h2.5M17 9l2 1"/>',
    "cream": '<path d="M4 10h16v8a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3z"/><rect x="5.5" y="6" width="13" height="4" rx="1"/><path d="M8.5 14.5h7" opacity=".6"/>',
    "honey": '<path d="M7 8h10l1 3v8a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-8z"/><path d="M8 5h8v3H8z"/><path d="M9.5 13.5l1.3-.8 1.2.8v1.5l-1.2.7-1.3-.7zM12 13.5l1.3-.8 1.2.8v1.5l-1.2.7-1.2-.7"/>',
    "capsule": '<rect x="2.8" y="8.3" width="18.4" height="7.4" rx="3.7" transform="rotate(-45 12 12)"/><path d="M9.4 9.4l5.2 5.2"/>',
    "water": '<path d="M7 3h10l-1 18H8z"/><path d="M7.4 9.5c1.6-1 3.1-1 4.6 0s3 1 4.6 0"/>',
    "roller": '<rect x="4" y="3" width="11" height="6" rx="3"/><path d="M15 6h3v5h-7.5v3"/><path d="M10.5 14h0v7"/><path d="M6 4.5v3M9.5 4.5v3M13 4.5v3" opacity=".6"/>',
    "seed": '<path d="M12 21V11"/><path d="M12 13c-4 0-6-2.5-6-6 4 0 6 2.5 6 6zM12 11c0-4 2-6.5 6-6.5 0 4-2 6.5-6 6.5z"/>',
}

# ------------------------------------------------------------------ اختيار الرمز حسب الاسم
ITEM_RULES = [
    ("hijama", ("حجام",)), ("bee", ("سم النحل", "العكبر", "حبوب اللقاح", "الطلع")),
    ("laser", ("ليزر",)), ("bolt", ("كهرب", "إليكتروليز")),
    ("hair", ("شعر",)), ("plasma", ("بلازما",)),
    ("needle", ("إبر", "حقن", "فيلر", "ميزو")),
    ("slim", ("تخسيس", "منحف", "مُنحف", "مسمن", "مُسمن")),
    ("glow", ("تبييض", "نضارة", "أوكسي")),
    ("face", ("بشرة", "وجه", "تقشير", "تنظيف", "الرؤوس")),
    ("honey", ("عسل",)), ("spray", ("بخاخ",)), ("oil", ("زيت", "دهن")),
    ("cream", ("كريم", "مرهم")), ("water", ("ماء",)), ("roller", ("رولر",)),
    ("seed", ("جنسنغ", "ماكا", "نخيل")), ("capsule", ("تركيبة", "كبسول", "حبوب")),
    ("course", ("دورة", "تكوين")),
]


def item_icon(name, kind="service"):
    n = name or ""
    for ic, words in ITEM_RULES:
        if any(w in n for w in words):
            return ic
    return "services" if kind == "service" else "leaf"


def sprite():
    body = "".join(f'<symbol id="i-{k}" viewBox="0 0 24 24">{v}</symbol>' for k, v in I.items())
    return Markup('<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
                  '<defs></defs>' + body + '</svg>')


def ic(name, cls=""):
    if name not in I:
        name = "services"
    return Markup(f'<svg class="ic {cls}" width="1em" height="1em" aria-hidden="true"><use href="#i-{name}"/></svg>')


def item(name, kind="service"):
    """رمز صغير داخل مربع لطيف أمام اسم خدمة أو منتج."""
    return Markup(f'<span class="itm">{ic(item_icon(name, kind))}</span>')


def avatar(name):
    """دائرة بأول حرف من اسم الزبون، بلون ثابت لكل اسم."""
    n = (name or "?").strip()
    first = n[0] if n else "?"
    hue = [152, 168, 30, 190, 140, 24, 176, 44][sum(map(ord, n)) % 8]
    return Markup(f'<span class="av" style="--h:{hue}">{first}</span>')
