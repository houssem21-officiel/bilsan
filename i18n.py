"""الترجمة: كل عامل يختار لغتو (العربية، الفرنسية، الإنجليزية).

البرنامج مكتوب بالعربية. كي تكون اللغة فرنسية ولا إنجليزية، الصفحة تتترجم قبل ما تتبعث:
كل جملة عربية في الصفحة تتبدّل بترجمتها من القاموس (i18n_dict.json).
- ما نبدّلوش value="..." (القيم اللي تتبعث في الاستمارات) ولا محتوى <textarea> (كتابة العمال).
- <option> بلا value: نزيدولها value بالنص العربي الأصلي باش الاستمارة تبقى صحيحة.
- أسماء الزبائن والملاحظات ما تتبدّلش (ما هيش في القاموس).
"""
import json
import os
import re

LANGS = {"ar": "العربية", "fr": "Français", "en": "English"}
_IDX = {"fr": 0, "en": 1}
import sys
_HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
try:
    with open(os.path.join(_HERE, "i18n_dict.json"), encoding="utf-8") as f:
        DICT = json.load(f)
except Exception:  # noqa: BLE001
    DICT = {}

RUN = re.compile(r"[ء-ي](?:[ء-يٰ-ۓً-ٟ ]|ـ)*")
# الجمل حسب أول كلمة (للبحث على أطول جملة معروفة داخل نص مختلط)
_BY_FIRST = {}
for _k in DICT:
    _w = _k.split()
    _BY_FIRST.setdefault(_w[0], []).append((len(_w), _k))
for _v in _BY_FIRST.values():
    _v.sort(reverse=True)

_TOKEN = re.compile(r"(<!--.*?-->|<[^>]+>)", re.S)
_ATTR = re.compile(r'(\s(?:title|placeholder|aria-label|alt|onclick|onsubmit|onchange|data-confirm)\s*=\s*")([^"]*)(")', re.I)
_OPTION_NOVAL = re.compile(r"<option(?![^>]*\bvalue\s*=)([^>]*)>([^<]*)</option>", re.I)
_CACHE = {}


def _phrase(run, i):
    """ترجمة جملة عربية وحدة. ترجع None إذا ما نعرفوهاش."""
    key = run.strip()
    t = DICT.get(key)
    if t:
        return t[i]
    words = key.split()
    out, known, j = [], 0, 0
    while j < len(words):
        hit = None
        for n, k in _BY_FIRST.get(words[j], ()):
            if n <= len(words) - j and words[j:j + n] == k.split():
                hit = (n, k)
                break
        if hit:
            out.append(DICT[hit[1]][i])
            known += hit[0]
            j += hit[0]
        else:
            out.append(words[j])
            j += 1
    # نقبلو الترجمة غير إذا أغلب الكلمات معروفة (باش ما نخلطوش أسماء الزبائن وكتابتهم)
    if known and known >= 0.6 * len(words):
        return " ".join(out)
    return None


def tr_text(s, lang):
    i = _IDX[lang]

    def sub(m):
        run = m.group(0)
        ck = (lang, run)
        if ck not in _CACHE:
            t = _phrase(run, i)
            if t is not None:
                lead = run[:len(run) - len(run.lstrip())]
                trail = run[len(run.rstrip()):]
                t = lead + t + trail
            if len(_CACHE) < 50000:
                _CACHE[ck] = t
            else:
                return t if t is not None else run
        t = _CACHE[ck]
        return t if t is not None else run
    return RUN.sub(sub, s).translate(_PUNCT)


_PUNCT = str.maketrans({"،": ",", "؛": ";", "؟": "?", "«": "«", "»": "»"})


def t(s, lang):
    """ترجمة نص واحد (للاستعمال في الكود)."""
    if not s or lang not in _IDX:
        return s
    return tr_text(s, lang)


def translate_html(html, lang):
    if lang not in _IDX or not html:
        return html
    html = _OPTION_NOVAL.sub(lambda m: f'<option value="{m.group(2).strip()}"{m.group(1)}>{m.group(2)}</option>', html)
    parts = _TOKEN.split(html)
    out = []
    skip = None  # داخل textarea / style
    for p in parts:
        if not p:
            continue
        if p.startswith("<"):
            low = p[:12].lower()
            if low.startswith("<html"):
                p = re.sub(r'lang="ar"', f'lang="{lang}"', p)
                p = re.sub(r'dir="rtl"', 'dir="ltr"', p)
            if skip:
                if low.startswith("</" + skip):
                    skip = None
                out.append(p)
                continue
            if low.startswith("<textarea"):
                skip = "textarea"
            elif low.startswith("<style"):
                skip = "style"
            if not p.startswith("<!--"):
                p = _ATTR.sub(lambda m: m.group(1) + tr_text(m.group(2), lang) + m.group(3), p)
            out.append(p)
        else:
            out.append(p if skip else tr_text(p, lang))
    return "".join(out)
