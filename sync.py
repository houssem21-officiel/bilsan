# -*- coding: utf-8 -*-
"""
المزامنة بين الحاسوب المركزي (الحروش) وحاسوب استقبال فرع (سكيكدة).

- الحاسوب المركزي: يعمل كالعادة، ويستقبل عمليات الفرع ويرسل له القوائم والتعديلات.
- حاسوب الفرع (وضع "فرع"): عنده قاعدة بيانات محلية، يعمل بدون إنترنت،
  وكل 30 ثانية يرسل ما سجّله ويستقبل ما تغيّر في المركزي عندما يتوفر الاتصال.

كل جدول متزامن فيه عمودان: _upd (وقت آخر تعديل) و _rcv (وقت استلامه في المركزي).
عمليات الفرع تأخذ أرقامًا سالبة خاصة بالفرع حتى لا تتكرر الأرقام بين الحاسوبين.
"""
import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from urllib import request as urlreq, error as urlerr

from paths import DATA_DIR as BASE_DIR  # node.json يوضع مع البيانات

# الجداول المتزامنة (كلها بمفتاح id)
SYNC_TABLES = ["branches", "departments", "posts", "users", "services", "products", "clients",
               "appointments", "plans", "charges", "payments", "sale_items", "stock_moves",
               "employees", "attendance", "grants", "visits", "visit_items", "courses", "course_trainees",
               "client_notes", "client_photos", "perms", "audit", "cash_days", "expenses"]
# جداول عامة يرسلها المركزي كاملة للفرع
CATALOG = ["branches", "departments", "posts", "users", "services", "products", "clients", "client_notes", "perms"]
# جداول خاصة بفرع (فيها branch_id)
BRANCH_OWNED = ["appointments", "plans", "charges", "payments", "stock_moves", "employees", "visits", "courses", "client_photos", "audit", "cash_days", "expenses"]
# جداول يرسلها الفرع للمركزي فقط (مصاريف المديرة وسجل العمليات لا تنزل إلى حاسوب الفرع)
PUSH_ONLY = {"audit", "expenses"}
# جداول تابعة عبر جدول آخر
VIA = {
    "sale_items": "payment_id IN (SELECT id FROM payments WHERE branch_id=?)",
    "attendance": "employee_id IN (SELECT id FROM employees WHERE branch_id=?)",
    "grants": "employee_id IN (SELECT id FROM employees WHERE branch_id=?)",
    "visit_items": "visit_id IN (SELECT id FROM visits WHERE branch_id=?)",
    "course_trainees": "course_id IN (SELECT id FROM courses WHERE branch_id=?)",
}
# إعدادات لا تُنقل من المركزي إلى الفرع
LOCAL_SETTINGS = {"last_stock_sms", "sync_key", "backup_dir", "backup_dir2", "backup_last", "backup_last_size",
                  "backup_error", "backup_every_hours", "last_birthday_run"}
SPAN = 10 ** 9


def utcnow():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:23]


# ---------------------------------------------------------------- إعداد وضع الفرع
def load_node():
    """يقرأ node.json إن وُجد:
    {"branch_id": 1, "slot": 101, "device": "dev-101", "central_url": "http://bilsan-central:5000", "key": "..."}"""
    path = os.environ.get("BILSAN_NODE", os.path.join(BASE_DIR, "node.json"))
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        if cfg.get("branch_id") and cfg.get("central_url"):
            cfg["branch_id"] = int(cfg["branch_id"])
            # رقم الحاسوب: كل حاسوب له مجال أرقام خاص به (حاسوب سكيكدة القديم = رقم فرعه)
            cfg["slot"] = int(cfg.get("slot") or cfg["branch_id"])
            cfg["central_url"] = cfg["central_url"].rstrip("/")
            return cfg
    return None


NODE = load_node()

_INS = re.compile(r"^\s*INSERT\s+(OR\s+\w+\s+)?INTO\s+(\w+)\s*\(([^)]*)\)\s*VALUES\s*\(", re.I | re.S)


class BilConn(sqlite3.Connection):
    """اتصال قاعدة البيانات: في وضع الفرع يعطي كل سطر جديد رقمًا سالبًا خاصًا بالفرع."""
    applying = False

    def execute(self, sql, params=()):
        if NODE and not self.applying:
            m = _INS.match(sql)
            if m and m.group(2) in SYNC_TABLES:
                cols = [c.strip() for c in m.group(3).split(",")]
                if "id" not in cols:
                    new_id = self.next_node_id(m.group(2))
                    sql = sql[:m.start(3)] + "id," + sql[m.start(3):m.end()] + "?," + sql[m.end():]
                    params = (new_id,) + tuple(params)
        return super().execute(sql, params)

    def next_node_id(self, table):
        b = NODE["slot"]
        hi, lo = -(b * SPAN) - 1, -((b + 1) * SPAN) + 1
        r = super().execute(f"SELECT MIN(id) FROM {table} WHERE id BETWEEN ? AND ?", (lo, hi)).fetchone()[0]
        return hi if r is None else r - 1


def setup_connection(con):
    con.create_function("bil_applying", 0, lambda: 1 if con.applying else 0)


def install(con):
    """يضيف أعمدة التتبع والمشغّلات (triggers) لكل جدول متزامن."""
    con.execute("CREATE TABLE IF NOT EXISTS _deleted(tbl TEXT, rid INTEGER, at TEXT, _rcv TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS _sync_state(k TEXT PRIMARY KEY, v TEXT)")
    for t in SYNC_TABLES:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
        for c in ("_upd", "_rcv", "_dirty"):
            if c not in cols:
                con.execute(f"ALTER TABLE {t} ADD COLUMN {c} {'INTEGER DEFAULT 0' if c == '_dirty' else 'TEXT'}")
        con.execute(f"UPDATE {t} SET _upd='2000-01-01 00:00:00.000' WHERE _upd IS NULL")
        con.execute(f"CREATE INDEX IF NOT EXISTS ix_{t}_upd ON {t}(_upd)")
        con.execute(f"CREATE INDEX IF NOT EXISTS ix_{t}_rcv ON {t}(_rcv)")
        con.execute(f"CREATE INDEX IF NOT EXISTS ix_{t}_dirty ON {t}(_dirty) WHERE _dirty=1")
        now = "strftime('%Y-%m-%d %H:%M:%f','now')"
        con.execute(f"""CREATE TRIGGER IF NOT EXISTS trg_{t}_i AFTER INSERT ON {t} WHEN bil_applying()=0
            BEGIN UPDATE {t} SET _upd={now}, _dirty=1 WHERE id=NEW.id; END""")
        con.execute(f"""CREATE TRIGGER IF NOT EXISTS trg_{t}_u AFTER UPDATE ON {t}
            WHEN bil_applying()=0 AND NEW._upd IS OLD._upd
            BEGIN UPDATE {t} SET _upd={now}, _dirty=1 WHERE id=NEW.id; END""")
        con.execute(f"""CREATE TRIGGER IF NOT EXISTS trg_{t}_d AFTER DELETE ON {t} WHEN bil_applying()=0
            BEGIN INSERT INTO _deleted(tbl,rid,at) VALUES('{t}', OLD.id, {now}); END""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_deleted_at ON _deleted(at)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_deleted_rcv ON _deleted(_rcv)")


def state_get(con, k, default=""):
    r = con.execute("SELECT v FROM _sync_state WHERE k=?", (k,)).fetchone()
    return r[0] if r else default


def state_set(con, k, v):
    con.execute("INSERT OR REPLACE INTO _sync_state(k,v) VALUES(?,?)", (k, str(v)))


# ---------------------------------------------------------------- تطبيق البيانات المستلمة
def apply_rows(con, tables, deleted, rcv=None):
    """يطبّق أسطرًا مستلمة: الأحدث (_upd) هو الذي يبقى."""
    con.applying = True
    n = 0
    try:
        for t, rows in tables.items():
            if t not in SYNC_TABLES or not rows:
                continue
            cols = {r[1] for r in con.execute(f"PRAGMA table_info({t})")}
            for row in rows:
                row = {k: v for k, v in row.items() if k in cols}
                if "id" not in row:
                    continue
                if rcv:
                    row["_rcv"] = rcv
                row["_dirty"] = 0
                cur = con.execute(f"SELECT _upd FROM {t} WHERE id=?", (row["id"],)).fetchone()
                if cur and cur[0] and row.get("_upd") and cur[0] >= row["_upd"]:
                    continue
                if t == "attendance":  # نفس العامل ونفس اليوم برقمين مختلفين: الأحدث يبقى
                    o = con.execute("SELECT id,_upd FROM attendance WHERE employee_id=? AND day=? AND id<>?",
                                    (row.get("employee_id"), row.get("day"), row["id"])).fetchone()
                    if o and o[1] and row.get("_upd") and o[1] > row["_upd"]:
                        continue
                    if o:
                        con.execute("DELETE FROM attendance WHERE id=?", (o[0],))
                keys = list(row)
                con.execute(f"INSERT OR REPLACE INTO {t}({','.join(keys)}) VALUES({','.join('?' * len(keys))})",
                            [row[k] for k in keys])
                n += 1
        for d in deleted or []:
            if d.get("tbl") in SYNC_TABLES:
                con.execute(f"DELETE FROM {d['tbl']} WHERE id=?", (d["rid"],))
                con.execute("INSERT INTO _deleted(tbl,rid,at,_rcv) VALUES(?,?,?,?)",
                            (d["tbl"], d["rid"], d.get("at"), rcv or "pulled"))
    finally:
        con.applying = False
    return n


def recompute_stock(con, branch_id=None):
    """الكمية = مجموع حركات المخزون (بيع، إدخال، إرجاع...) فلا تختلف بين الحاسوبين."""
    q = """INSERT OR IGNORE INTO stock(product_id,branch_id,qty)
           SELECT DISTINCT product_id, branch_id, 0 FROM stock_moves"""
    con.execute(q + (" WHERE branch_id=?" if branch_id else ""), (branch_id,) if branch_id else ())
    con.execute("""UPDATE stock SET qty=(SELECT COALESCE(SUM(m.qty),0) FROM stock_moves m
        WHERE m.product_id=stock.product_id AND m.branch_id=stock.branch_id)"""
                + (" WHERE branch_id=?" if branch_id else ""), (branch_id,) if branch_id else ())


def rows_since(con, t, since, where="", args=()):
    # نختار أولًا الأسطر التي تغيّرت (بالفهرس) ثم نصفّيها حسب الفرع: سريع حتى مع ملايين الأسطر
    q = (f"SELECT * FROM {t} WHERE id IN (SELECT id FROM {t} INDEXED BY ix_{t}_upd WHERE _upd > ? "
         f"UNION SELECT id FROM {t} INDEXED BY ix_{t}_rcv WHERE _rcv > ?)")
    a = [since, since]
    if where:
        q += f" AND ({where})"
        a += list(args)
    return [dict(r) for r in con.execute(q + " ORDER BY _upd LIMIT 5000", a)]


# ---------------------------------------------------------------- جهة المركزي
IMAGE_SETTINGS = {"stamp_img", "signature_img"}


OVERLAP = 10  # ثوانٍ: نعيد إرسال آخر لحظات حتى لا تضيع عملية وصلت من حاسوب آخر في نفس اللحظة


def central_pull(con, branch_id, since, img_ver=None):
    """ما يرسله المركزي للفرع: القوائم العامة + كل ما يخص هذا الفرع."""
    now = (datetime.utcnow() - timedelta(seconds=OVERLAP)).strftime("%Y-%m-%d %H:%M:%S.%f")[:23]
    out = {}
    for t in CATALOG:
        out[t] = rows_since(con, t, since)
    for t in BRANCH_OWNED:
        if t in PUSH_ONLY:
            continue
        out[t] = rows_since(con, t, since, "branch_id=?", (branch_id,))
    for t, w in VIA.items():
        out[t] = rows_since(con, t, since, w, (branch_id,))
    deleted = [dict(r) for r in con.execute(
        "SELECT tbl,rid,at FROM _deleted WHERE at > ? OR _rcv > ?", (since, since))]
    settings = {r[0]: r[1] for r in con.execute("SELECT key,value FROM settings") if r[0] not in LOCAL_SETTINGS}
    if img_ver is not None and img_ver == settings.get("img_ver"):
        for k in IMAGE_SETTINGS:  # الختم والإمضاء لا يُرسلان إلا إذا تغيّرا
            settings.pop(k, None)
    stock = [dict(r) for r in con.execute("SELECT product_id,branch_id,min_qty FROM stock WHERE branch_id=?",
                                          (branch_id,))]
    return {"now": now, "tables": out, "deleted": deleted, "settings": settings, "stock": stock}


# ---------------------------------------------------------------- سرعة التنقل
STAMP = [0]                 # يزيد كلما تغيّرت المعلومات (لتحديث الصفحات المفتوحة وحدها)
WAKE = threading.Event()    # يوقظ المزامنة فورًا بعد أي عملية في هذا الحاسوب
_last_hello = [0.0]


def bump():
    STAMP[0] += 1


def central_push(con, branch_id, payload):
    rcv = utcnow()
    n = apply_rows(con, payload.get("tables", {}), payload.get("deleted", []), rcv=rcv)
    if n:
        bump()
    recompute_stock(con, branch_id)
    con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                (f"sync_last_{branch_id}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    con.commit()
    return n


# ---------------------------------------------------------------- جهة الفرع
def node_collect(con):
    """كل ما سُجّل أو عُدّل في الفرع ولم يُرسل بعد (_dirty=1)."""
    tables = {}
    for t in SYNC_TABLES:
        rows = [dict(r) for r in con.execute(f"SELECT * FROM {t} INDEXED BY ix_{t}_dirty WHERE _dirty=1 ORDER BY _upd LIMIT 3000")]
        if rows:
            tables[t] = rows
    deleted = [dict(r) for r in con.execute("SELECT rowid AS _rowid, tbl,rid,at FROM _deleted WHERE _rcv IS NULL")]
    return tables, deleted


def mark_sent(con, tables, deleted):
    con.applying = True
    try:
        for t, rows in tables.items():
            for r in rows:
                con.execute(f"UPDATE {t} SET _dirty=0 WHERE id=? AND _upd IS ?", (r["id"], r["_upd"]))
        for d in deleted:
            con.execute("UPDATE _deleted SET _rcv=? WHERE rowid=?", (utcnow(), d["_rowid"]))
    finally:
        con.applying = False


def pending_count(con):
    return sum(con.execute(f"SELECT COUNT(*) FROM {t} WHERE _dirty=1").fetchone()[0] for t in SYNC_TABLES) + \
        con.execute("SELECT COUNT(*) FROM _deleted WHERE _rcv IS NULL").fetchone()[0]


class DeviceDisabled(Exception):
    pass


def _post(path, data, timeout=25):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urlreq.Request(NODE["central_url"] + path, data=body, method="POST",
                         headers={"Content-Type": "application/json", "X-Sync-Key": NODE.get("key", "")})
    try:
        with urlreq.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urlerr.HTTPError as e:
        if e.code == 423:  # المديرة أوقفت هذا الحاسوب
            raise DeviceDisabled()
        raise


APP_VERSION = "0"  # يضبطه app.py


def vtuple(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


def central_is_newer(con):
    return vtuple(state_get(con, "central_version", "0")) > vtuple(APP_VERSION)


def node_sync_once(connect):
    """يرسل ثم يستقبل. يعيد (نجح؟، رسالة)."""
    con = connect()
    try:
        # 0) نسخة البرنامج في الحاسوب المركزي (للتحديث التلقائي)
        if time.time() - _last_hello[0] > 60:  # مرة في الدقيقة تكفي
            hello = _post("/sync/hello", {"branch_id": NODE["branch_id"], "device": NODE.get("device"),
                                          "version": APP_VERSION}, timeout=15)
            state_set(con, "central_version", hello.get("version", "0"))
            con.commit()
            _last_hello[0] = time.time()
        # 1) إرسال ما سُجّل محليًا
        for _ in range(20):
            tables, deleted = node_collect(con)
            if not tables and not deleted:
                break
            res = _post("/sync/push", {"branch_id": NODE["branch_id"], "device": NODE.get("device"),
                                       "tables": tables, "deleted": deleted})
            if not res.get("ok"):
                raise RuntimeError(res.get("error", "رفض المركزي"))
            mark_sent(con, tables, deleted)
            con.commit()
            if sum(len(v) for v in tables.values()) < 3000:
                break
        # 2) استقبال ما تغيّر في المركزي
        #    إذا كان المركزي بنسخة أحدث ننتظر التحديث أولًا (قد تكون فيه أعمدة جديدة)
        for _ in range(0 if central_is_newer(con) else 20):
            since = state_get(con, "last_pull", "")
            iv = con.execute("SELECT value FROM settings WHERE key='img_ver'").fetchone()
            res = _post("/sync/pull", {"branch_id": NODE["branch_id"], "device": NODE.get("device"),
                                       "since": since, "img_ver": iv[0] if iv else ""})
            if not res.get("ok"):
                raise RuntimeError(res.get("error", "رفض المركزي"))
            applied = apply_rows(con, res["tables"], res["deleted"])
            if applied:
                bump()
            for k, v in res.get("settings", {}).items():
                con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, v))
            for s in res.get("stock", []):
                con.execute("INSERT OR IGNORE INTO stock(product_id,branch_id,qty) VALUES(?,?,0)",
                            (s["product_id"], s["branch_id"]))
                con.execute("UPDATE stock SET min_qty=? WHERE product_id=? AND branch_id=?",
                            (s["min_qty"], s["product_id"], s["branch_id"]))
            if applied:
                recompute_stock(con, NODE["branch_id"])
            got = sum(len(v) for v in res["tables"].values())
            # إذا كانت الدفعة كاملة (5000) نكمل من آخر وقت استلمناه
            if got and max(len(v) for v in res["tables"].values()) >= 5000:
                last = max(max((r.get("_upd") or "") for r in v) for v in res["tables"].values() if v)
                state_set(con, "last_pull", last)
                con.commit()
                continue
            state_set(con, "last_pull", res["now"])
            con.commit()
            break
        state_set(con, "last_ok", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        state_set(con, "last_error", "في انتظار تحديث البرنامج" if central_is_newer(con) else "")
        state_set(con, "disabled", "")
        con.commit()
        return True, "تمت المزامنة"
    except DeviceDisabled:
        state_set(con, "disabled", "1")
        state_set(con, "last_error", "هذا الحاسوب موقوف من طرف المديرة")
        con.commit()
        return False, "هذا الحاسوب موقوف من طرف المديرة"
    except Exception as e:
        try:
            state_set(con, "last_error", str(e)[:200])
            state_set(con, "last_try", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            con.commit()
        except Exception:
            pass
        return False, str(e)[:200]
    finally:
        con.close()


_lock = threading.Lock()


def sync_now(connect):
    with _lock:
        return node_sync_once(connect)


def node_loop(connect, every=3):
    """كل 3 ثوانٍ، وفورًا بعد أي عملية في هذا الحاسوب. عند انقطاع الاتصال ننتظر أكثر."""
    while True:
        ok = False
        try:
            ok, _ = sync_now(connect)
        except Exception as e:
            print("sync error:", e)
        WAKE.wait(every if ok else 15)
        WAKE.clear()
