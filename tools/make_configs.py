# -*- coding: utf-8 -*-
"""يحضّر ملفات الإعداد لكل ملف تثبيت: build/cfg/<Variant>/...

Central  -> seed.json   (مفتاح الربط + الحواسيب + كلمة سر المديرة)
<Device> -> node.json   (الفرع، رقم الحاسوب، عنوان الحاسوب المركزي، مفتاح الربط)
Setup    -> pair.flag   (حاسوب جديد: يطلب رمز الربط من المديرة)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(ROOT, "config", "devices.json"), encoding="utf-8"))
out = os.path.join(ROOT, "build", "cfg")


def write(variant, name, data):
    d = os.path.join(out, variant)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False, indent=1)


write("Central", "seed.json", {"sync_key": cfg["sync_key"], "admin_password": cfg["admin_password"],
                               "devices": [{k: v for k, v in d.items() if k != "file"} for d in cfg["devices"]]})
for d in cfg["devices"]:
    write(d["file"], "node.json", {"branch_id": d["branch_id"], "slot": d["slot"], "device": d["username"],
                                   "central_url": cfg["central_url"], "key": cfg["sync_key"]})
write("Setup", "pair.flag", "1")
variants = ["Central"] + [d["file"] for d in cfg["devices"]] + ["Setup"]
print(" ".join(variants))
if len(sys.argv) > 1:
    with open(sys.argv[1], "w") as f:
        f.write("\n".join(variants))
