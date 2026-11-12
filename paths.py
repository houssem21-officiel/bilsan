# -*- coding: utf-8 -*-
"""مكان ملفات البرنامج ومكان البيانات.

- عند التشغيل من الكود: كل شيء في مجلد البرنامج (كما كان).
- عند التشغيل من النسخة المثبّتة (Bilsan.exe): البيانات في C:\\ProgramData\\Bilsan
  لأن مجلد Program Files لا يُكتب فيه.
"""
import os
import sys

FROZEN = getattr(sys, "frozen", False)
# مكان الملفات الثابتة (الشعار، الأيقونة...)
APP_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
if FROZEN:
    _default = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), "Bilsan")
else:
    _default = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("BILSAN_DATA", _default)
os.makedirs(DATA_DIR, exist_ok=True)


def data(*p):
    return os.path.join(DATA_DIR, *p)
