# -*- coding: utf-8 -*-
"""النسخ الاحتياطي التلقائي لقاعدة بيانات بيلسان.

- كل 6 ساعات (وعند تشغيل البرنامج) تُصنع نسخة كاملة مضغوطة في D:\\Bilsan_Backup
  (أو مجلد backups بجانب البرنامج إذا لم يوجد قرص D)، وفي مجلد ثانٍ اختياري (فلاشة، Google Drive).
- الاحتفاظ: كل النسخ لآخر 30 يومًا، ثم نسخة لكل شهر، ونسخة لكل سنة إلى الأبد.
- النسخة تُصنع والبرنامج يعمل، دون إيقافه (sqlite backup).
"""
import os
import shutil
import sqlite3
import threading
import time
import zipfile
from datetime import datetime, timedelta

from paths import DATA_DIR as BASE_DIR  # مكان البيانات
PREFIX = "bilsan_"


def default_dir():
    if os.name == "nt" and os.path.exists("D:\\"):
        return "D:\\Bilsan_Backup"
    return os.path.join(BASE_DIR, "backups")


def make_backup(db_path, dirs):
    """ينسخ قاعدة البيانات إلى ملف zip في كل مجلد. يعيد (المسار, الحجم) أو يرفع خطأ."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    tmp = os.path.join(BASE_DIR, f".backup_{stamp}.db")
    src = sqlite3.connect(db_path, timeout=60)
    dst = sqlite3.connect(tmp)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    # فحص سلامة النسخة قبل اعتمادها
    chk = sqlite3.connect(tmp)
    ok = chk.execute("PRAGMA quick_check").fetchone()[0]
    chk.close()
    if ok != "ok":
        os.remove(tmp)
        raise RuntimeError("النسخة غير سليمة: " + ok)
    first = None
    errors = []
    for d in dirs:
        if not d:
            continue
        try:
            os.makedirs(d, exist_ok=True)
            out = os.path.join(d, f"{PREFIX}{stamp}.zip")
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                z.write(tmp, "bilsan.db")
            first = first or out
            rotate(d)
        except Exception as e:
            errors.append(f"{d}: {e}")
    os.remove(tmp)
    if not first:
        raise RuntimeError("تعذر الحفظ في مجلد النسخ: " + "؛ ".join(errors))
    return first, os.path.getsize(first), errors


def list_backups(d):
    if not d or not os.path.isdir(d):
        return []
    out = []
    for f in os.listdir(d):
        if f.startswith(PREFIX) and f.endswith(".zip"):
            try:
                dt = datetime.strptime(f[len(PREFIX):-4], "%Y-%m-%d_%H-%M")
            except ValueError:
                continue
            out.append(dict(name=f, path=os.path.join(d, f), dt=dt, size=os.path.getsize(os.path.join(d, f))))
    return sorted(out, key=lambda x: x["dt"], reverse=True)


def rotate(d, keep_days=30):
    """آخر 30 يومًا: كل النسخ. أقدم من ذلك: أول نسخة من كل شهر فقط (فتبقى نسخة لكل شهر ولكل سنة)."""
    limit = datetime.now() - timedelta(days=keep_days)
    seen_month = set()
    for b in sorted(list_backups(d), key=lambda x: x["dt"]):
        if b["dt"] >= limit:
            continue
        key = b["dt"].strftime("%Y-%m")
        if key in seen_month:
            try:
                os.remove(b["path"])
            except OSError:
                pass
        else:
            seen_month.add(key)


def apply_pending_restore(db_path):
    """عند تشغيل البرنامج: إذا طلبت المديرة استرجاع نسخة، تُستبدل قاعدة البيانات قبل فتحها."""
    flag = os.path.join(BASE_DIR, "restore_pending.txt")
    if not os.path.exists(flag):
        return None
    with open(flag, encoding="utf-8") as f:
        src = f.read().strip()
    os.remove(flag)
    if not os.path.exists(src):
        return f"الملف غير موجود: {src}"
    keep = db_path + datetime.now().strftime(".before_restore_%Y-%m-%d_%H-%M")
    if os.path.exists(db_path):
        shutil.copy2(db_path, keep)
    for ext in ("-wal", "-shm"):
        if os.path.exists(db_path + ext):
            os.remove(db_path + ext)
    with zipfile.ZipFile(src) as z:
        with z.open("bilsan.db") as zf, open(db_path, "wb") as out:
            shutil.copyfileobj(zf, out)
    return f"تم الاسترجاع من {os.path.basename(src)} (النسخة السابقة محفوظة باسم {os.path.basename(keep)})"


_lock = threading.Lock()


def run_backup(connect, db_path, reason="تلقائي"):
    """ينفذ نسخة ويسجل النتيجة في الإعدادات."""
    with _lock:
        con = connect()
        s = {r["key"]: r["value"] for r in con.execute("SELECT key, value FROM settings WHERE key LIKE 'backup%'")}
        d1 = s.get("backup_dir") or default_dir()
        d2 = s.get("backup_dir2") or ""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            path, size, errs = make_backup(db_path, [d1, d2])
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('backup_last',?)", (now,))
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('backup_last_size',?)", (str(size),))
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('backup_error',?)", ("؛ ".join(errs),))
            con.commit()
            return True, path
        except Exception as e:
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('backup_error',?)", (f"{now}: {e}"[:400],))
            con.commit()
            return False, str(e)
        finally:
            con.close()


def backup_loop(connect, db_path, every_hours=6):
    time.sleep(60)  # دقيقة بعد التشغيل
    while True:
        try:
            con = connect()
            r = con.execute("SELECT value FROM settings WHERE key='backup_last'").fetchone()
            h = con.execute("SELECT value FROM settings WHERE key='backup_every_hours'").fetchone()
            con.close()
            hours = float(h[0]) if h and h[0] else every_hours
            last = datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S") if r and r[0] else None
            if not last or datetime.now() - last >= timedelta(hours=hours):
                run_backup(connect, db_path)
        except Exception as e:
            print("backup error:", e)
        time.sleep(30 * 60)
