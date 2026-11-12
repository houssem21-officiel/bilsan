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
               "client_notes", "client_photos", "perms", "audit", "cash_days", "expenses",
               "suppliers", "purchases", "purchase_items"]
# جداول أضيفت للمزامنة في النسخة 19.5 (المشتريات): تحتاج تحويل البيانات القديمة مرة واحدة
V2_TABLES = ["suppliers", "purchases", "purchase_items"]
# جداول عامة يرسلها المركزي كاملة للفرع
CATALOG = ["branches", "departments", "posts", "users", "services", "products", "clients", "client_notes", "perms",
           "suppliers"]
# جداول خاصة بفرع (فيها branch_id)
BRANCH_OWNED = ["appointments", "plans", "charges", "payments", "stock_moves", "employees", "visits", "courses", "client_photos", "audit", "cash_days", "expenses",
                "purchases"]
# جداول يرسلها الفرع للمركزي فقط (مصاريف المديرة وسجل العمليات لا تنزل إلى حاسوب الفرع)
PUSH_ONLY = {"audit", "expenses"}
# جداول تابعة عبر جدول آخر
VIA = {
    "sale_items": "payment_id IN (SELECT id FROM payments WHERE branch_id=?)",
    "attendance": "employee_id IN (SELECT id FROM employees WHERE branch_id=?)",
    "grants": "employee_id IN (SELECT id FROM employees WHERE branch_id=?)",
    "visit_items": "visit_id IN (SELECT id FROM visits WHERE branch_id=?)",
    "course_trainees": "course_id IN (SELECT id FROM courses WHERE branch_id=?)",
    "purchase_items": "purchase_id IN (SELECT id FROM purchases WHERE branch_id=?)",
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


_ID_LOCK = threading.Lock()
_ID_NEXT = {}


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
        """رقم جديد لا يتكرر حتى لو سجّل عاملان في نفس اللحظة (نحجز الأرقام في الذاكرة تحت قفل)."""
        b = NODE["slot"]
        hi, lo = -(b * SPAN) - 1, -((b + 1) * SPAN) + 1
        with _ID_LOCK:
            r = super().execute(f"SELECT MIN(id) FROM {table} WHERE id BETWEEN ? AND ?", (lo, hi)).fetchone()[0]
            cand = hi if r is None else r - 1
            if table in _ID_NEXT:
                cand = min(cand, _ID_NEXT[table])
            _ID_NEXT[table] = cand - 1
            return cand


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


def migrate_v2(con):
    """مرة واحدة: المشتريات والموردون أصبحوا يتزامنون.
    - في حاسوب الفرع: ما سُجّل محليًا يأخذ أرقامًا سالبة خاصة به ثم يُرسل للمركزي.
    - في الحاسوب المركزي: الموجود يُعلَّم ليُرسل للحواسيب."""
    if state_get(con, "mig_v2"):
        return
    if NODE:
        refs = {"suppliers": [("purchases", "supplier_id"), ("expenses", "supplier_id")],
                "purchases": [("purchase_items", "purchase_id"), ("expenses", "purchase_id")],
                "purchase_items": []}
        for t in V2_TABLES:
            for (old,) in con.execute(f"SELECT id FROM {t} WHERE id>0 ORDER BY id").fetchall():
                new = con.next_node_id(t)
                con.execute(f"UPDATE {t} SET id=? WHERE id=?", (new, old))
                for rt, col in refs[t]:
                    con.execute(f"UPDATE {rt} SET {col}=? WHERE {col}=?", (new, old))
            con.execute(f"UPDATE {t} SET _dirty=1 WHERE id<0")
    else:
        for t in V2_TABLES:
            con.execute(f"UPDATE {t} SET _rcv=? WHERE _rcv IS NULL", (utcnow(),))
    state_set(con, "mig_v2", "1")


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


COND = threading.Condition()


def bump():
    with COND:
        STAMP[0] += 1
        COND.notify_all()


def wait_change(old, timeout=25):
    """ينتظر حتى تتغيّر المعلومات (أو تنتهي المهلة). يعيد الرقم الحالي."""
    with COND:
        COND.wait_for(lambda: STAMP[0] != old, timeout)
        return STAMP[0]


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


# ---------------------------------------------------------------- الاتصال بالحاسوب المركزي (سريع)
# 1) نحفظ عنوان IP لاسم bilsan-central: في Windows البحث عن الاسم داخل الشبكة قد يأخذ عدة ثوانٍ في كل مرة.
# 2) نبقي الاتصال مفتوحًا بين العمليات بدل فتح اتصال جديد كل مرة.
import http.client  # noqa: E402
import socket  # noqa: E402
from urllib.parse import urlsplit  # noqa: E402

_net = {"ip": None, "ip_at": 0.0, "conn": None}
LAST_MS = [0]


def _resolve(host):
    if re.match(r"^[0-9.]+$", host) or host in ("localhost",):
        return host
    if _net["ip"] and time.time() - _net["ip_at"] < 600:
        return _net["ip"]
    try:
        ip = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
    except OSError:
        ip = None
    if not ip:
        raise urlerr.URLError(f"getaddrinfo failed: {host}")
    _net["ip"], _net["ip_at"] = ip, time.time()
    return ip


def _conn(fresh=False):
    u = urlsplit(NODE["central_url"])
    if fresh or not _net["conn"]:
        if _net["conn"]:
            try:
                _net["conn"].close()
            except Exception:
                pass
        if fresh:
            _net["ip"] = None  # ربما تغيّر عنوان حاسوب المديرة
        _net["conn"] = http.client.HTTPConnection(_resolve(u.hostname), u.port or 80, timeout=25)
        _net["host"] = u.netloc
        _net["base"] = (u.path or "").rstrip("/")
    return _net["conn"]


def _post(path, data, timeout=25):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    hdr = {"Content-Type": "application/json", "X-Sync-Key": NODE.get("key", ""), "Connection": "keep-alive"}
    t0 = time.time()
    for attempt in (0, 1):
        try:
            c = _conn(fresh=attempt == 1)
            c.timeout = timeout
            if c.sock:
                c.sock.settimeout(timeout)
            hdr["Host"] = _net["host"]
            c.request("POST", _net["base"] + path, body=body, headers=hdr)
            r = c.getresponse()
            raw = r.read()
            if r.status == 423:  # المديرة أوقفت هذا الحاسوب
                raise DeviceDisabled()
            if r.status >= 400:
                raise urlerr.HTTPError(path, r.status, r.reason, None, None)
            LAST_MS[0] = int((time.time() - t0) * 1000)
            return json.loads(raw.decode("utf-8"))
        except (DeviceDisabled, urlerr.HTTPError):
            raise
        except (OSError, http.client.HTTPException, urlerr.URLError):
            _net["conn"] = None
            if attempt == 1:
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
        if time.time() - _last_hello[0] > 20:  # كل 20 ثانية تكفي
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


def watch_central():
    """اتصال انتظار دائم مع الحاسوب المركزي: يرجع فور ما تتسجل معلومة جديدة هناك،
    فيستقبلها هذا الحاسوب في أقل من ثانية بدل الانتظار."""
    stamp = -1
    conn = None
    while True:
        try:
            if conn is None:
                u = urlsplit(NODE["central_url"])
                conn = http.client.HTTPConnection(_resolve(u.hostname), u.port or 80, timeout=40)
                host, base = u.netloc, (u.path or "").rstrip("/")
            body = json.dumps({"branch_id": NODE["branch_id"], "device": NODE.get("device"), "s": stamp}).encode()
            conn.request("POST", base + "/sync/wait", body=body, headers={
                "Content-Type": "application/json", "X-Sync-Key": NODE.get("key", ""), "Host": host,
                "Connection": "keep-alive"})
            r = conn.getresponse()
            raw = r.read()
            if r.status != 200:
                raise OSError(f"wait {r.status}")
            new = json.loads(raw.decode("utf-8")).get("s", stamp)
            if new != stamp:
                if stamp != -1:
                    WAKE.set()  # معلومة جديدة في المركزي: نستقبلها الآن
                stamp = new
        except Exception:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
            conn = None
            stamp = -1
            _net["ip"] = None  # ربما تغيّر عنوان حاسوب المديرة
            time.sleep(5)


def node_loop(connect, every=20):
    """فورًا بعد أي عملية هنا، وفورًا عند وصول جديد في المركزي (watch_central)،
    ومرة كل 20 ثانية احتياطًا. عند انقطاع الاتصال نعيد المحاولة كل 10 ثوانٍ."""
    threading.Thread(target=watch_central, daemon=True).start()
    while True:
        ok = False
        try:
            ok, _ = sync_now(connect)
        except Exception as e:
            print("sync error:", e)
        WAKE.wait(every if ok else 10)
        WAKE.clear()
