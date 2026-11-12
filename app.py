# -*- coding: utf-8 -*-
"""
برنامج تسيير مركز الطب البديل بيلسان
الخادم يعمل على الحاسوب المركزي، والفروع (سكيكدة، الحروش) تتصل به عبر المتصفح.
"""
import os, sys, csv, io, json, sqlite3, threading, time, base64
from datetime import datetime, timedelta, date
from functools import wraps
from urllib import request as urlreq

from flask import (Flask, g, request, redirect, url_for, session, flash,
                   render_template, abort, Response)
from jinja2 import DictLoader
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import sync
import catalog
import backup

import paths  # noqa: E402
BASE_DIR = paths.DATA_DIR  # مكان البيانات (قاعدة البيانات، السجل، الإعدادات)
DB_PATH = os.environ.get("BILSAN_DB", os.path.join(BASE_DIR, "bilsan.db"))

app = Flask(__name__, static_folder=os.path.join(paths.APP_DIR, "static"))
def _secret():
    """مفتاح الجلسات: يُنشأ مرة واحدة لكل حاسوب ويُحفظ مع البيانات."""
    if os.environ.get("BILSAN_SECRET"):
        return os.environ["BILSAN_SECRET"]
    p = os.path.join(BASE_DIR, "secret.key")
    if not os.path.exists(p):
        with open(p, "w") as f:
            f.write(secrets.token_hex(32))
    with open(p) as f:
        return f.read().strip()


app.secret_key = _secret()

ROLES = {"admin": "المدير (الحاسوب المركزي)", "reception": "الاستقبال",
         "laser": "الليزر", "beauty": "التجميل"}
DEPTS = {"reception": "الاستقبال", "laser": "الليزر", "beauty": "التجميل"}
SERVICE_KINDS = {"hijama": "حجامة", "herbs": "أعشاب", "course": "دورات",
                 "laser": "ليزر", "beauty": "تجميل", "other": "أخرى"}
PAY_KINDS = {"service": "خدمة", "product": "بيع منتجات", "course": "دورة", "other": "أخرى"}
METHODS = {"cash": "نقدًا", "card": "بطاقة", "ccp": "تحويل CCP / بريدي"}
ATT_STATUS = {"present": "حاضر", "half": "غياب نصف يوم", "late": "متأخر", "absent": "غائب يوم كامل", "justified": "غياب مبرر",
              "sick": "عطلة مرضية", "leave": "عطلة", "off": "يوم راحة"}
GRANT_KINDS = {"bonus": "منحة", "reward": "مكافأة", "perf": "منحة المردودية", "allowance": "علاوة",
               "advance": "تسبيق على الراتب", "other": "أخرى"}
VISIT_STATUS = {"waiting": "في الانتظار", "treating": "في العلاج", "done": "انتهى — ينتظر الدفع",
                "paid": "مدفوعة", "cancelled": "ملغاة"}
VISIT_TARGETS = {"director": "المديرة", "reception": "الاستقبال (حجامة...)", "laser": "الليزر", "beauty": "التجميل"}
CLIENT_FIELDS = ("birth_date", "gender", "address", "chronic", "allergies", "medications")
EXPENSE_CATS = ["كراء", "كهرباء وماء وغاز", "إنترنت وهاتف", "أجور العمال", "شراء سلع (منتجات)",
                "مواد ومستلزمات العلاج", "صيانة وإصلاح", "إشهار وتسويق", "نقل", "ضرائب ورسوم", "أخرى"]
PURCHASE_STATUS = {"ordered": "طلبية (لم تصل)", "received": "استُلمت", "cancelled": "ملغاة"}
COURSE_STATUS = {"open": "جارية", "finished": "منتهية", "cancelled": "ملغاة"}
TRAINEE_STATUS = {"enrolled": "مسجّل", "completed": "أكمل الدورة", "withdrawn": "انسحب"}
PLAN_STATUS = {"active": "جارية", "done": "منتهية", "cancelled": "ملغاة"}
APPT_STATUS = {"scheduled": "مبرمج", "done": "تم", "cancelled": "ملغى", "noshow": "لم يحضر"}

# ---------------------------------------------------------------- قاعدة البيانات
SCHEMA = """
CREATE TABLE IF NOT EXISTS branches(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS departments(id INTEGER PRIMARY KEY, branch_id INTEGER, kind TEXT,
    UNIQUE(branch_id, kind));
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, pw_hash TEXT,
    full_name TEXT, role TEXT, branch_id INTEGER, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT,
    notes TEXT, branch_id INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY, name TEXT, kind TEXT, dept TEXT,
    price REAL DEFAULT 0, branch_id INTEGER, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY, client_id INTEGER, branch_id INTEGER,
    dept TEXT, service_id INTEGER, start_at TEXT, notes TEXT, status TEXT DEFAULT 'scheduled',
    sms_sent_at TEXT, created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT, barcode TEXT, category TEXT,
    price REAL DEFAULT 0, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS stock(product_id INTEGER, branch_id INTEGER, qty REAL DEFAULT 0,
    PRIMARY KEY(product_id, branch_id));
CREATE TABLE IF NOT EXISTS stock_moves(id INTEGER PRIMARY KEY, product_id INTEGER, branch_id INTEGER,
    qty REAL, reason TEXT, user_id INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS charges(id INTEGER PRIMARY KEY, branch_id INTEGER, client_id INTEGER,
    dept TEXT, service_id INTEGER, appointment_id INTEGER, description TEXT, amount REAL,
    status TEXT DEFAULT 'pending', payment_id INTEGER, created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY, branch_id INTEGER, client_id INTEGER,
    amount REAL, method TEXT, kind TEXT, description TEXT, received_by INTEGER, created_at TEXT,
    cancelled INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY, payment_id INTEGER, product_id INTEGER,
    qty REAL, unit_price REAL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS employees(id INTEGER PRIMARY KEY, branch_id INTEGER, name TEXT NOT NULL,
    phone TEXT, job TEXT, hire_date TEXT, base_salary REAL DEFAULT 0, notes TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY, employee_id INTEGER, day TEXT, status TEXT,
    check_in TEXT, check_out TEXT, note TEXT, recorded_by INTEGER, UNIQUE(employee_id, day));
CREATE TABLE IF NOT EXISTS grants(id INTEGER PRIMARY KEY, employee_id INTEGER, day TEXT, kind TEXT,
    amount REAL, note TEXT, created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY, branch_id INTEGER, name TEXT NOT NULL, dept TEXT,
    active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS plans(id INTEGER PRIMARY KEY, client_id INTEGER, branch_id INTEGER, dept TEXT,
    service_id INTEGER, post_id INTEGER, title TEXT, total_price REAL DEFAULT 0, price_mode TEXT DEFAULT 'session',
    notes TEXT, status TEXT DEFAULT 'active', created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS visits(id INTEGER PRIMARY KEY, client_id INTEGER, branch_id INTEGER, target TEXT,
    request TEXT, status TEXT DEFAULT 'waiting', created_by INTEGER, created_at TEXT, started_at TEXT,
    done_at TEXT, done_by INTEGER);
CREATE TABLE IF NOT EXISTS visit_items(id INTEGER PRIMARY KEY, visit_id INTEGER, kind TEXT, service_id INTEGER,
    product_id INTEGER, description TEXT, qty REAL DEFAULT 1, unit_price REAL DEFAULT 0, stage TEXT,
    added_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY, branch_id INTEGER, name TEXT, price REAL DEFAULT 0,
    start_date TEXT, end_date TEXT, hours REAL, trainer TEXT, notes TEXT, status TEXT DEFAULT 'open',
    created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS course_trainees(id INTEGER PRIMARY KEY, course_id INTEGER, client_id INTEGER,
    price REAL DEFAULT 0, status TEXT DEFAULT 'enrolled', enrolled_at TEXT, completed_at TEXT,
    cert_title TEXT, cert_body TEXT, cert_footer TEXT, cert_printed_at TEXT, created_by INTEGER);
CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY, branch_id INTEGER, day TEXT, category TEXT,
    description TEXT, amount REAL, method TEXT, supplier_id INTEGER, purchase_id INTEGER, employee_id INTEGER,
    month TEXT, created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS client_notes(id INTEGER PRIMARY KEY, client_id INTEGER, branch_id INTEGER, visit_id INTEGER,
    note TEXT, created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS client_photos(id INTEGER PRIMARY KEY, client_id INTEGER, branch_id INTEGER, kind TEXT,
    note TEXT, data TEXT, created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY, name TEXT, phone TEXT, address TEXT, notes TEXT,
    active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY, supplier_id INTEGER, branch_id INTEGER, day TEXT,
    status TEXT DEFAULT 'ordered', notes TEXT, created_by INTEGER, created_at TEXT, received_at TEXT);
CREATE TABLE IF NOT EXISTS purchase_items(id INTEGER PRIMARY KEY, purchase_id INTEGER, product_id INTEGER,
    qty REAL, unit_cost REAL);
CREATE TABLE IF NOT EXISTS perms(id INTEGER PRIMARY KEY, branch_id INTEGER, role TEXT, perm TEXT, enabled INTEGER,
    UNIQUE(branch_id, role, perm));
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, branch_id INTEGER, user_id INTEGER, action TEXT,
    details TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS cash_days(id INTEGER PRIMARY KEY, branch_id INTEGER, day TEXT, role TEXT, counted REAL,
    expected REAL, note TEXT, closed_by INTEGER, closed_at TEXT, UNIQUE(branch_id, day, role));
CREATE TABLE IF NOT EXISTS sms_log(id INTEGER PRIMARY KEY, appointment_id INTEGER, phone TEXT,
    message TEXT, status TEXT, response TEXT, created_at TEXT);
"""

DEFAULT_SETTINGS = {
    "center_name": "مركز الطب البديل بيلسان",
    "currency": "دج",
    "sms_enabled": "0",
    "sms_url": "https://api.sms-gate.app/3rdparty/v1/message",
    "sms_user": "",
    "sms_pass": "",
    "sms_hours_before": "24",
    "sms_depts": "beauty",
    "sms_template": "مرحبا {name}، نذكركم بموعدكم في {center} - {branch} يوم {date} على الساعة {time}. للإلغاء اتصلوا بنا.",
    "sms_confirm": "0",
    "sms_confirm_template": "مرحبا {name}، تم تسجيل موعدكم في {center} - {branch} يوم {date} على الساعة {time}. شكرا لثقتكم.",
    "sms_birthday": "0",
    "sms_birthday_template": "{center} يتمنى لكم {name} عيد ميلاد سعيد وسنة مليئة بالصحة والعافية.",
    "last_birthday_run": "",
    "expiry_days": "30",
    "default_min_qty": "5",
    "manager_phone": "",
    "stock_sms_enabled": "0",
    "last_stock_sms": "",
    "work_days": "26",
    "deduct_absence": "1",
    "paid_statuses": "",
    "attendance_mode": "absences",
    "weekly_off": "4",
    "director_branch": "2",
    "backup_dir": "",
    "backup_dir2": "",
    "backup_every_hours": "6",
    "staff_can_edit_prices": "0",
    "cert_title": "شهادة تكوين",
    "cert_body": "يشهد {center} بأن {sayed} {name}، {mawlud} بتاريخ {birth_date}، قد {tabaa} بنجاح الدورة التكوينية «{course}» المنظمة من {start} إلى {end}، بحجم ساعي قدره {hours} ساعة، تحت إشراف {trainer}.",
    "cert_footer": "سُلّمت هذه الشهادة للمعني(ة) بطلب منه(ا) لاستعمالها في حدود ما يسمح به القانون.",
    "cert_signer": "مديرة المركز",
    "stamp_img": "",
    "signature_img": "",
    "img_ver": "0",
    "consent_title": "استمارة الموافقة المستنيرة على إجراء علاجي / تجميلي",
    "consent_body": "أنا الموقّع(ة) أدناه {name}، أصرّح بما يلي:\n- تلقيت شرحًا واضحًا عن الإجراء «{procedure}»: طريقته، والنتائج المتوقعة، والبدائل الممكنة، وأُتيحت لي فرصة طرح أسئلتي.\n- أُعلمت بالآثار الجانبية والمضاعفات المحتملة (مثل الاحمرار، التورم، الكدمات، الحساسية، أو تغيّر لون الجلد)، وأنها غالبًا مؤقتة.\n- صرّحت بكل أمراضي المزمنة وحساسيتي والأدوية التي أتناولها، وبحالة الحمل أو الرضاعة إن وُجدت، وأتحمل مسؤولية أي معلومة غير صحيحة أو ناقصة.\n- أفهم أن النتائج تختلف من شخص لآخر، وأنه لا يمكن ضمان نتيجة معينة، وقد يتطلب الأمر عدة جلسات.\n- ألتزم بتعليمات ما قبل الجلسة وما بعدها التي قُدّمت لي.\n- أوافق بإرادتي الحرة على إجراء «{procedure}» في {center}.\n- [  ] أوافق   [  ] لا أوافق على التقاط صور قبل وبعد لغرض متابعة العلاج فقط.",
}
PAY_TYPES = {"daily": "أجرة يومية", "monthly": "راتب شهري ثابت"}


INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_pay_day ON payments(substr(created_at,1,10))",
    "CREATE INDEX IF NOT EXISTS ix_pay_branch_day ON payments(branch_id, substr(created_at,1,10))",
    "CREATE INDEX IF NOT EXISTS ix_pay_client ON payments(client_id)",
    "CREATE INDEX IF NOT EXISTS ix_pay_enroll ON payments(enroll_id)",
    "CREATE INDEX IF NOT EXISTS ix_pay_user ON payments(received_by)",
    "CREATE INDEX IF NOT EXISTS ix_ap_day ON appointments(substr(start_at,1,10))",
    "CREATE INDEX IF NOT EXISTS ix_ap_branch_day ON appointments(branch_id, substr(start_at,1,10))",
    "CREATE INDEX IF NOT EXISTS ix_ap_client ON appointments(client_id)",
    "CREATE INDEX IF NOT EXISTS ix_ap_plan ON appointments(plan_id)",
    "CREATE INDEX IF NOT EXISTS ix_ap_post ON appointments(post_id, substr(start_at,1,10))",
    "CREATE INDEX IF NOT EXISTS ix_ap_sched ON appointments(status, start_at)",
    "CREATE INDEX IF NOT EXISTS ix_ch_status ON charges(status, branch_id)",
    "CREATE INDEX IF NOT EXISTS ix_ch_client ON charges(client_id)",
    "CREATE INDEX IF NOT EXISTS ix_ch_appt ON charges(appointment_id)",
    "CREATE INDEX IF NOT EXISTS ix_ch_visit ON charges(visit_id)",
    "CREATE INDEX IF NOT EXISTS ix_ch_pay ON charges(payment_id)",
    "CREATE INDEX IF NOT EXISTS ix_ch_debt ON charges(debt_of)",
    "CREATE INDEX IF NOT EXISTS ix_cl_name ON clients(name)",
    "CREATE INDEX IF NOT EXISTS ix_cl_phone ON clients(phone)",
    "CREATE INDEX IF NOT EXISTS ix_cl_day ON clients(substr(created_at,1,10))",
    "CREATE INDEX IF NOT EXISTS ix_cl_bday ON clients(substr(birth_date,6,5))",
    "CREATE INDEX IF NOT EXISTS ix_vi_status ON visits(status, target)",
    "CREATE INDEX IF NOT EXISTS ix_vi_day ON visits(substr(created_at,1,10))",
    "CREATE INDEX IF NOT EXISTS ix_vi_client ON visits(client_id)",
    "CREATE INDEX IF NOT EXISTS ix_vit_visit ON visit_items(visit_id)",
    "CREATE INDEX IF NOT EXISTS ix_si_pay ON sale_items(payment_id)",
    "CREATE INDEX IF NOT EXISTS ix_si_prod ON sale_items(product_id)",
    "CREATE INDEX IF NOT EXISTS ix_sm_prod ON stock_moves(product_id, branch_id)",
    "CREATE INDEX IF NOT EXISTS ix_att_emp ON attendance(employee_id, day)",
    "CREATE INDEX IF NOT EXISTS ix_gr_emp ON grants(employee_id)",
    "CREATE INDEX IF NOT EXISTS ix_ex_branch_day ON expenses(branch_id, day)",
    "CREATE INDEX IF NOT EXISTS ix_ex_purchase ON expenses(purchase_id)",
    "CREATE INDEX IF NOT EXISTS ix_ex_supplier ON expenses(supplier_id)",
    "CREATE INDEX IF NOT EXISTS ix_au_day ON audit(substr(created_at,1,10))",
    "CREATE INDEX IF NOT EXISTS ix_cn_client ON client_notes(client_id)",
    "CREATE INDEX IF NOT EXISTS ix_cp_client ON client_photos(client_id)",
    "CREATE INDEX IF NOT EXISTS ix_ct_course ON course_trainees(course_id)",
    "CREATE INDEX IF NOT EXISTS ix_sms_status ON sms_log(status)",
    "CREATE INDEX IF NOT EXISTS ix_pi_purchase ON purchase_items(purchase_id)",
    "CREATE INDEX IF NOT EXISTS ix_pl_client ON plans(client_id)",
]


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect():
    con = sqlite3.connect(DB_PATH, timeout=30, factory=sync.BilConn, check_same_thread=False)
    sync.setup_connection(con)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    return con


def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    con = connect()
    con.executescript(SCHEMA)
    def add_col(table, col, decl):
        if col not in [r[1] for r in con.execute(f"PRAGMA table_info({table})")]:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    add_col("branches", "address", "TEXT")
    add_col("branches", "phone", "TEXT")
    add_col("branches", "active", "INTEGER DEFAULT 1")
    add_col("stock", "min_qty", "REAL DEFAULT 0")
    add_col("products", "expiry", "TEXT")
    add_col("employees", "pay_type", "TEXT DEFAULT 'daily'")
    for col in ("birth_date", "birth_place", "address", "id_card", "ss_number", "marital_status",
                "blood_type", "emergency_contact"):
        add_col("employees", col, "TEXT")
    add_col("employees", "social_security", "INTEGER DEFAULT 0")
    add_col("employees", "post_id", "INTEGER")
    add_col("employees", "pay_day", "INTEGER")
    add_col("employees", "end_date", "TEXT")
    add_col("employees", "end_reason", "TEXT")
    add_col("appointments", "plan_id", "INTEGER")
    for col in ("birth_date", "gender", "address", "chronic", "allergies", "medications"):
        add_col("clients", col, "TEXT")
    add_col("charges", "visit_id", "INTEGER")
    add_col("payments", "enroll_id", "INTEGER")
    add_col("payments", "dept", "TEXT")
    add_col("charges", "discount", "REAL DEFAULT 0")
    add_col("services", "duration", "INTEGER DEFAULT 30")
    add_col("expenses", "from_cash", "INTEGER DEFAULT 0")
    add_col("expenses", "role", "TEXT")
    add_col("appointments", "confirm_sent_at", "TEXT")
    add_col("charges", "debt_of", "INTEGER")
    add_col("products", "cost_price", "REAL DEFAULT 0")
    add_col("sale_items", "unit_cost", "REAL")
    if "can_collect" not in [r[1] for r in con.execute("PRAGMA table_info(departments)")]:
        con.execute("ALTER TABLE departments ADD COLUMN can_collect INTEGER DEFAULT 0")
        # التجميل في فرع الحروش يحصّل المال في غرفته
        con.execute("UPDATE departments SET can_collect=1 WHERE branch_id=2 AND kind='beauty'")
    add_col("appointments", "session_no", "INTEGER")
    add_col("appointments", "price", "REAL")
    add_col("appointments", "paid", "INTEGER DEFAULT 0")
    add_col("appointments", "payment_id", "INTEGER")
    add_col("appointments", "post_id", "INTEGER")
    add_col("employees", "children", "INTEGER DEFAULT 0")
    add_col("employees", "daily_wage", "REAL DEFAULT 0")
    add_col("grants", "deduct_month", "TEXT")
    # الحواسيب: كل حاسوب = حساب بكلمة سر خاصة به
    add_col("users", "device", "INTEGER DEFAULT 0")
    add_col("users", "slot", "INTEGER")
    add_col("users", "last_seen", "TEXT")
    con.execute("CREATE TABLE IF NOT EXISTS pair_codes(code TEXT PRIMARY KEY, user_id INTEGER, expires TEXT)")
    for k, v in DEFAULT_SETTINGS.items():
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
    sync.install(con)
    # فهارس لتبقى السرعة جيدة حتى مع بيانات عشرات السنين
    for sql in INDEXES:
        con.execute(sql)
    if not sync.NODE and not con.execute("SELECT value FROM settings WHERE key='sync_key' AND value<>''").fetchone():
        con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('sync_key',?)", (secrets.token_hex(12),))
    if not sync.NODE and not con.execute("SELECT 1 FROM branches").fetchone():
        con.execute("INSERT INTO branches(id,name) VALUES(1,'فرع سكيكدة للطب البديل')")
        con.execute("INSERT INTO branches(id,name) VALUES(2,'فرع الحروش للطب البديل')")
        for b, kinds in ((1, ("reception", "laser", "beauty")), (2, ("reception", "beauty"))):
            for k in kinds:
                con.execute("INSERT INTO departments(branch_id,kind) VALUES(?,?)", (b, k))
        con.execute("UPDATE departments SET can_collect=1 WHERE branch_id=2 AND kind='beauty'")
        services = [
            ("حجامة", "hijama", "reception", 0, None),
            ("دورة تكوينية", "course", "reception", 0, 1),
            ("جلسة ليزر", "laser", "laser", 0, 1),
            ("خدمة تجميل", "beauty", "beauty", 0, None),
        ]
        for s in services:
            con.execute("INSERT INTO services(name,kind,dept,price,branch_id) VALUES(?,?,?,?,?)", s)
        con.execute("INSERT INTO users(username,pw_hash,full_name,role,branch_id) VALUES(?,?,?,?,NULL)",
                    ("admin", generate_password_hash("admin123"), "المدير", "admin"))
    if not sync.NODE:
        apply_seed(con)
    if not sync.NODE and not os.environ.get("BILSAN_NO_CATALOG") and \
            not con.execute("SELECT 1 FROM settings WHERE key='catalog_v1'").fetchone():
        catalog.apply_catalog(con)
        con.execute("INSERT INTO settings(key,value) VALUES('catalog_v1','1')")
    if not sync.NODE and not con.execute("SELECT 1 FROM posts").fetchone():
        names = {"reception": ["الاستقبال", "غرفة الحجامة"], "laser": ["غرفة الليزر"], "beauty": ["غرفة التجميل"]}
        for d in con.execute("SELECT * FROM departments ORDER BY branch_id, id").fetchall():
            for nm in names.get(d["kind"], []):
                con.execute("INSERT INTO posts(branch_id,name,dept) VALUES(?,?,?)", (d["branch_id"], nm, d["kind"]))
    con.commit()
    con.close()


def apply_seed(con):
    """seed.json (يأتي مع ملف تثبيت الحاسوب المركزي): مفتاح الربط والحواسيب بكلمات سرها الأولية.
    يُطبّق مرة واحدة ثم يُحذف الملف حتى لا تبقى كلمات السر مكتوبة على القرص."""
    p = os.path.join(BASE_DIR, "seed.json")
    if not os.path.exists(p):
        return
    try:
        with open(p, encoding="utf-8") as f:
            seed = json.load(f)
    except (OSError, ValueError):
        return
    if not con.execute("SELECT 1 FROM settings WHERE key='seed_v1'").fetchone():
        if seed.get("sync_key"):
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('sync_key',?)", (seed["sync_key"],))
        for d in seed.get("devices", []):
            if con.execute("SELECT 1 FROM users WHERE username=?", (d["username"],)).fetchone():
                continue
            con.execute("""INSERT INTO users(username,pw_hash,full_name,role,branch_id,device,slot)
                VALUES(?,?,?,?,?,1,?)""", (d["username"], generate_password_hash(str(d["password"])),
                                          d["full_name"], d["role"], d["branch_id"], d["slot"]))
        if seed.get("admin_password"):
            con.execute("UPDATE users SET pw_hash=? WHERE username='admin'",
                        (generate_password_hash(str(seed["admin_password"])),))
        con.execute("INSERT INTO settings(key,value) VALUES('seed_v1','1')")
        con.commit()
    try:
        os.remove(p)
    except OSError:
        pass


def setting(key):
    row = get_db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else DEFAULT_SETTINGS.get(key, "")


# ---------------------------------------------------------------- الصلاحيات
def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    if "user" not in g:
        g.user = get_db().execute("SELECT * FROM users WHERE id=? AND active=1", (uid,)).fetchone()
    return g.user


def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            u = current_user()
            if not u:
                return redirect(url_for("login", next=request.path))
            if roles and u["role"] not in roles:
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


def is_admin():
    u = current_user()
    return bool(u and u["role"] == "admin")


def scope_branch():
    """الفرع الذي يعمل فيه المستخدم. المدير يختار فرعًا أو يرى الكل (None)."""
    u = current_user()
    if u["role"] != "admin":
        return u["branch_id"]
    if "branch" in request.values:
        b = request.values.get("branch")
    else:
        b = str(session.get("view_branch") or "")
    return int(b) if b and b.isdigit() else None


def work_branch():
    """الفرع الذي تُسجَّل باسمه العملية (بيع، دفعة...)."""
    u = current_user()
    if u["branch_id"]:
        return u["branch_id"]
    b = request.values.get("branch") or session.get("view_branch")
    if b and str(b).isdigit():
        return int(b)
    r = get_db().execute("SELECT id FROM branches WHERE active=1 ORDER BY id LIMIT 1").fetchone()
    return r["id"] if r else 1


@app.route("/view-branch")
@login_required("admin")
def view_branch():
    b = request.args.get("b", "")
    session["view_branch"] = int(b) if b.isdigit() else None
    return redirect(request.referrer or url_for("dashboard"))


def branch_depts(branch_id):
    rows = get_db().execute("SELECT kind FROM departments WHERE branch_id=?", (branch_id,)).fetchall()
    return [r["kind"] for r in rows]


def price_locked(u=None):
    """الأسعار تُعدَّل من المديرة فقط: العمال يستعملون أسعار القائمة كما هي."""
    u = u or current_user()
    return bool(u) and u["role"] != "admin" and setting("staff_can_edit_prices") != "1"


def service_price(sid):
    r = get_db().execute("SELECT price FROM services WHERE id=?", (sid,)).fetchone() if sid else None
    return r["price"] if r else 0


# ---------------------------------------------------------------- الصلاحيات (لكل مكان: فرع × استقبال/ليزر/تجميل)
# (المفتاح، الاسم، أماكن مفعّلة افتراضيًا). "collect_dept" = الأقسام التي تحصّل في غرفتها
PERMS = [
    ("reception_visits", "استقبال الزبائن وإرسالهم للعلاج", ("reception",)),
    ("clients_edit", "تسجيل الزبائن وتعديل معلوماتهم", ("reception", "laser", "beauty")),
    ("appointments", "إضافة المواعيد وتعديلها وإلغاؤها", ("reception", "laser", "beauty")),
    ("plans", "خطط الحصص (مواعيد بعدة جلسات)", ("reception", "laser", "beauty")),
    ("calendar", "جدول الغرف", ("reception", "laser", "beauty")),
    ("collect", "تحصيل الأموال", ("reception", "collect_dept")),
    ("direct_payment", "الدفع المباشر", ("reception", "collect_dept")),
    ("debts", "الديون (تسجيل وتسديد)", ("reception", "collect_dept")),
    ("cash_close", "إغلاق الصندوق اليومي (عدّ النقود)", ("reception", "collect_dept")),
    ("pos", "بيع المنتجات", ("reception",)),
    ("courses", "الدورات والشهادات", ("reception",)),
    ("attendance", "حضور العمال", ("reception",)),
    ("stock_alerts", "تنبيهات المخزون", ("reception",)),
    ("purchases", "إدخال فاتورة شراء (استلام سلعة)", ()),
    ("expenses", "إخراج مبلغ من الصندوق (مصروف)", ()),
    ("medical", "الملف الطبي وصور قبل/بعد", ("laser", "beauty")),
    ("consent", "طباعة وثيقة الموافقة", ("reception", "laser", "beauty")),
]
PERM_LABELS = {k: v for k, v, _ in PERMS}
PLACES = {"reception": "الاستقبال", "laser": "غرفة الليزر", "beauty": "غرفة التجميل"}


def default_perm(branch_id, role, perm):
    d = next((x[2] for x in PERMS if x[0] == perm), ())
    if role in d:
        return True
    if "collect_dept" in d and role in ("laser", "beauty"):
        r = get_db().execute("SELECT can_collect FROM departments WHERE branch_id=? AND kind=?",
                             (branch_id, role)).fetchone()
        return bool(r and r["can_collect"])
    return False


def place_perms(branch_id, role):
    rows = {r["perm"]: bool(r["enabled"]) for r in get_db().execute(
        "SELECT perm, enabled FROM perms WHERE branch_id=? AND role=?", (branch_id, role))}
    return {k: rows[k] if k in rows else default_perm(branch_id, role, k) for k, _, _ in PERMS}


def has_perm(perm, u=None):
    """المديرة تملك كل شيء. العامل يملك ما فعّلته المديرة لمكان عمله."""
    u = u or current_user()
    if not u:
        return False
    if u["role"] == "admin":
        return True
    key = ("_perms", u["branch_id"], u["role"])
    cache = g.setdefault("perm_cache", {})
    if key not in cache:
        cache[key] = place_perms(u["branch_id"], u["role"])
    return cache[key].get(perm, False)


def perm_required(perm):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not current_user():
                return redirect(url_for("login", next=request.path))
            if not has_perm(perm):
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


def need(perm):
    if not has_perm(perm):
        abort(403)


def audit(action, details="", branch_id=None):
    """سجل العمليات: من فعل ماذا ومتى (تراه المديرة فقط)."""
    u = current_user()
    get_db().execute("INSERT INTO audit(branch_id,user_id,action,details,created_at) VALUES(?,?,?,?,?)",
                     (branch_id or (u["branch_id"] if u else None), u["id"] if u else None, action, str(details)[:500],
                      now_str()))


def can_collect(u=None):
    return has_perm("collect", u)


def collector_required(fn):
    return perm_required("collect")(fn)


def posts_for(branch_id, only_active=True):
    q = "SELECT * FROM posts WHERE branch_id=?" + (" AND active=1" if only_active else "") + " ORDER BY dept, name"
    return get_db().execute(q, (branch_id,)).fetchall()


def all_posts():
    return get_db().execute("""SELECT p.*, b.name AS branch FROM posts p JOIN branches b ON b.id=p.branch_id
        WHERE p.active=1 ORDER BY p.branch_id, p.name""").fetchall()


@app.context_processor
def inject():
    db = get_db()
    return dict(
        cu=current_user(), ROLES=ROLES, DEPTS=DEPTS, SERVICE_KINDS=SERVICE_KINDS,
        PAY_KINDS=PAY_KINDS, ATT_STATUS=ATT_STATUS, GRANT_KINDS=GRANT_KINDS, PAY_TYPES=PAY_TYPES, PLAN_STATUS=PLAN_STATUS, COURSE_STATUS=COURSE_STATUS, PURCHASE_STATUS=PURCHASE_STATUS, EXPENSE_CATS=EXPENSE_CATS, TRAINEE_STATUS=TRAINEE_STATUS, VISIT_STATUS=VISIT_STATUS, VISIT_TARGETS=VISIT_TARGETS,
        queue_count=queue_count() if current_user() else 0, posts_for=posts_for, METHODS=METHODS, APPT_STATUS=APPT_STATUS,
        center=setting("center_name"), cur=setting("currency"),
        all_branches=db.execute("SELECT * FROM branches WHERE active=1 ORDER BY id").fetchall(),
        today=date.today().isoformat(),
        view_branch=session.get("view_branch"),
        alerts_count=len(stock_alerts(scope_branch())) if current_user() else 0,
        branch_name=branch_name,
        NODE=sync.NODE, perm=has_perm, bk=backup_status() if (current_user() and current_user()["role"] == "admin") else None, PLACES=PLACES, locked=price_locked() if current_user() else False, can_collect=can_collect() if current_user() else False, node_status=node_status() if sync.NODE else None,
    )


def node_status():
    db = get_db()
    return dict(ok=sync.state_get(db, "last_ok"), err=sync.state_get(db, "last_error"),
                pending=sync.pending_count(db), first=not db.execute("SELECT 1 FROM users").fetchone())


def branch_name(bid):
    if not bid:
        return "كل الفروع"
    r = get_db().execute("SELECT name FROM branches WHERE id=?", (bid,)).fetchone()
    return r["name"] if r else ""


@app.template_filter("age")
def age_filter(bd):
    try:
        b = datetime.strptime(bd, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return ""
    t = date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


@app.template_filter("rid")
def rid_filter(v):
    """رقم الوصل/الزيارة للعرض: أرقام الفرع (السالبة) تظهر مثل 1-25."""
    try:
        v = int(v)
    except (TypeError, ValueError):
        return v
    if v >= 0:
        return v
    b, k = divmod(-v, sync.SPAN)
    return f"{b}-{k}" if k else v


@app.template_filter("money")
def money(v):
    try:
        txt = f"{float(v):,.2f}".replace(",", "\u00a0")
    except (TypeError, ValueError):
        txt = "0.00"
    return Markup(f'<bdi dir="ltr">{txt}</bdi>')


def fnum(v, default=0.0):
    try:
        return float(str(v).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- الدخول
@app.route("/login", methods=["GET", "POST"])
def login():
    db = get_db()
    dev = None
    if sync.NODE and sync.NODE.get("device"):
        dev = db.execute("SELECT * FROM users WHERE username=?", (sync.NODE["device"],)).fetchone()
    if request.method == "POST":
        if dev is not None or (sync.NODE and sync.NODE.get("device")):
            # حاسوب مثبّت لمكان واحد: كلمة سر الحاسوب فقط
            if sync.state_get(db, "disabled") == "1" or (dev and not dev["active"]):
                flash("هذا الحاسوب موقوف من طرف المديرة", "err")
                return render_template("login.html", dev=dev)
            u = dev
        else:
            u = db.execute("SELECT * FROM users WHERE username=? AND active=1",
                           (request.form.get("username", "").strip(),)).fetchone()
            if u and sync.NODE and (u["role"] == "admin" or u["branch_id"] != sync.NODE["branch_id"]):
                flash("هذا الحاسوب خاص بفرع واحد. المديرة تدخل من الحاسوب المركزي.", "err")
                return render_template("login.html", dev=dev)
        if not limiter_ok():
            flash("محاولات كثيرة، انتظر دقيقة", "err")
            return render_template("login.html", dev=dev)
        if u and check_password_hash(u["pw_hash"], request.form.get("password", "")):
            session.clear()
            session["uid"] = u["id"]
            nxt = request.args.get("next") or url_for("dashboard")
            if not nxt.startswith("/"):
                nxt = url_for("dashboard")
            return redirect(nxt)
        limiter_fail()
        flash("كلمة السر غير صحيحة" if dev is not None else "اسم المستخدم أو كلمة المرور غير صحيحة", "err")
    return render_template("login.html", dev=dev)


_fails = []


def limiter_fail():
    _fails.append(time.time())


def limiter_ok():
    """بعد 10 محاولات خاطئة في دقيقة يُمنع الدخول دقيقة."""
    now = time.time()
    _fails[:] = [t for t in _fails if now - t < 60]
    return len(_fails) < 10


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/password", methods=["GET", "POST"])
@login_required()
def change_password():
    if request.method == "POST":
        u = current_user()
        if not check_password_hash(u["pw_hash"], request.form.get("old", "")):
            flash("كلمة المرور الحالية غير صحيحة", "err")
        elif len(request.form.get("new", "")) < 4:
            flash("كلمة المرور الجديدة قصيرة جدًا", "err")
        else:
            db = get_db()
            db.execute("UPDATE users SET pw_hash=? WHERE id=?",
                       (generate_password_hash(request.form["new"]), u["id"]))
            db.commit()
            flash("تم تغيير كلمة المرور", "ok")
            return redirect(url_for("dashboard"))
    return render_template("password.html")


# ---------------------------------------------------------------- لوحة التحكم
@app.route("/")
@login_required()
def dashboard():
    db = get_db()
    u = current_user()
    today = date.today().isoformat()
    if u["role"] == "admin" and session.get("view_branch"):
        return redirect(url_for("branch_view", bid=session["view_branch"]))
    if u["role"] == "admin":
        per_branch = db.execute("""
            SELECT b.id, b.name,
              COALESCE((SELECT SUM(amount) FROM payments p WHERE p.branch_id=b.id AND p.cancelled=0
                        AND substr(p.created_at,1,10)=?),0) AS total,
              (SELECT COUNT(*) FROM payments p WHERE p.branch_id=b.id AND p.cancelled=0
                        AND substr(p.created_at,1,10)=?) AS cnt,
              (SELECT COUNT(*) FROM charges c WHERE c.branch_id=b.id AND c.status='pending') AS pending,
              (SELECT COUNT(*) FROM appointments a WHERE a.branch_id=b.id
                        AND substr(a.start_at,1,10)=? AND a.status='scheduled') AS appts
            FROM branches b WHERE b.active=1 ORDER BY b.id""", (today, today, today)).fetchall()
        grand = sum(r["total"] for r in per_branch)
        recent = db.execute("""SELECT p.*, b.name AS branch, c.name AS client, us.full_name AS by_name
            FROM payments p JOIN branches b ON b.id=p.branch_id LEFT JOIN clients c ON c.id=p.client_id
            LEFT JOIN users us ON us.id=p.received_by ORDER BY p.id DESC LIMIT 15""").fetchall()
        low = stock_alerts(None)[:10]
        return render_template("dash_admin.html", per_branch=per_branch, grand=grand, due=due_salaries(),
                               recent=recent, low=low)
    b = u["branch_id"]
    dept = u["role"] if u["role"] in ("laser", "beauty") else None
    q = """SELECT a.*, c.name AS client, c.phone, s.name AS service, s.price AS sprice, b.name AS branch,
           po.name AS room, pl.title AS plan_title, (SELECT COUNT(*) FROM appointments x WHERE x.plan_id=a.plan_id) AS plan_n FROM appointments a
           JOIN clients c ON c.id=a.client_id LEFT JOIN services s ON s.id=a.service_id
           JOIN branches b ON b.id=a.branch_id LEFT JOIN posts po ON po.id=a.post_id
           LEFT JOIN plans pl ON pl.id=a.plan_id
           WHERE a.branch_id=? AND substr(a.start_at,1,10)=?"""
    args = [b, today]
    if dept:
        q += " AND a.dept=?"
        args.append(dept)
    appts = db.execute(q + " ORDER BY a.start_at", args).fetchall()
    pending = db.execute("SELECT COUNT(*) n FROM charges WHERE branch_id=? AND status='pending'"
                         + (" AND dept=?" if dept else ""), (b, dept) if dept else (b,)).fetchone()["n"]
    my_total = db.execute("""SELECT COALESCE(SUM(amount),0) t FROM payments WHERE branch_id=?
        AND cancelled=0 AND substr(created_at,1,10)=?""", (b, today)).fetchone()["t"]
    return render_template("dash_staff.html", appts=appts, pending=pending, my_total=my_total,
                           low=stock_alerts(b)[:10])


# ---------------------------------------------------------------- الزبائن
@app.route("/clients", methods=["GET", "POST"])
@login_required()
def clients():
    db = get_db()
    u = current_user()
    if request.method == "POST":
        need("clients_edit")
        name = request.form.get("name", "").strip()
        if not name:
            flash("الاسم مطلوب", "err")
        else:
            br = u["branch_id"] or int(request.form.get("branch_id") or work_branch())
            extra = [request.form.get(k, "").strip() or None for k in CLIENT_FIELDS]
            cur = db.execute(f"INSERT INTO clients(name,phone,notes,branch_id,created_at,{','.join(CLIENT_FIELDS)}) "
                             f"VALUES(?,?,?,?,?{',?' * len(CLIENT_FIELDS)})",
                             [name, request.form.get("phone", "").strip(),
                              request.form.get("notes", "").strip(), br, now_str()] + extra)
            db.commit()
            flash("تمت إضافة الزبون", "ok")
            back = request.form.get("back")
            if back and back.startswith("/"):
                sep = "&" if "?" in back else "?"
                return redirect(f"{back}{sep}client_id={cur.lastrowid}")
            return redirect(url_for("client_view", cid=cur.lastrowid))
    s = request.args.get("q", "").strip()
    q = "SELECT c.*, b.name AS branch FROM clients c LEFT JOIN branches b ON b.id=c.branch_id"
    args = []
    if s:
        q += " WHERE c.name LIKE ? OR c.phone LIKE ?"
        args = [f"%{s}%", f"%{s}%"]
    rows = db.execute(q + " ORDER BY c.id DESC LIMIT 200", args).fetchall()
    return render_template("clients.html", rows=rows, s=s)


@app.route("/clients/<int(signed=True):cid>", methods=["GET", "POST"])
@login_required()
def client_view(cid):
    db = get_db()
    c = db.execute("SELECT * FROM clients WHERE id=?", (cid,)).fetchone() or abort(404)
    if request.method == "POST":
        need("clients_edit")
        db.execute("UPDATE clients SET name=?, phone=?, notes=?, " + ",".join(f"{k}=?" for k in CLIENT_FIELDS)
                   + " WHERE id=?",
                   [request.form.get("name", c["name"]).strip(), request.form.get("phone", "").strip(),
                    request.form.get("notes", "").strip()]
                   + [request.form.get(k, "").strip() or None for k in CLIENT_FIELDS] + [cid])
        db.commit()
        flash("تم الحفظ", "ok")
        return redirect(url_for("client_view", cid=cid))
    appts = db.execute("""SELECT a.*, s.name AS service, b.name AS branch FROM appointments a
        LEFT JOIN services s ON s.id=a.service_id JOIN branches b ON b.id=a.branch_id
        WHERE a.client_id=? ORDER BY a.start_at DESC""", (cid,)).fetchall()
    pays = db.execute("""SELECT p.*, b.name AS branch FROM payments p JOIN branches b ON b.id=p.branch_id
        WHERE p.client_id=? ORDER BY p.id DESC""", (cid,)).fetchall()
    cplans = db.execute("""SELECT pl.*, (SELECT COUNT(*) FROM appointments a WHERE a.plan_id=pl.id) n,
        (SELECT COUNT(*) FROM appointments a WHERE a.plan_id=pl.id AND a.status='done') done,
        (SELECT COUNT(*) FROM appointments a WHERE a.plan_id=pl.id AND a.paid=1) paid_n
        FROM plans pl WHERE pl.client_id=? ORDER BY pl.id DESC""", (cid,)).fetchall()
    cvisits = db.execute("""SELECT v.*, b.name AS branch,
        (SELECT COALESCE(SUM(qty*unit_price),0) FROM visit_items i WHERE i.visit_id=v.id) AS total
        FROM visits v JOIN branches b ON b.id=v.branch_id WHERE v.client_id=? ORDER BY v.id DESC LIMIT 50""",
                         (cid,)).fetchall()
    cdebts = db.execute("SELECT * FROM charges WHERE client_id=? AND status='debt' ORDER BY id", (cid,)).fetchall()
    notes = db.execute("""SELECT n.*, u.full_name AS by_name, b.name AS branch FROM client_notes n
        LEFT JOIN users u ON u.id=n.created_by LEFT JOIN branches b ON b.id=n.branch_id
        WHERE n.client_id=? ORDER BY n.id DESC""", (cid,)).fetchall() if has_perm("medical") else []
    photos = db.execute("SELECT id,kind,note,created_at FROM client_photos WHERE client_id=? ORDER BY id DESC",
                        (cid,)).fetchall() if can_see_photos() else []
    return render_template("client_view.html", c=c, appts=appts, pays=pays, cplans=cplans, cvisits=cvisits,
                           cdebts=cdebts, notes=notes, photos=photos, can_photos=can_see_photos(),
                           services=services_for(current_user()["branch_id"] or work_branch()))


@app.route("/api/clients")
@login_required()
def api_clients():
    s = request.args.get("q", "").strip()
    rows = get_db().execute("SELECT id,name,phone FROM clients WHERE name LIKE ? OR phone LIKE ? LIMIT 15",
                            (f"%{s}%", f"%{s}%")).fetchall()
    return {"items": [dict(r) for r in rows]}


# ---------------------------------------------------------------- المواعيد
def services_for(branch_id, dept=None):
    q = "SELECT * FROM services WHERE active=1 AND (branch_id IS NULL OR branch_id=?)"
    args = [branch_id]
    if dept:
        q += " AND dept=?"
        args.append(dept)
    return get_db().execute(q + " ORDER BY name", args).fetchall()


@app.route("/appointments", methods=["GET", "POST"])
@login_required()
def appointments():
    db = get_db()
    u = current_user()
    if request.method == "POST":
        need("appointments")
        br = u["branch_id"] or int(request.form.get("branch_id") or work_branch())
        dept = request.form.get("dept")
        if u["role"] in ("laser", "beauty"):
            dept = u["role"]
        if dept not in branch_depts(br):
            flash("هذا القسم غير موجود في هذا الفرع", "err")
            return redirect(url_for("appointments"))
        cid = request.form.get("client_id")
        d, t = request.form.get("date"), request.form.get("time")
        if not (cid and d and t):
            flash("اختر الزبون والتاريخ والساعة", "err")
            return redirect(url_for("appointments", date=d))
        post = request.form.get("post_id")
        if post and not request.form.get("force"):
            cf = room_conflicts(db, post, f"{d} {t}", appt_duration(request.form.get("service_id")))
            if cf:
                flash("الغرفة محجوزة في هذا الوقت: " + "، ".join(f"{x['start_at'][11:16]} {x['client']}" for x in cf)
                      + " — اختر وقتًا آخر أو أشّر على «حجز رغم التعارض».", "err")
                return redirect(url_for("appointments", date=d, client_id=cid))
        db.execute("""INSERT INTO appointments(client_id,branch_id,dept,service_id,start_at,notes,
            created_by,created_at,post_id) VALUES(?,?,?,?,?,?,?,?,?)""",
                   (int(cid), br, dept, request.form.get("service_id") or None, f"{d} {t}",
                    request.form.get("notes", "").strip(), u["id"], now_str(), request.form.get("post_id") or None))
        db.commit()
        flash("تم تسجيل الموعد", "ok")
        return redirect(url_for("appointments", date=d, branch=br if is_admin() else None))
    d = request.args.get("date") or date.today().isoformat()
    br = scope_branch()
    dept = request.args.get("dept") or (u["role"] if u["role"] in ("laser", "beauty") else "")
    q = """SELECT a.*, c.name AS client, c.phone, s.name AS service, s.price AS sprice, b.name AS branch,
           po.name AS room, pl.title AS plan_title, (SELECT COUNT(*) FROM appointments x WHERE x.plan_id=a.plan_id) AS plan_n
           FROM appointments a JOIN clients c ON c.id=a.client_id LEFT JOIN services s ON s.id=a.service_id
           JOIN branches b ON b.id=a.branch_id LEFT JOIN posts po ON po.id=a.post_id
           LEFT JOIN plans pl ON pl.id=a.plan_id WHERE substr(a.start_at,1,10)=?"""
    args = [d]
    if br:
        q += " AND a.branch_id=?"
        args.append(br)
    if dept:
        q += " AND a.dept=?"
        args.append(dept)
    rows = db.execute(q + " ORDER BY a.start_at", args).fetchall()
    form_branch = u["branch_id"] or br or work_branch()
    sel_client = None
    if request.args.get("client_id"):
        sel_client = db.execute("SELECT id,name,phone FROM clients WHERE id=?",
                                (request.args["client_id"],)).fetchone()
    return render_template("appointments.html", rows=rows, d=d, br=br, dept=dept,
                           depts=branch_depts(form_branch), form_branch=form_branch,
                           services=services_for(form_branch), sel_client=sel_client,
                           posts=posts_for(form_branch))


@app.route("/appointments/<int(signed=True):aid>/status", methods=["POST"])
@login_required()
def appt_status(aid):
    db = get_db()
    a = db.execute("SELECT * FROM appointments WHERE id=?", (aid,)).fetchone() or abort(404)
    u = current_user()
    if u["role"] != "admin" and a["branch_id"] != u["branch_id"]:
        abort(403)
    need("appointments")
    st = request.form.get("status")
    if st in APPT_STATUS and st != "done":
        audit("تغيير حالة موعد", f"موعد {a['start_at'] or ''} ← {APPT_STATUS[st]}", a["branch_id"])
        db.execute("UPDATE appointments SET status=? WHERE id=?", (st, aid))
        db.commit()
    return redirect(request.referrer or url_for("appointments"))


@app.route("/appointments/<int(signed=True):aid>/done", methods=["POST"])
@login_required()
def appt_done(aid):
    """إنهاء الموعد وإرسال المبلغ إلى الاستقبال للتحصيل."""
    db = get_db()
    a = db.execute("""SELECT a.*, s.name AS service FROM appointments a
        LEFT JOIN services s ON s.id=a.service_id WHERE a.id=?""", (aid,)).fetchone() or abort(404)
    u = current_user()
    if u["role"] != "admin" and a["branch_id"] != u["branch_id"]:
        abort(403)
    amount = fnum(request.form.get("amount"))
    if price_locked(u):
        amount = (a["price"] or 0) if a["plan_id"] else service_price(a["service_id"])
    if a["paid"]:
        amount = 0  # الحصة مدفوعة مسبقًا
    db.execute("UPDATE appointments SET status='done' WHERE id=?", (aid,))
    if a["plan_id"] and amount > 0 and db.execute(
            "SELECT 1 FROM charges WHERE appointment_id=? AND status='pending'", (aid,)).fetchone():
        amount = 0  # أُرسل مبلغها للاستقبال مسبقًا
    if amount > 0:
        chid = db.execute("""INSERT INTO charges(branch_id,client_id,dept,service_id,appointment_id,description,
            amount,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                   (a["branch_id"], a["client_id"], a["dept"], a["service_id"], aid,
                    (a["service"] or DEPTS.get(a["dept"])) + (f" — حصة {a['session_no']}" if a["plan_id"] else ""),
                    amount, u["id"], now_str())).lastrowid
        if request.form.get("collect") and can_collect(u):
            ch = db.execute("SELECT * FROM charges WHERE id=?", (chid,)).fetchone()
            pid = pay_charge(db, ch, request.form.get("method", "cash"), u)
            db.commit()
            flash("تم إنهاء الموعد وتحصيل المبلغ", "ok")
            return redirect(url_for("receipt", pid=pid))
        flash("تم إنهاء الموعد وإرسال المبلغ إلى الاستقبال للتحصيل", "ok")
    else:
        flash("تم إنهاء الموعد (بدون مبلغ)", "ok")
    db.commit()
    return redirect(request.referrer or url_for("appointments"))


# ---------------------------------------------------------------- مبالغ للتحصيل (من الأقسام إلى الاستقبال)
@app.route("/charges/new", methods=["GET", "POST"])
@login_required()
def charge_new():
    db = get_db()
    u = current_user()
    br = work_branch()
    if request.method == "POST":
        amount = fnum(request.form.get("amount"))
        if price_locked(u):
            q_ = max(1, fnum(request.form.get("qty"), 1))
            amount = service_price(request.form.get("service_id")) * q_
        dept = u["role"] if u["role"] in ("laser", "beauty") else request.form.get("dept", "reception")
        if amount <= 0:
            flash("أدخل مبلغًا صحيحًا", "err")
        else:
            sid = request.form.get("service_id") or None
            desc = request.form.get("description", "").strip()
            if not desc and sid:
                r = db.execute("SELECT name FROM services WHERE id=?", (sid,)).fetchone()
                desc = r["name"] if r else ""
            db.execute("""INSERT INTO charges(branch_id,client_id,dept,service_id,description,amount,
                created_by,created_at) VALUES(?,?,?,?,?,?,?,?)""",
                       (br, request.form.get("client_id") or None, dept, sid, desc or DEPTS.get(dept),
                        amount, u["id"], now_str()))
            db.commit()
            flash("تم إرسال المبلغ إلى الاستقبال", "ok")
            return redirect(url_for("dashboard"))
    dept = u["role"] if u["role"] in ("laser", "beauty") else None
    sel_client = None
    if request.args.get("client_id"):
        sel_client = db.execute("SELECT id,name,phone FROM clients WHERE id=?",
                                (request.args["client_id"],)).fetchone()
    return render_template("charge_new.html", services=services_for(br, dept), br=br,
                           depts=branch_depts(br), sel_client=sel_client)


def make_payment(db, branch_id, client_id, amount, method, kind, desc, uid, dept=None):
    if dept is None:
        r = current_user()
        dept = r["role"] if r and r["role"] in ("laser", "beauty") else "reception"
    cur = db.execute("""INSERT INTO payments(branch_id,client_id,amount,method,kind,description,
        received_by,created_at,dept) VALUES(?,?,?,?,?,?,?,?,?)""",
                     (branch_id, client_id, amount, method, kind, desc, uid, now_str(), dept))
    return cur.lastrowid


# ---------------------------------------------------------------- الاستقبال
@app.route("/reception")
@collector_required
def reception():
    db = get_db()
    br = scope_branch()
    q = """SELECT ch.*, c.name AS client, c.phone, b.name AS branch, us.full_name AS by_name
           FROM charges ch LEFT JOIN clients c ON c.id=ch.client_id JOIN branches b ON b.id=ch.branch_id
           LEFT JOIN users us ON us.id=ch.created_by WHERE ch.status='pending'"""
    args = []
    if current_user()["role"] in ("laser", "beauty"):
        q += " AND ch.dept=?"
        args.append(current_user()["role"])
    if br:
        q += " AND ch.branch_id=?"
        args.append(br)
    pending = db.execute(q + " ORDER BY ch.id", args).fetchall()
    today = date.today().isoformat()
    q2 = """SELECT p.*, c.name AS client FROM payments p LEFT JOIN clients c ON c.id=p.client_id
            WHERE substr(p.created_at,1,10)=?"""
    a2 = [today]
    if br:
        q2 += " AND p.branch_id=?"
        a2.append(br)
    if current_user()["role"] != "admin":
        # الفروع لا ترى الصندوق ولا المجاميع: فقط الوصولات التي سلّمها هذا الموظف اليوم لإعادة طباعتها
        q2 += " AND p.received_by=?"
        a2.append(current_user()["id"])
    todays = db.execute(q2 + " ORDER BY p.id DESC LIMIT 30", a2).fetchall()
    total = sum(p["amount"] for p in todays if not p["cancelled"])
    qv = """SELECT v.*, c.name AS client FROM visits v JOIN clients c ON c.id=v.client_id
            WHERE v.status IN ('waiting','treating')"""
    av = []
    if br:
        qv += " AND v.branch_id=?"
        av.append(br)
    open_visits = db.execute(qv + " ORDER BY v.id", av).fetchall()
    return render_template("reception.html", pending=pending, todays=todays, total=total, br=br,
                           open_visits=open_visits)


def pay_charge(db, ch, method, u, amount=None, discount=0.0):
    """تحصيل مبلغ معلّق: يُسجَّل في الصندوق ويُعلَّم الموعد/الزيارة مدفوعًا.
    إذا دفع الزبون أقل من المستحق يبقى الباقي دينًا عليه. التخفيض بإذن المديرة فقط."""
    due = round(ch["amount"] - discount, 2)
    amount = due if amount is None else round(min(max(amount, 0), due), 2)
    kind = "course" if ch["service_id"] and (db.execute(
        "SELECT kind FROM services WHERE id=?", (ch["service_id"],)).fetchone() or {"kind": ""})["kind"] == "course" else "service"
    pid = None
    if amount > 0:
        pid = make_payment(db, ch["branch_id"], ch["client_id"], amount, method or "cash", kind,
                           f"{DEPTS.get(ch['dept'], '')}: {ch['description'] or ''}", u["id"], dept=ch["dept"])
    rest = round(due - amount, 2)
    if rest > 0:
        db.execute("""INSERT INTO charges(branch_id,client_id,dept,service_id,description,amount,status,created_by,
            created_at,debt_of) VALUES(?,?,?,?,?,?,'debt',?,?,?)""",
                   (ch["branch_id"], ch["client_id"], ch["dept"], ch["service_id"],
                    ("باقي: " + (ch["description"] or ""))[:400], rest, u["id"], now_str(), ch["id"]))
    db.execute("UPDATE charges SET status=?, payment_id=?, discount=? WHERE id=?",
               ("paid" if ch["status"] == "pending" else "settled", pid, discount, ch["id"]))
    if ch["appointment_id"]:
        db.execute("UPDATE appointments SET paid=1, payment_id=? WHERE id=?", (pid, ch["appointment_id"]))
    if ch["visit_id"]:
        db.execute("UPDATE visits SET status='paid' WHERE id=?", (ch["visit_id"],))
    return pid


def check_charge_access(ch, u):
    if u["role"] == "admin":
        return
    if ch["branch_id"] != u["branch_id"]:
        abort(403)
    if u["role"] in ("laser", "beauty") and (ch["dept"] != u["role"] or not can_collect(u)):
        abort(403)


@app.route("/charges/<int(signed=True):chid>/pay", methods=["POST"])
@collector_required
def charge_pay(chid):
    db = get_db()
    ch = db.execute("SELECT * FROM charges WHERE id=? AND status='pending'", (chid,)).fetchone()
    if not ch:
        flash("هذا المبلغ تم تحصيله أو إلغاؤه", "err")
        return redirect(url_for("reception"))
    u = current_user()
    check_charge_access(ch, u)
    disc = 0.0 if price_locked(u) else min(max(fnum(request.form.get("discount")), 0), ch["amount"])
    amt = fnum(request.form.get("paid"), ch["amount"] - disc) if request.form.get("paid") not in (None, "") else None
    if amt is not None and amt < ch["amount"] - disc and not ch["client_id"]:
        flash("لتسجيل دين يجب أن يكون المبلغ مرتبطًا بزبون", "err")
        return redirect(request.referrer or url_for("reception"))
    pid = pay_charge(db, ch, request.form.get("method", "cash"), u, amt, disc)
    if disc or (amt is not None and amt < ch["amount"] - disc):
        audit("تحصيل بتخفيض/دين", f"{ch['description'] or ''}: المستحق {ch['amount']:g}، تخفيض {disc:g}، المدفوع {amt if amt is not None else ch['amount']-disc:g}", ch["branch_id"])
    db.commit()
    rest = round(ch["amount"] - disc - (amt if amt is not None else ch["amount"] - disc), 2)
    flash("تم التحصيل" + (f"، وبقي على الزبون دين {rest:g} {setting('currency')}" if rest > 0 else ""), "ok")
    return redirect(url_for("receipt", pid=pid) if pid else url_for("debts"))


@app.route("/debts", methods=["GET", "POST"])
@perm_required("debts")
def debts():
    """ديون الزبائن: ما بقي عليهم بعد دفع جزء من المبلغ."""
    db = get_db()
    u = current_user()
    if request.method == "POST":
        ch = db.execute("SELECT * FROM charges WHERE id=? AND status='debt'", (request.form.get("id"),)).fetchone()
        if not ch:
            flash("هذا الدين سُدّد مسبقًا", "err")
            return redirect(url_for("debts"))
        check_charge_access(ch, u)
        amt = fnum(request.form.get("paid"), ch["amount"])
        if amt <= 0:
            flash("أدخل المبلغ المسدَّد", "err")
            return redirect(url_for("debts"))
        pid = pay_charge(db, ch, request.form.get("method", "cash"), u, amt)
        db.commit()
        flash("تم تسجيل التسديد", "ok")
        return redirect(url_for("receipt", pid=pid))
    br = scope_branch()
    q = """SELECT ch.*, c.name AS client, c.phone, b.name AS branch FROM charges ch
        LEFT JOIN clients c ON c.id=ch.client_id JOIN branches b ON b.id=ch.branch_id WHERE ch.status='debt'"""
    args = []
    if br:
        q += " AND ch.branch_id=?"
        args.append(br)
    if u["role"] in ("laser", "beauty"):
        q += " AND ch.dept=?"
        args.append(u["role"])
    if request.args.get("client_id"):
        q += " AND ch.client_id=?"
        args.append(request.args["client_id"])
    rows = db.execute(q + " ORDER BY c.name, ch.id", args).fetchall()
    return render_template("debts.html", rows=rows, br=br, total=sum(r["amount"] for r in rows))


@app.route("/charges/<int(signed=True):chid>/cancel", methods=["POST"])
@collector_required
def charge_cancel(chid):
    db = get_db()
    ch = db.execute("SELECT * FROM charges WHERE id=?", (chid,)).fetchone() or abort(404)
    u = current_user()
    check_charge_access(ch, u)
    audit("إلغاء مبلغ معلّق", f"{ch['description'] or ''} — {ch['amount']:g}", ch["branch_id"])
    db.execute("UPDATE charges SET status='cancelled' WHERE id=? AND status='pending'", (chid,))
    db.commit()
    flash("تم إلغاء المبلغ", "ok")
    return redirect(url_for("reception"))


@app.route("/payment/new", methods=["GET", "POST"])
@perm_required("direct_payment")
def payment_new():
    """دفع مباشر في الاستقبال: حجامة، دورة، أو أي خدمة أخرى."""
    db = get_db()
    u = current_user()
    br = work_branch()
    if request.method == "POST":
        amount = fnum(request.form.get("amount"))
        if price_locked(u):
            amount = service_price(request.form.get("service_id")) * max(1, fnum(request.form.get("qty"), 1))
        if amount <= 0:
            flash("اختر الخدمة (إن كان سعرها 0 فالمديرة لم تحدده بعد)" if price_locked(u) else "أدخل مبلغًا صحيحًا", "err")
        else:
            sid = request.form.get("service_id")
            srv = db.execute("SELECT * FROM services WHERE id=?", (sid,)).fetchone() if sid else None
            kind = "course" if srv and srv["kind"] == "course" else ("service" if srv else "other")
            desc = request.form.get("description", "").strip() or (srv["name"] if srv else "دفعة")
            pid = make_payment(db, br, request.form.get("client_id") or None, amount,
                               request.form.get("method", "cash"), kind, desc, u["id"])
            db.commit()
            flash("تم تسجيل الدفعة", "ok")
            return redirect(url_for("receipt", pid=pid))
    sel_client = None
    if request.args.get("client_id"):
        sel_client = db.execute("SELECT id,name,phone FROM clients WHERE id=?",
                                (request.args["client_id"],)).fetchone()
    dept_ = u["role"] if u["role"] in ("laser", "beauty") else "reception"
    return render_template("payment_new.html", services=services_for(br, dept_), br=br,
                           sel_client=sel_client)


@app.route("/payments/<int(signed=True):pid>/cancel", methods=["POST"])
@login_required("admin")
def payment_cancel(pid):
    db = get_db()
    p = db.execute("SELECT * FROM payments WHERE id=? AND cancelled=0", (pid,)).fetchone()
    if p:
        audit("إلغاء وصل", f"وصل {rid_filter(pid)} — {p['amount']:g} — {p['description'] or ''}", p["branch_id"])
        db.execute("UPDATE payments SET cancelled=1 WHERE id=?", (pid,))
        for it in db.execute("SELECT * FROM sale_items WHERE payment_id=?", (pid,)).fetchall():
            move_stock(db, it["product_id"], p["branch_id"], it["qty"], f"إلغاء الوصل {pid}")
        db.execute("UPDATE charges SET status='pending', payment_id=NULL WHERE payment_id=?", (pid,))
        db.execute("UPDATE appointments SET paid=0, payment_id=NULL WHERE payment_id=?", (pid,))
        db.execute("""UPDATE visits SET status='done' WHERE status='paid' AND id IN
            (SELECT visit_id FROM charges WHERE payment_id IS NULL AND status='pending' AND visit_id IS NOT NULL)""")
        db.commit()
        flash("تم إلغاء الدفعة", "ok")
    return redirect(request.referrer or url_for("cashbox"))


@app.route("/receipt/<int(signed=True):pid>")
@login_required()
def receipt(pid):
    db = get_db()
    p = db.execute("""SELECT p.*, b.name AS branch, c.name AS client, c.phone, us.full_name AS by_name
        FROM payments p JOIN branches b ON b.id=p.branch_id LEFT JOIN clients c ON c.id=p.client_id
        LEFT JOIN users us ON us.id=p.received_by WHERE p.id=?""", (pid,)).fetchone() or abort(404)
    if current_user()["role"] != "admin" and p["branch_id"] != current_user()["branch_id"]:
        abort(403)
    items = db.execute("""SELECT si.*, pr.name FROM sale_items si JOIN products pr ON pr.id=si.product_id
        WHERE si.payment_id=?""", (pid,)).fetchall()
    vitems = db.execute("""SELECT i.* FROM visit_items i JOIN charges ch ON ch.visit_id=i.visit_id
        WHERE ch.payment_id=? ORDER BY i.id""", (pid,)).fetchall()
    rest = db.execute("""SELECT COALESCE(SUM(amount),0) FROM charges WHERE status='debt' AND debt_of IN
        (SELECT id FROM charges WHERE payment_id=?)""", (pid,)).fetchone()[0]
    return render_template("receipt.html", p=p, items=items, vitems=vitems, rest=rest)


# ---------------------------------------------------------------- نقطة البيع (منتجات)
def move_stock(db, product_id, branch_id, qty, reason, uid=None):
    db.execute("INSERT OR IGNORE INTO stock(product_id,branch_id,qty) VALUES(?,?,0)", (product_id, branch_id))
    db.execute("UPDATE stock SET qty=qty+? WHERE product_id=? AND branch_id=?", (qty, product_id, branch_id))
    db.execute("INSERT INTO stock_moves(product_id,branch_id,qty,reason,user_id,created_at) VALUES(?,?,?,?,?,?)",
               (product_id, branch_id, qty, reason, uid, now_str()))


@app.route("/pos", methods=["GET", "POST"])
@perm_required("pos")
def pos():
    db = get_db()
    u = current_user()
    br = work_branch()
    if request.method == "POST":
        try:
            cart = json.loads(request.form.get("cart") or "[]")
        except ValueError:
            cart = []
        lines, total = [], 0.0
        for it in cart:
            pr = db.execute("SELECT * FROM products WHERE id=? AND active=1", (it.get("id"),)).fetchone()
            qty = fnum(it.get("qty"))
            if pr and qty > 0:
                price = pr["price"] if price_locked(u) else fnum(it.get("price"), pr["price"])
                lines.append((pr, qty, price))
                total += qty * price
        if not lines:
            flash("السلة فارغة", "err")
            return redirect(url_for("pos", branch=br))
        for pr, qty, _ in lines:
            st = db.execute("SELECT qty FROM stock WHERE product_id=? AND branch_id=?", (pr["id"], br)).fetchone()
            if (st["qty"] if st else 0) < qty:
                flash(f"تنبيه: مخزون «{pr['name']}» غير كافٍ في هذا الفرع (تم البيع وأصبح المخزون سالبًا)", "err")
        desc = "، ".join(f"{pr['name']} ×{qty:g}" for pr, qty, _ in lines)
        pid = make_payment(db, br, request.form.get("client_id") or None, round(total, 2),
                           request.form.get("method", "cash"), "product", desc, u["id"])
        for pr, qty, price in lines:
            db.execute("INSERT INTO sale_items(payment_id,product_id,qty,unit_price,unit_cost) VALUES(?,?,?,?,?)",
                       (pid, pr["id"], qty, price, pr["cost_price"] or 0))
            move_stock(db, pr["id"], br, -qty, f"بيع - وصل {pid}", u["id"])
        db.commit()
        flash("تم البيع وتسجيل المبلغ في الصندوق المركزي", "ok")
        return redirect(url_for("receipt", pid=pid))
    prods = db.execute("""SELECT p.*, COALESCE(s.qty,0) AS qty FROM products p
        LEFT JOIN stock s ON s.product_id=p.id AND s.branch_id=? WHERE p.active=1
        ORDER BY p.category, p.name""", (br,)).fetchall()
    return render_template("pos.html", prods=[dict(p) for p in prods], br=br)


# ---------------------------------------------------------------- الصندوق المركزي
def cash_query(args):
    d1 = args.get("from") or date.today().isoformat()
    d2 = args.get("to") or d1
    q = """SELECT p.*, b.name AS branch, c.name AS client, us.full_name AS by_name FROM payments p
           JOIN branches b ON b.id=p.branch_id LEFT JOIN clients c ON c.id=p.client_id
           LEFT JOIN users us ON us.id=p.received_by WHERE substr(p.created_at,1,10) BETWEEN ? AND ?"""
    a = [d1, d2]
    br = scope_branch()
    if br:
        q += " AND p.branch_id=?"
        a.append(br)
    if args.get("kind") in PAY_KINDS:
        q += " AND p.kind=?"
        a.append(args["kind"])
    return d1, d2, br, get_db().execute(q + " ORDER BY p.id DESC", a).fetchall()


@app.route("/cashbox")
@login_required("admin")
def cashbox():
    d1, d2, br, rows = cash_query(request.args)
    valid = [r for r in rows if not r["cancelled"]]
    total = sum(r["amount"] for r in valid)
    by_branch, by_kind, by_method = {}, {}, {}
    for r in valid:
        by_branch[r["branch"]] = by_branch.get(r["branch"], 0) + r["amount"]
        by_kind[PAY_KINDS.get(r["kind"], r["kind"])] = by_kind.get(PAY_KINDS.get(r["kind"], r["kind"]), 0) + r["amount"]
        by_method[METHODS.get(r["method"], r["method"])] = by_method.get(METHODS.get(r["method"], r["method"]), 0) + r["amount"]
    return render_template("cashbox.html", rows=rows, total=total, d1=d1, d2=d2, br=br,
                           kind=request.args.get("kind", ""), by_branch=by_branch,
                           by_kind=by_kind, by_method=by_method)


@app.route("/cashbox.csv")
@login_required("admin")
def cashbox_csv():
    d1, d2, br, rows = cash_query(request.args)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["رقم الوصل", "التاريخ", "الفرع", "الزبون", "النوع", "البيان", "طريقة الدفع", "المبلغ", "استلمه", "ملغى"])
    for r in rows:
        w.writerow([r["id"], r["created_at"], r["branch"], r["client"] or "", PAY_KINDS.get(r["kind"], r["kind"]),
                    r["description"], METHODS.get(r["method"], r["method"]), r["amount"], r["by_name"] or "",
                    "نعم" if r["cancelled"] else ""])
    return Response("﻿" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=cashbox_{d1}_{d2}.csv"})


# ---------------------------------------------------------------- المنتجات والمخزون
def active_branches():
    return get_db().execute("SELECT * FROM branches WHERE active=1 ORDER BY id").fetchall()


def set_min(db, product_id, branch_id, min_qty):
    db.execute("INSERT OR IGNORE INTO stock(product_id,branch_id,qty) VALUES(?,?,0)", (product_id, branch_id))
    db.execute("UPDATE stock SET min_qty=? WHERE product_id=? AND branch_id=?", (min_qty, product_id, branch_id))


def stock_alerts(branch_id=None):
    """المنتجات التي وصلت حد التنبيه أو اقترب تاريخ انتهاء صلاحيتها."""
    db = get_db()
    days = int(fnum(setting("expiry_days"), 30))
    limit = (date.today() + timedelta(days=days)).isoformat()
    q = """SELECT p.id AS product_id, p.name, p.category, p.price, p.expiry, b.id AS branch_id, b.name AS branch,
              COALESCE(s.qty,0) AS qty, COALESCE(s.min_qty,0) AS min_qty
           FROM products p JOIN branches b ON b.active=1
           LEFT JOIN stock s ON s.product_id=p.id AND s.branch_id=b.id
           WHERE p.active=1 AND s.product_id IS NOT NULL
             AND ((COALESCE(s.min_qty,0)>0 AND COALESCE(s.qty,0)<=s.min_qty)
                  OR (p.expiry IS NOT NULL AND p.expiry<>'' AND p.expiry<=? AND COALESCE(s.qty,0)>0))"""
    args = [limit]
    if branch_id:
        q += " AND b.id=?"
        args.append(branch_id)
    rows = []
    for r in db.execute(q + " ORDER BY (COALESCE(s.qty,0)-COALESCE(s.min_qty,0)), p.name", args).fetchall():
        d = dict(r)
        d["low"] = d["min_qty"] > 0 and d["qty"] <= d["min_qty"]
        d["out"] = d["qty"] <= 0
        d["expiring"] = bool(d["expiry"]) and d["expiry"] <= limit
        d["expired"] = bool(d["expiry"]) and d["expiry"] < date.today().isoformat()
        d["suggest"] = max(0, d["min_qty"] * 2 - d["qty"]) if d["low"] else 0
        rows.append(d)
    return rows


@app.route("/products", methods=["GET", "POST"])
@login_required("admin")
def products():
    db = get_db()
    u = current_user()
    branches = active_branches()
    if request.method == "POST":
        pid = request.form.get("id")
        vals = (request.form.get("name", "").strip(), request.form.get("barcode", "").strip(),
                request.form.get("category", "").strip(), fnum(request.form.get("price")),
                request.form.get("expiry") or None,
                1 if request.form.get("active", "1") == "1" else 0, fnum(request.form.get("cost_price")))
        if not vals[0]:
            flash("اسم المنتج مطلوب", "err")
            return redirect(url_for("products"))
        if pid:
            old = db.execute("SELECT price FROM products WHERE id=?", (pid,)).fetchone()
            if old and old["price"] != vals[3]:
                audit("تغيير سعر منتج", f"{vals[0]}: {old['price']:g} ← {vals[3]:g}")
            db.execute("UPDATE products SET name=?,barcode=?,category=?,price=?,expiry=?,active=?,cost_price=? WHERE id=?",
                       vals + (pid,))
            flash("تم تعديل المنتج", "ok")
        else:
            pid = db.execute("INSERT INTO products(name,barcode,category,price,expiry,active,cost_price) VALUES(?,?,?,?,?,?,?)",
                             vals).lastrowid
            for b in branches:
                q = fnum(request.form.get(f"qty_{b['id']}"))
                if q:
                    move_stock(db, pid, b["id"], q, "مخزون أولي", u["id"])
            flash("تمت إضافة المنتج", "ok")
        for b in branches:
            m = request.form.get(f"min_{b['id']}")
            if m is not None and m != "":
                set_min(db, pid, b["id"], fnum(m))
        db.commit()
        return redirect(url_for("products"))
    br = scope_branch()
    show = [b for b in branches if not br or b["id"] == br]
    q = request.args.get("q", "").strip()
    sql = "SELECT * FROM products"
    args = []
    if q:
        sql += " WHERE name LIKE ? OR category LIKE ? OR barcode=?"
        args = [f"%{q}%", f"%{q}%", q]
    rows = db.execute(sql + " ORDER BY active DESC, category, name", args).fetchall()
    stock = {(r["product_id"], r["branch_id"]): r for r in db.execute("SELECT * FROM stock")}
    edit = db.execute("SELECT * FROM products WHERE id=?", (request.args.get("edit"),)).fetchone() \
        if request.args.get("edit") else None
    soon = (date.today() + timedelta(days=int(fnum(setting("expiry_days"), 30)))).isoformat()
    return render_template("products.html", rows=rows, branches=branches, show=show, stock=stock, edit=edit,
                           br=br, q=q, soon=soon, default_min=setting("default_min_qty"))


@app.route("/products/<int(signed=True):pid>/stock", methods=["POST"])
@login_required("admin")
def product_stock(pid):
    db = get_db()
    bid = int(request.form["branch_id"])
    q = fnum(request.form.get("qty"))
    if q:
        audit("تعديل مخزون", f"منتج {pid}: {q:+g} — {branch_name(bid)}", bid)
        move_stock(db, pid, bid, q,
                   request.form.get("reason") or ("إدخال سلعة" if q > 0 else "إخراج / تلف"), current_user()["id"])
        flash("تم تحديث المخزون", "ok")
    if request.form.get("min_qty", "") != "":
        set_min(db, pid, bid, fnum(request.form.get("min_qty")))
        flash("تم تحديث حد التنبيه", "ok")
    db.commit()
    nxt = request.form.get("next")
    return redirect(nxt if nxt and nxt.startswith("/") else url_for("products"))


@app.route("/products/template.csv")
@login_required("admin")
def products_template():
    head = ["الاسم", "الفئة", "السعر", "الباركود", "تاريخ انتهاء الصلاحية (YYYY-MM-DD)"]
    for b in active_branches():
        head += [f"الكمية - {b['name']}", f"حد التنبيه - {b['name']}"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(head)
    db = get_db()
    st = {(r["product_id"], r["branch_id"]): r for r in db.execute("SELECT * FROM stock")}
    for p in db.execute("SELECT * FROM products WHERE active=1 ORDER BY category, name"):
        row = [p["name"], p["category"] or "", f"{p['price']:g}", p["barcode"] or "", p["expiry"] or ""]
        for b in active_branches():
            x = st.get((p["id"], b["id"]))
            row += ["", f"{x['min_qty']:g}" if x and x["min_qty"] else ""]
        w.writerow(row)
    return Response("\ufeff" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=products_list.csv"})


@app.route("/products/import", methods=["POST"])
@login_required("admin")
def products_import():
    """استيراد منتجات من CSV: الاسم، الفئة، السعر، الباركود، تاريخ الانتهاء، ثم لكل فرع: الكمية وحد التنبيه"""
    db = get_db()
    f = request.files.get("file")
    if not f:
        flash("اختر ملفًا", "err")
        return redirect(url_for("products"))
    text = f.read().decode("utf-8-sig", errors="replace")
    branches = active_branches()
    dmin = fnum(setting("default_min_qty"))
    n = 0
    for i, row in enumerate(csv.reader(io.StringIO(text))):
        if not row or not row[0].strip() or (i == 0 and row[0].strip() == "الاسم"):
            continue
        row += [""] * (5 + 2 * len(branches))
        exp = row[4].strip().replace("/", "-") or None
        if exp:
            try:
                exp = datetime.strptime(exp, "%Y-%m-%d").date().isoformat()
            except ValueError:
                try:
                    exp = datetime.strptime(exp, "%d-%m-%Y").date().isoformat()
                except ValueError:
                    exp = None
        ex = db.execute("SELECT id FROM products WHERE name=?", (row[0].strip(),)).fetchone()
        if ex:  # منتج موجود: تحديث السعر والفئة، والكمية تُضاف للمخزون
            pid = ex["id"]
            db.execute("UPDATE products SET category=COALESCE(NULLIF(?,''),category), price=?, "
                       "barcode=COALESCE(NULLIF(?,''),barcode), expiry=COALESCE(?,expiry) WHERE id=?",
                       (row[1].strip(), fnum(row[2]), row[3].strip(), exp, pid))
        else:
            pid = db.execute("INSERT INTO products(name,category,price,barcode,expiry) VALUES(?,?,?,?,?)",
                             (row[0].strip(), row[1].strip(), fnum(row[2]), row[3].strip(), exp)).lastrowid
        for k, b in enumerate(branches):
            qty, mn = row[5 + 2 * k], row[6 + 2 * k]
            if not fnum(qty) and not mn.strip():
                continue  # المنتج غير موجود في هذا الفرع
            if fnum(qty):
                move_stock(db, pid, b["id"], fnum(qty), "استيراد", current_user()["id"])
            set_min(db, pid, b["id"], fnum(mn) if mn.strip() else dmin)
        n += 1
    db.commit()
    flash(f"تم استيراد {n} منتج", "ok")
    return redirect(url_for("products"))


@app.route("/stock-alerts")
@perm_required("stock_alerts")
def stock_alerts_page():
    br = scope_branch()
    rows = stock_alerts(br)
    kind = request.args.get("kind", "")
    if kind == "low":
        rows = [r for r in rows if r["low"]]
    elif kind == "expiry":
        rows = [r for r in rows if r["expiring"]]
    return render_template("stock_alerts.html", rows=rows, br=br, kind=kind,
                           now=datetime.now().strftime("%Y-%m-%d %H:%M"))



# ---------------------------------------------------------------- العمال، الحضور، المنح
def month_bounds(m):
    try:
        d1 = datetime.strptime(m + "-01", "%Y-%m-%d").date()
    except (TypeError, ValueError):
        d1 = date.today().replace(day=1)
    d2 = (d1.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return d1.strftime("%Y-%m"), d1.isoformat(), d2.isoformat()


def check_emp_access(e):
    u = current_user()
    if u["role"] != "admin" and e["branch_id"] != u["branch_id"]:
        abort(403)


def day_value(status, paid):
    """قيمة اليوم في حساب الأجرة: حاضر/متأخر = 1، نصف يوم = 0.5، العطل المدفوعة = 1، غير ذلك 0."""
    if status in ("present", "late"):
        return 1.0
    if status == "half":
        return 0.5
    return 1.0 if status in paid else 0.0


def emp_pay_day(e):
    """يوم استلام الأجرة: ما حددته المديرة، وإلا يوم بداية العمل (1 إلى 28)، وإلا أول الشهر."""
    if e["pay_day"]:
        return int(e["pay_day"])
    if e["hire_date"]:
        try:
            return min(28, int(e["hire_date"][8:10]))
        except ValueError:
            pass
    return 1


def emp_period(e, mm):
    """فترة أجرة العامل التي تبدأ في الشهر mm: من يوم أجرته إلى اليوم الذي قبله في الشهر التالي.
    مثال: دخل يوم 15 ← فترته من 15 نوفمبر إلى 14 ديسمبر، ويقبض أجرته يوم 15 ديسمبر."""
    y, m = int(mm[:4]), int(mm[5:7])
    p = emp_pay_day(e)
    start = date(y, m, p)
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    due = date(ny, nm, p)
    end = due - timedelta(days=1)
    return start.isoformat(), end.isoformat(), due.isoformat()


def current_period_month(e, day=None):
    """الشهر الذي تبدأ فيه فترة الأجرة الحالية للعامل."""
    day = day or date.today()
    p = emp_pay_day(e)
    if day.day >= p:
        return day.strftime("%Y-%m")
    y, m = (day.year - 1, 12) if day.month == 1 else (day.year, day.month - 1)
    return f"{y:04d}-{m:02d}"


def work_dates(e, d1, d2):
    """أيام العمل للعامل في الفترة: من بداية الشهر (أو تاريخ توظيفه) إلى آخره (أو اليوم)، دون أيام الراحة."""
    off = {int(x) for x in (setting("weekly_off") or "").split(",") if x.strip().isdigit()}
    start = datetime.strptime(d1, "%Y-%m-%d").date()
    end = min(datetime.strptime(d2, "%Y-%m-%d").date(), date.today())
    if e["hire_date"]:
        try:
            start = max(start, datetime.strptime(e["hire_date"][:10], "%Y-%m-%d").date())
        except ValueError:
            pass
    if e["end_date"]:
        try:
            end = min(end, datetime.strptime(e["end_date"][:10], "%Y-%m-%d").date())
        except ValueError:
            pass
    out, d = [], start
    while d <= end:
        if d.weekday() not in off:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out, off


def month_summary(branch_id, m, emp_id=None, d2_override=None):
    """ملخص الشهر لكل عامل: الأيام، الأجرة، المنح، التسبيقات، الصافي.

    الطريقة الافتراضية (attendance_mode=absences): العامل حاضر تلقائيًا كل أيام العمل،
    والمديرة/الاستقبال يسجّلان فقط الغياب (يوم كامل أو نصف يوم)، والأجرة تُحسب وحدها."""
    db = get_db()
    mm, d1, d2 = month_bounds(m)
    q = """SELECT e.*, b.name AS branch, po.name AS post FROM employees e JOIN branches b ON b.id=e.branch_id
           LEFT JOIN posts po ON po.id=e.post_id WHERE 1=1"""
    args = []
    if emp_id:
        q += " AND e.id=?"
        args.append(emp_id)
    else:  # العمال الحاليون + من غادر خلال هذه الفترة فقط
        q += " AND (e.active=1 OR (e.end_date IS NOT NULL AND e.end_date >= ?))"
        args.append(d1)
    if branch_id:
        q += " AND e.branch_id=?"
        args.append(branch_id)
    emps = db.execute(q + " ORDER BY e.branch_id, e.name", args).fetchall()
    wd = fnum(setting("work_days"), 26) or 26
    end_override = d2_override
    deduct = setting("deduct_absence") == "1"
    paid = [x for x in setting("paid_statuses").split(",") if x]
    auto = (setting("attendance_mode") or "absences") == "absences"
    out = []
    for e in emps:
        d1, d2, due = emp_period(e, mm)
        if end_override:
            d2 = end_override
        cnt = {k: 0 for k in ATT_STATUS}
        recs = db.execute("SELECT day, status FROM attendance WHERE employee_id=? AND day BETWEEN ? AND ?",
                          (e["id"], d1, d2)).fetchall()
        for r in recs:
            if r["status"] in cnt:
                cnt[r["status"]] += 1
        wdates, off = work_dates(e, d1, d2)
        lost = extra = 0.0
        if auto:
            wset = set(wdates)
            for r in recs:
                st = r["status"]
                if r["day"] in wset:  # يوم عمل: نخصم الغياب فقط
                    if st == "absent":
                        lost += 1
                    elif st == "half":
                        lost += 0.5
                    elif st in ("justified", "sick", "leave", "off") and st not in paid:
                        lost += 1
                elif r["day"] <= date.today().isoformat():  # عمل في يوم الراحة: يُضاف
                    if st in ("present", "late"):
                        extra += 1
                    elif st == "half":
                        extra += 0.5
            days = max(0.0, len(wdates) - lost + extra)
        else:
            days = sum(day_value(r["status"], paid) for r in recs)
        grants = db.execute("""SELECT * FROM grants WHERE employee_id=? AND kind<>'advance'
            AND day BETWEEN ? AND ? ORDER BY day""", (e["id"], d1, d2)).fetchall()
        advances = db.execute("""SELECT * FROM grants WHERE employee_id=? AND kind='advance'
            AND COALESCE(NULLIF(deduct_month,''), substr(day,1,7))""" + (">=?" if end_override else "=?") + " ORDER BY day",
                              (e["id"], mm)).fetchall()
        plus = sum(g["amount"] for g in grants)
        adv = sum(g["amount"] for g in advances)
        ptype = e["pay_type"] or "daily"
        if ptype == "daily":
            rate = e["daily_wage"] or 0
            gross = round(days * rate, 2)
            ded = round(lost * rate, 2) if auto else 0
        else:
            rate = round((e["base_salary"] or 0) / wd, 2)
            ded = 0
            if deduct and e["base_salary"]:
                miss = max(0.0, lost - extra) if auto else (cnt["absent"] + 0.5 * cnt["half"])
                ded = round((e["base_salary"] / wd) * miss, 2)
            gross = round((e["base_salary"] or 0) - ded, 2)
            if end_override or (e["end_date"] and e["end_date"] < d2):  # غادر قبل نهاية الفترة: الراتب بنسبة الأيام
                gross = round((e["base_salary"] or 0) / wd * max(0.0, len(wdates) - lost + extra), 2)
        out.append(dict(e=e, cnt=cnt, days=days, ptype=ptype, rate=rate, gross=gross, ded=ded,
                        grants=grants, advances=advances, plus=plus, advance=adv, auto=auto,
                        wdays=len(wdates), lost=lost, extra=extra, d1=d1, d2=d2, due=due,
                        paid=db.execute("SELECT id, day, amount FROM expenses WHERE employee_id=? AND month=?",
                                        (e["id"], mm)).fetchone(),
                        net=round(gross + plus - adv, 2)))
    return out


@app.route("/staff", methods=["GET", "POST"])
@perm_required("attendance")
def staff():
    db = get_db()
    u = current_user()
    if request.method == "POST":
        if u["role"] != "admin":
            abort(403)
        eid = request.form.get("id")
        f = request.form
        data = {
            "branch_id": int(f.get("branch_id") or work_branch()),
            "name": f.get("name", "").strip(),
            "phone": f.get("phone", "").strip(),
            "birth_date": f.get("birth_date") or None,
            "birth_place": f.get("birth_place", "").strip(),
            "address": f.get("address", "").strip(),
            "id_card": f.get("id_card", "").strip(),
            "social_security": 1 if f.get("social_security") == "1" else 0,
            "ss_number": f.get("ss_number", "").strip() if f.get("social_security") == "1" else "",
            "marital_status": f.get("marital_status", "").strip(),
            "children": int(fnum(f.get("children"))),
            "blood_type": f.get("blood_type", "").strip(),
            "emergency_contact": f.get("emergency_contact", "").strip(),
            "hire_date": f.get("hire_date") or None,
            "pay_day": min(28, max(1, int(fnum(f.get("pay_day"), 0)))) if fnum(f.get("pay_day"), 0) else None,
            "post_id": int(f.get("post_id")) if (f.get("post_id") or "").lstrip("-").isdigit() else None,
            "pay_type": f.get("pay_type") if f.get("pay_type") in PAY_TYPES else "daily",
            "daily_wage": fnum(f.get("daily_wage")),
            "base_salary": fnum(f.get("base_salary")),
            "notes": f.get("notes", "").strip(),
            "active": 1 if f.get("active", "1") == "1" else 0,
        }
        if not data["name"]:
            flash("اسم العامل مطلوب", "err")
            return redirect(url_for("staff"))
        if eid:
            db.execute("UPDATE employees SET " + ",".join(f"{k}=?" for k in data) + " WHERE id=?",
                       list(data.values()) + [eid])
            flash("تم تعديل بيانات العامل", "ok")
        else:
            eid = db.execute(f"INSERT INTO employees({','.join(data)}) VALUES({','.join('?' * len(data))})",
                             list(data.values())).lastrowid
            flash("تمت إضافة العامل", "ok")
        db.commit()
        return redirect(url_for("employee_view", eid=eid))
    br = scope_branch()
    t = date.today().isoformat()
    q = """SELECT e.*, b.name AS branch, a.status AS today_status, a.check_in, po.name AS post FROM employees e
           JOIN branches b ON b.id=e.branch_id LEFT JOIN posts po ON po.id=e.post_id
           LEFT JOIN attendance a ON a.employee_id=e.id AND a.day=?"""
    args = [t]
    if br:
        q += " WHERE e.branch_id=?"
        args.append(br)
    rows = db.execute(q + " ORDER BY e.active DESC, e.branch_id, e.name", args).fetchall()
    edit = db.execute("SELECT * FROM employees WHERE id=?", (request.args.get("edit"),)).fetchone() \
        if request.args.get("edit") and u["role"] == "admin" else None
    due = due_salaries(br) if u["role"] == "admin" else []
    return render_template("staff.html", rows=rows, br=br, edit=edit, form_branch=br or work_branch(), due=due,
                           pay_info={r["id"]: (emp_pay_day(r), emp_period(r, current_period_month(r))[2]) for r in rows},
                           posts=all_posts())


@app.route("/attendance", methods=["GET", "POST"])
@perm_required("attendance")
def attendance():
    db = get_db()
    u = current_user()
    br = scope_branch() if u["role"] == "admin" else u["branch_id"]
    if u["role"] == "admin" and not br:
        br = work_branch()
    d = request.values.get("date") or date.today().isoformat()
    if u["role"] != "admin" and d != date.today().isoformat():
        # الاستقبال يسجّل حضور اليوم وأمس فقط
        if d < (date.today() - timedelta(days=1)).isoformat() or d > date.today().isoformat():
            flash("يمكنك تسجيل حضور اليوم أو أمس فقط", "err")
            return redirect(url_for("attendance"))
    emps = db.execute("""SELECT e.*, po.name AS post FROM employees e LEFT JOIN posts po ON po.id=e.post_id
        WHERE e.branch_id=? AND e.active=1 ORDER BY e.name""", (br,)).fetchall()
    if request.method == "POST":
        n = 0
        for e in emps:
            st = request.form.get(f"st_{e['id']}")
            if st not in ATT_STATUS:
                db.execute("DELETE FROM attendance WHERE employee_id=? AND day=?", (e["id"], d))
                continue
            db.execute("""INSERT INTO attendance(employee_id,day,status,check_in,check_out,note,recorded_by)
                VALUES(?,?,?,?,?,?,?) ON CONFLICT(employee_id,day) DO UPDATE SET status=excluded.status,
                check_in=excluded.check_in, check_out=excluded.check_out, note=excluded.note,
                recorded_by=excluded.recorded_by""",
                       (e["id"], d, st, request.form.get(f"in_{e['id']}") or None,
                        request.form.get(f"out_{e['id']}") or None,
                        request.form.get(f"note_{e['id']}", "").strip(), u["id"]))
            n += 1
        db.commit()
        flash(f"تم حفظ الحضور ليوم {d} ({n} عامل)", "ok")
        return redirect(url_for("attendance", date=d, branch=br))
    att = {r["employee_id"]: r for r in db.execute(
        "SELECT * FROM attendance WHERE day=? AND employee_id IN (SELECT id FROM employees WHERE branch_id=?)", (d, br))}
    off = {int(x) for x in (setting("weekly_off") or "").split(",") if x.strip().isdigit()}
    is_off = datetime.strptime(d, "%Y-%m-%d").date().weekday() in off
    return render_template("attendance.html", emps=emps, att=att, d=d, br=br, is_off=is_off,
                           auto=(setting("attendance_mode") or "absences") == "absences")


@app.route("/staff/<int(signed=True):eid>", methods=["GET", "POST"])
@perm_required("attendance")
def employee_view(eid):
    db = get_db()
    e = db.execute("""SELECT e.*, b.name AS branch, po.name AS post FROM employees e
        JOIN branches b ON b.id=e.branch_id LEFT JOIN posts po ON po.id=e.post_id WHERE e.id=?""",
                   (eid,)).fetchone() or abort(404)
    check_emp_access(e)
    if request.method == "POST":
        if current_user()["role"] != "admin":
            abort(403)
        amount = fnum(request.form.get("amount"))
        if amount <= 0 or request.form.get("kind") not in GRANT_KINDS:
            flash("أدخل نوع المنحة ومبلغًا صحيحًا", "err")
        else:
            day = request.form.get("day") or date.today().isoformat()
            dm = request.form.get("deduct_month") if request.form["kind"] == "advance" else None
            db.execute("""INSERT INTO grants(employee_id,day,kind,amount,note,created_by,created_at,deduct_month)
                VALUES(?,?,?,?,?,?,?,?)""",
                       (eid, day, request.form["kind"], amount, request.form.get("note", "").strip(),
                        current_user()["id"], now_str(), dm or day[:7]))
            db.commit()
            flash("تم تسجيل المنحة", "ok")
        return redirect(url_for("employee_view", eid=eid, month=request.args.get("month")))
    mm = request.args.get("month") or current_period_month(e)
    mm, _, _ = month_bounds(mm)
    d1, d2, _ = emp_period(e, mm)
    att = db.execute("SELECT * FROM attendance WHERE employee_id=? AND day BETWEEN ? AND ? ORDER BY day",
                     (eid, d1, d2)).fetchall()
    grants = db.execute("""SELECT * FROM grants WHERE employee_id=? AND (day BETWEEN ? AND ?
        OR (kind='advance' AND deduct_month=?)) ORDER BY day""", (eid, d1, d2, mm)).fetchall()
    summ = month_summary(None, mm, emp_id=eid)
    return render_template("employee.html", e=e, att=att, grants=grants, mm=mm,
                           s=summ[0] if summ else None)


@app.route("/staff/<int(signed=True):eid>/payslip")
@login_required("admin")
def payslip(eid):
    """كشف الأجرة الشهرية للعامل، قابل للطباعة، فيه كل التسبيقات بتواريخها."""
    db = get_db()
    e = db.execute("SELECT * FROM employees WHERE id=?", (eid,)).fetchone() or abort(404)
    mm, _, _ = month_bounds(request.args.get("month") or current_period_month(e))
    s_ = month_summary(None, mm, emp_id=eid)[0]
    d1, d2 = s_["d1"], s_["d2"]
    att = db.execute("SELECT * FROM attendance WHERE employee_id=? AND day BETWEEN ? AND ? ORDER BY day",
                     (eid, d1, d2)).fetchall()
    return render_template("payslip.html", s=s_, att=att, mm=mm, now=datetime.now().strftime("%Y-%m-%d %H:%M"))



@app.route("/staff/<int(signed=True):eid>/leave", methods=["GET", "POST"])
@login_required("admin")
def employee_leave(eid):
    """مغادرة العمل نهائيًا: تصفية الحساب (أجرة الأيام الأخيرة − التسبيقات الباقية) ثم إيقاف العامل،
    فلا تُحسب له أجرة بعد ذلك ولا تظهر في المصاريف الشهرية."""
    db = get_db()
    e = db.execute("""SELECT e.*, b.name AS branch, po.name AS post FROM employees e JOIN branches b ON b.id=e.branch_id
        LEFT JOIN posts po ON po.id=e.post_id WHERE e.id=?""", (eid,)).fetchone() or abort(404)
    last = request.values.get("last_day") or date.today().isoformat()
    try:
        last_d = datetime.strptime(last, "%Y-%m-%d").date()
    except ValueError:
        last_d = date.today()
        last = last_d.isoformat()
    mm = current_period_month(e, last_d)
    s_ = month_summary(None, mm, emp_id=eid, d2_override=last)[0]
    # فترة سابقة لم تُدفع بعد؟
    prev_y, prev_m = (int(mm[:4]) - 1, 12) if mm[5:7] == "01" else (int(mm[:4]), int(mm[5:7]) - 1)
    prev_mm = f"{prev_y:04d}-{prev_m:02d}"
    prev = None
    if e["hire_date"] and e["hire_date"][:10] <= emp_period(e, prev_mm)[1] and \
            not db.execute("SELECT 1 FROM expenses WHERE employee_id=? AND month=?", (eid, prev_mm)).fetchone():
        prev = month_summary(None, prev_mm, emp_id=eid)[0]
    if request.method == "POST":
        if not e["active"]:
            flash("هذا العامل غادر مسبقًا", "err")
            return redirect(url_for("employee_view", eid=eid))
        total = round(s_["net"] + (prev["net"] if prev else 0), 2)
        amount = fnum(request.form.get("amount"), total)
        if prev:
            db.execute("""INSERT INTO expenses(branch_id,day,category,description,amount,method,employee_id,month,created_by,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)""", (e["branch_id"], date.today().isoformat(), "أجور العمال",
                                                 f"أجرة {e['name']} — {prev['d1']} إلى {prev['d2']}", prev["net"], "cash",
                                                 eid, prev_mm, current_user()["id"], now_str()))
            amount -= prev["net"]
        db.execute("""INSERT INTO expenses(branch_id,day,category,description,amount,method,employee_id,month,created_by,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (e["branch_id"], date.today().isoformat(), "أجور العمال",
                                             f"تصفية حساب {e['name']} (مغادرة) — {s_['d1']} إلى {last}", round(amount, 2), "cash",
                                             eid, mm, current_user()["id"], now_str()))
        db.execute("UPDATE employees SET active=0, end_date=?, end_reason=? WHERE id=?",
                   (last, request.form.get("reason", "").strip(), eid))
        audit("مغادرة عامل", f"{e['name']} — آخر يوم {last} — تصفية {total:g}", e["branch_id"])
        db.commit()
        flash(f"تمت تصفية حساب {e['name']} وإيقافه. لن تُحسب له أجرة بعد {last}.", "ok")
        return redirect(url_for("employee_leave", eid=eid, last_day=last, done=1))
    return render_template("leave.html", e=e, s=s_, prev=prev, last=last, mm=mm,
                           total=round(s_["net"] + (prev["net"] if prev else 0), 2),
                           done=bool(request.args.get("done")), now=datetime.now().strftime("%Y-%m-%d %H:%M"))


def due_salaries(branch_id=None):
    """أجور مستحقة: فترات انتهت (أو تنتهي خلال 7 أيام) ولم تُسجَّل كمدفوعة."""
    db = get_db()
    q = "SELECT * FROM employees WHERE active=1"
    args = []
    if branch_id:
        q += " AND branch_id=?"
        args.append(branch_id)
    out = []
    today = date.today()
    for e in db.execute(q + " ORDER BY name", args).fetchall():
        cur = current_period_month(e)
        y, m = (int(cur[:4]) - 1, 12) if cur[5:7] == "01" else (int(cur[:4]), int(cur[5:7]) - 1)
        for mm in (f"{y:04d}-{m:02d}", cur):
            d1, d2, due = emp_period(e, mm)
            if e["hire_date"] and e["hire_date"][:10] > d2:
                continue
            if datetime.strptime(due, "%Y-%m-%d").date() - today > timedelta(days=7):
                continue
            if db.execute("SELECT 1 FROM expenses WHERE employee_id=? AND month=?", (e["id"], mm)).fetchone():
                continue
            out.append(dict(e=e, mm=mm, d1=d1, d2=d2, due=due, late=due <= today.isoformat()))
    return out

@app.route("/staff/payslips")
@login_required("admin")
def payslips_all():
    """طباعة كشوف كل عمال الفرع دفعة واحدة."""
    mm, d1, d2 = month_bounds(request.args.get("month"))
    rows = month_summary(scope_branch(), mm)
    return render_template("payslips_all.html", rows=rows, mm=mm, now=datetime.now().strftime("%Y-%m-%d %H:%M"))


@app.route("/grants/<int(signed=True):gid>/delete", methods=["POST"])
@login_required("admin")
def grant_delete(gid):
    db = get_db()
    g_ = db.execute("SELECT * FROM grants WHERE id=?", (gid,)).fetchone() or abort(404)
    db.execute("DELETE FROM grants WHERE id=?", (gid,))
    db.commit()
    flash("تم حذف المنحة", "ok")
    return redirect(request.referrer or url_for("employee_view", eid=g_["employee_id"]))


@app.route("/staff/report")
@perm_required("attendance")
def staff_report():
    br = scope_branch()
    mm, d1, d2 = month_bounds(request.args.get("month"))
    rows = month_summary(br, mm)
    show_money = current_user()["role"] == "admin"
    tot = dict(gross=sum(r["gross"] for r in rows), plus=sum(r["plus"] for r in rows),
               days=sum(r["days"] for r in rows), adv=sum(r["advance"] for r in rows), net=sum(r["net"] for r in rows))
    return render_template("staff_report.html", rows=rows, br=br, mm=mm, tot=tot, show_money=show_money,
                           now=datetime.now().strftime("%Y-%m-%d %H:%M"))




# ---------------------------------------------------------------- ملف الزيارة (الاستقبال ← المديرة/القسم ← الاستقبال)
def queue_target():
    """قائمة الانتظار التي يعالجها هذا المستخدم: المديرة = المدير في فرعها، أو قسم الليزر/التجميل."""
    u = current_user()
    if u["role"] == "admin":
        return "director", int(fnum(setting("director_branch"), 0)) or None
    if u["role"] in ("laser", "beauty"):
        return u["role"], u["branch_id"]
    if u["role"] == "reception":
        return "reception", u["branch_id"]
    return None, None


def queue_count():
    tgt, br = queue_target()
    if not tgt:
        return 0
    q = "SELECT COUNT(*) n FROM visits WHERE target=? AND status IN ('waiting','treating')"
    args = [tgt]
    if br:
        q += " AND branch_id=?"
        args.append(br)
    return get_db().execute(q, args).fetchone()["n"]


def visit_data(vid):
    db = get_db()
    v = db.execute("""SELECT v.*, c.name AS client, c.phone, c.birth_date, c.gender, c.address, c.chronic,
        c.allergies, c.medications, c.notes AS cnotes, b.name AS branch, u.full_name AS by_name
        FROM visits v JOIN clients c ON c.id=v.client_id JOIN branches b ON b.id=v.branch_id
        LEFT JOIN users u ON u.id=v.created_by WHERE v.id=?""", (vid,)).fetchone() or abort(404)
    u = current_user()
    if u["role"] != "admin" and v["branch_id"] != u["branch_id"]:
        abort(403)
    items = db.execute("""SELECT i.*, u.full_name AS by_name FROM visit_items i LEFT JOIN users u ON u.id=i.added_by
        WHERE i.visit_id=? ORDER BY i.id""", (vid,)).fetchall()
    total = round(sum(i["qty"] * i["unit_price"] for i in items), 2)
    return v, items, total


def add_visit_item(db, v, f, stage):
    kind = f.get("kind", "service")
    qty = fnum(f.get("qty"), 1) or 1
    price = f.get("price", "").strip()
    if price_locked():
        price = ""  # سعر القائمة فقط
        if kind not in ("service", "product"):
            return False
    if kind == "discount":
        desc = f.get("description", "").strip()
        amt = abs(fnum(price))
        if amt <= 0:
            return False
        db.execute("""INSERT INTO visit_items(visit_id,kind,description,qty,unit_price,stage,added_by,created_at)
            VALUES(?,?,?,?,?,?,?,?)""", (v["id"], "discount", desc or "تخفيض", 1, -amt, stage,
                                         current_user()["id"], now_str()))
        return True
    sid = pid = None
    desc = f.get("description", "").strip()
    if kind == "service" and f.get("service_id"):
        srv = db.execute("SELECT * FROM services WHERE id=?", (f["service_id"],)).fetchone()
        if srv:
            sid = srv["id"]
            desc = desc or srv["name"]
            price = price or str(srv["price"])
    elif kind == "product" and f.get("product_id"):
        pr = db.execute("SELECT * FROM products WHERE id=?", (f["product_id"],)).fetchone()
        if pr:
            pid = pr["id"]
            desc = desc or pr["name"]
            price = price or str(pr["price"])
    if not desc:
        return False
    db.execute("""INSERT INTO visit_items(visit_id,kind,service_id,product_id,description,qty,unit_price,stage,
        added_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
               (v["id"], kind if (sid or pid) else "other", sid, pid, desc, qty, fnum(price), stage,
                current_user()["id"], now_str()))
    if pid:
        move_stock(db, pid, v["branch_id"], -qty, f"زيارة {v['id']}", current_user()["id"])
    return True


@app.route("/visits/new", methods=["GET", "POST"])
@perm_required("reception_visits")
def visit_new():
    db = get_db()
    u = current_user()
    br = work_branch()
    if request.method == "POST":
        f = request.form
        if not f.get("client_id"):
            flash("اختر الزبون أو سجّله أولًا", "err")
            return redirect(url_for("visit_new"))
        target = f.get("target") if f.get("target") in VISIT_TARGETS else "director"
        vid = db.execute("""INSERT INTO visits(client_id,branch_id,target,request,status,created_by,created_at)
            VALUES(?,?,?,?,'waiting',?,?)""", (int(f["client_id"]), br, target, f.get("request", "").strip(),
                                              u["id"], now_str())).lastrowid
        v = db.execute("SELECT * FROM visits WHERE id=?", (vid,)).fetchone()
        sids, prices = f.getlist("service_id"), f.getlist("price")
        for i, sid in enumerate(sids):
            if sid:
                add_visit_item(db, v, {"kind": "service", "service_id": sid,
                                       "price": prices[i] if i < len(prices) else ""}, "reception")
        db.commit()
        flash(f"تم إرسال الزبون إلى {VISIT_TARGETS[target]}", "ok")
        return redirect(url_for("reception"))
    sel_client = None
    if request.args.get("client_id"):
        sel_client = db.execute("SELECT * FROM clients WHERE id=?", (request.args["client_id"],)).fetchone()
    dbr = int(fnum(setting("director_branch"), 0))
    targets = {k: v for k, v in VISIT_TARGETS.items()
               if (k == "director" and dbr == br) or (k != "director" and k in branch_depts(br))}
    return render_template("visit_new.html", services=services_for(br), sel_client=sel_client, br=br,
                           targets=targets)


@app.route("/visits/queue")
@login_required()
def visit_queue():
    tgt, br = queue_target()
    return render_template("visit_queue.html", tgt=tgt, br=br)


@app.route("/visits/queue/rows")
@login_required()
def visit_queue_rows():
    """جزء الصفحة الذي يتحدث تلقائيًا كل بضع ثوانٍ."""
    db = get_db()
    tgt, br = queue_target()
    q = """SELECT v.*, c.name AS client, c.phone, c.birth_date, c.gender, c.chronic, c.allergies,
        (SELECT COUNT(*) FROM visit_items i WHERE i.visit_id=v.id) AS n_items
        FROM visits v JOIN clients c ON c.id=v.client_id WHERE v.status IN ('waiting','treating') AND v.target=?"""
    args = [tgt]
    if br:
        q += " AND v.branch_id=?"
        args.append(br)
    rows = db.execute(q + " ORDER BY v.id", args).fetchall()
    return render_template("visit_queue_rows.html", rows=rows)


@app.route("/visits")
@perm_required("reception_visits")
def visits_list():
    db = get_db()
    br = scope_branch()
    d = request.args.get("date") or date.today().isoformat()
    q = """SELECT v.*, c.name AS client, b.name AS branch,
        (SELECT COALESCE(SUM(qty*unit_price),0) FROM visit_items i WHERE i.visit_id=v.id) AS total
        FROM visits v JOIN clients c ON c.id=v.client_id JOIN branches b ON b.id=v.branch_id
        WHERE substr(v.created_at,1,10)=?"""
    args = [d]
    if br:
        q += " AND v.branch_id=?"
        args.append(br)
    rows = db.execute(q + " ORDER BY v.id DESC", args).fetchall()
    return render_template("visits.html", rows=rows, d=d, br=br)


@app.route("/visits/<int(signed=True):vid>", methods=["GET", "POST"])
@login_required()
def visit_view(vid):
    db = get_db()
    u = current_user()
    v, items, total = visit_data(vid)
    tgt, _ = queue_target()
    can_treat = u["role"] == "admin" or (u["role"] in ("laser", "beauty", "reception") and v["target"] == u["role"])
    can_edit = v["status"] in ("waiting", "treating") and (can_treat or u["role"] in ("admin", "reception"))
    if request.method == "POST":
        act = request.form.get("action")
        if u["role"] == "reception" and act in ("add", "remove", "cancel") and not has_perm("reception_visits"):
            abort(403)
        if act == "add" and can_edit:
            stage = "reception" if u["role"] == "reception" and v["target"] != "reception" else "treatment"
            if add_visit_item(db, v, request.form, stage):
                if v["status"] == "waiting" and stage == "treatment":
                    db.execute("UPDATE visits SET status='treating', started_at=? WHERE id=?", (now_str(), vid))
                flash("تمت الإضافة", "ok")
            else:
                flash("اختر خدمة أو منتجًا أو اكتب وصفًا", "err")
        elif act == "remove" and can_edit:
            it = db.execute("SELECT * FROM visit_items WHERE id=? AND visit_id=?",
                            (request.form.get("item_id"), vid)).fetchone()
            if it:
                if it["product_id"]:
                    move_stock(db, it["product_id"], v["branch_id"], it["qty"], f"حذف من زيارة {vid}", u["id"])
                db.execute("DELETE FROM visit_items WHERE id=?", (it["id"],))
                audit("حذف بند من زيارة", f"{it['description']} — {it['qty']*it['unit_price']:g}", v["branch_id"])
                flash("تم الحذف", "ok")
        elif act == "start" and can_treat and v["status"] == "waiting":
            db.execute("UPDATE visits SET status='treating', started_at=? WHERE id=?", (now_str(), vid))
        elif act == "finish" and can_treat and v["status"] in ("waiting", "treating"):
            _, items, total = visit_data(vid)
            db.execute("UPDATE visits SET status='done', done_at=?, done_by=? WHERE id=?", (now_str(), u["id"], vid))
            if total > 0:
                desc = "، ".join(f"{i['description']}" + (f" ×{i['qty']:g}" if i["qty"] != 1 else "") for i in items)
                chid = db.execute("""INSERT INTO charges(branch_id,client_id,dept,description,amount,created_by,created_at,visit_id)
                    VALUES(?,?,?,?,?,?,?,?)""", (v["branch_id"], v["client_id"],
                                                 v["target"] if v["target"] in DEPTS else "reception",
                                                 f"زيارة: {desc}"[:400], total, u["id"], now_str(), vid)).lastrowid
                if request.form.get("collect") and can_collect(u):
                    ch = db.execute("SELECT * FROM charges WHERE id=?", (chid,)).fetchone()
                    pid = pay_charge(db, ch, request.form.get("method", "cash"), u)
                    db.commit()
                    flash("انتهى العلاج وتم تحصيل المبلغ", "ok")
                    return redirect(url_for("receipt", pid=pid))
                flash(f"انتهى العلاج. المبلغ ({total:g}) أُرسل إلى الاستقبال للتحصيل", "ok")
            else:
                db.execute("UPDATE visits SET status='paid' WHERE id=?", (vid,))
                flash("انتهى العلاج (بدون مبلغ)", "ok")
            db.commit()
            return redirect(url_for("visit_queue") if u["role"] != "reception" else url_for("reception"))
        elif act == "cancel" and v["status"] in ("waiting", "treating") and u["role"] in ("admin", "reception"):
            for it in items:
                if it["product_id"]:
                    move_stock(db, it["product_id"], v["branch_id"], it["qty"], f"إلغاء زيارة {vid}", u["id"])
            db.execute("UPDATE visits SET status='cancelled' WHERE id=?", (vid,))
            audit("إلغاء زيارة", f"زيارة {rid_filter(vid)} — {v['client']}", v["branch_id"])
            flash("تم إلغاء الزيارة", "ok")
        db.commit()
        return redirect(url_for("visit_view", vid=vid))
    prods = db.execute("""SELECT p.*, COALESCE(s.qty,0) AS qty FROM products p LEFT JOIN stock s
        ON s.product_id=p.id AND s.branch_id=? WHERE p.active=1 ORDER BY p.name""", (v["branch_id"],)).fetchall()
    vnotes = db.execute("""SELECT n.*, u.full_name AS by_name FROM client_notes n LEFT JOIN users u ON u.id=n.created_by
        WHERE n.client_id=? ORDER BY n.id DESC LIMIT 8""", (v["client_id"],)).fetchall() if has_perm("medical") else []
    return render_template("visit_view.html", v=v, items=items, total=total, services=services_for(v["branch_id"]),
                           vnotes=vnotes,
                           prods=prods, can_treat=can_treat, can_edit=can_edit)


# ---------------------------------------------------------------- الدورات التكوينية والشهادات
def course_or_404(cid):
    c = get_db().execute("""SELECT co.*, b.name AS branch FROM courses co JOIN branches b ON b.id=co.branch_id
        WHERE co.id=?""", (cid,)).fetchone() or abort(404)
    u = current_user()
    if u["role"] != "admin" and c["branch_id"] != u["branch_id"]:
        abort(403)
    return c


def trainees_of(cid):
    return get_db().execute("""SELECT t.*, c.name, c.phone, c.birth_date, c.gender,
        (SELECT COALESCE(SUM(amount),0) FROM payments p WHERE p.enroll_id=t.id AND p.cancelled=0) AS paid
        FROM course_trainees t JOIN clients c ON c.id=t.client_id WHERE t.course_id=? ORDER BY c.name""",
                            (cid,)).fetchall()


@app.route("/courses", methods=["GET", "POST"])
@perm_required("courses")
def courses():
    db = get_db()
    u = current_user()
    if request.method == "POST":
        if price_locked(u):
            abort(403)
        f = request.form
        name = f.get("name", "").strip()
        if not name:
            flash("اكتب اسم الدورة", "err")
            return redirect(url_for("courses"))
        cid = db.execute("""INSERT INTO courses(branch_id,name,price,start_date,end_date,hours,trainer,notes,created_by,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (u["branch_id"] or int(f.get("branch_id") or work_branch()), name,
                                             fnum(f.get("price")), f.get("start_date") or None, f.get("end_date") or None,
                                             fnum(f.get("hours")) or None, f.get("trainer", "").strip(),
                                             f.get("notes", "").strip(), u["id"], now_str())).lastrowid
        db.commit()
        flash("تم إنشاء الدورة. سجّل المتكونين فيها.", "ok")
        return redirect(url_for("course_view", cid=cid))
    br = scope_branch()
    q = """SELECT co.*, b.name AS branch, (SELECT COUNT(*) FROM course_trainees t WHERE t.course_id=co.id
        AND t.status<>'withdrawn') AS n FROM courses co JOIN branches b ON b.id=co.branch_id WHERE 1=1"""
    args = []
    if br:
        q += " AND co.branch_id=?"
        args.append(br)
    rows = db.execute(q + " ORDER BY co.status='finished', co.start_date DESC, co.id DESC", args).fetchall()
    return render_template("courses.html", rows=rows, br=br)


@app.route("/courses/<int(signed=True):cid>", methods=["GET", "POST"])
@perm_required("courses")
def course_view(cid):
    db = get_db()
    u = current_user()
    c = course_or_404(cid)
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        if act == "edit":
            if price_locked(u):
                abort(403)
            db.execute("""UPDATE courses SET name=?,price=?,start_date=?,end_date=?,hours=?,trainer=?,notes=?,status=?
                WHERE id=?""", (f.get("name", "").strip() or c["name"], fnum(f.get("price")), f.get("start_date") or None,
                                f.get("end_date") or None, fnum(f.get("hours")) or None, f.get("trainer", "").strip(),
                                f.get("notes", "").strip(), f.get("status") if f.get("status") in COURSE_STATUS else c["status"],
                                cid))
            flash("تم حفظ الدورة", "ok")
        elif act == "enroll":
            cl = f.get("client_id")
            if not cl:
                flash("اختر المتكوّن أو سجّله", "err")
            elif db.execute("SELECT 1 FROM course_trainees WHERE course_id=? AND client_id=?", (cid, cl)).fetchone():
                flash("هذا الشخص مسجّل في الدورة مسبقًا", "err")
            else:
                price = c["price"] if price_locked(u) or not f.get("price") else fnum(f.get("price"))
                db.execute("""INSERT INTO course_trainees(course_id,client_id,price,enrolled_at,created_by)
                    VALUES(?,?,?,?,?)""", (cid, int(cl), price, now_str(), u["id"]))
                flash("تم التسجيل في الدورة", "ok")
        elif act == "pay":
            t = db.execute("SELECT t.*, (SELECT COALESCE(SUM(amount),0) FROM payments p WHERE p.enroll_id=t.id AND p.cancelled=0) AS paid "
                           "FROM course_trainees t WHERE t.id=? AND t.course_id=?", (f.get("tid"), cid)).fetchone()
            amount = fnum(f.get("amount"))
            if not t or amount <= 0:
                flash("أدخل المبلغ المدفوع", "err")
            elif amount > round(t["price"] - t["paid"], 2) + 0.001:
                flash(f"المبلغ أكبر من الباقي ({t['price'] - t['paid']:g})", "err")
            else:
                pid = make_payment(db, c["branch_id"], t["client_id"], amount, f.get("method", "cash"), "course",
                                   f"دورة: {c['name']}", u["id"])
                db.execute("UPDATE payments SET enroll_id=? WHERE id=?", (t["id"], pid))
                db.commit()
                flash("تم تسجيل الدفع", "ok")
                return redirect(url_for("receipt", pid=pid))
        elif act == "status":
            st = f.get("status")
            if st in TRAINEE_STATUS:
                db.execute("UPDATE course_trainees SET status=?, completed_at=? WHERE id=? AND course_id=?",
                           (st, now_str() if st == "completed" else None, f.get("tid"), cid))
        elif act == "price" and not price_locked(u):
            db.execute("UPDATE course_trainees SET price=? WHERE id=? AND course_id=?", (fnum(f.get("price")), f.get("tid"), cid))
            flash("تم تعديل سعر المتكوّن", "ok")
        elif act == "finish":
            db.execute("UPDATE course_trainees SET status='completed', completed_at=? WHERE course_id=? AND status='enrolled'",
                       (now_str(), cid))
            db.execute("UPDATE courses SET status='finished' WHERE id=?", (cid,))
            flash("انتهت الدورة: كل المسجّلين أكملوا الدورة ويمكن طباعة شهاداتهم", "ok")
        db.commit()
        return redirect(url_for("course_view", cid=cid))
    rows = trainees_of(cid)
    tot = dict(price=sum(r["price"] for r in rows if r["status"] != "withdrawn"),
               paid=sum(r["paid"] for r in rows))
    sel_client = None
    if request.args.get("client_id"):
        sel_client = db.execute("SELECT id,name,phone FROM clients WHERE id=?", (request.args["client_id"],)).fetchone()
    return render_template("course_view.html", c=c, rows=rows, tot=tot, sel_client=sel_client)


def fmt_date(d):
    try:
        return datetime.strptime(d[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return d or "...."


def cert_texts(c, t):
    """النص الافتراضي للشهادة حسب جنس المتكوّن، أو النص المعدّل المحفوظ."""
    fem = (t["gender"] or "") == "أنثى"
    vals = dict(center=setting("center_name"), name=t["name"], course=c["name"],
                sayed="السيدة" if fem else "السيد", mawlud="المولودة" if fem else "المولود",
                tabaa="تابعت" if fem else "تابع", birth_date=fmt_date(t["birth_date"]),
                start=fmt_date(c["start_date"]), end=fmt_date(c["end_date"]),
                hours=f"{c['hours']:g}" if c["hours"] else "....", trainer=c["trainer"] or setting("cert_signer"),
                branch=c["branch"], date=fmt_date((t["completed_at"] or now_str())[:10]))

    def fill(x):
        try:
            return x.format(**vals)
        except (KeyError, IndexError, ValueError):
            return x
    def st(k):
        return setting(k) or DEFAULT_SETTINGS[k]
    return dict(title=t["cert_title"] or fill(st("cert_title")),
                body=t["cert_body"] or fill(st("cert_body")),
                footer=t["cert_footer"] or fill(st("cert_footer")),
                place_date=f"{c['branch']} في {vals['date']}", custom=bool(t["cert_body"]))


@app.route("/certificates/<int(signed=True):tid>", methods=["GET", "POST"])
@perm_required("courses")
def certificate(tid):
    db = get_db()
    t = db.execute("""SELECT t.*, c.name, c.birth_date, c.gender,
        (SELECT COALESCE(SUM(amount),0) FROM payments p WHERE p.enroll_id=t.id AND p.cancelled=0) AS paid
        FROM course_trainees t JOIN clients c ON c.id=t.client_id WHERE t.id=?""", (tid,)).fetchone() or abort(404)
    c = course_or_404(t["course_id"])
    if request.method == "POST":
        if request.form.get("action") == "reset":
            db.execute("UPDATE course_trainees SET cert_title=NULL, cert_body=NULL, cert_footer=NULL WHERE id=?", (tid,))
            flash("رجع نص الشهادة إلى النص الافتراضي", "ok")
        elif request.form.get("action") == "printed":
            db.execute("UPDATE course_trainees SET cert_printed_at=? WHERE id=?", (now_str(), tid))
            db.commit()
            return {"ok": True}
        else:
            db.execute("UPDATE course_trainees SET cert_title=?, cert_body=?, cert_footer=? WHERE id=?",
                       (request.form.get("title", "").strip(), request.form.get("body", "").strip(),
                        request.form.get("footer", "").strip(), tid))
            flash("تم حفظ تعديلات الشهادة", "ok")
        db.commit()
        return redirect(url_for("certificate", tid=tid))
    txt = cert_texts(c, t)
    return render_template("certificate.html", c=c, t=t, txt=txt,
                           stamp=setting("stamp_img"), signature=setting("signature_img"),
                           signer=setting("cert_signer") or DEFAULT_SETTINGS["cert_signer"], cert_no=f"{(t['completed_at'] or now_str())[:4]}/{rid_filter(t['id'])}")


@app.route("/settings/images", methods=["POST"])
@login_required("admin")
def settings_images():
    db = get_db()
    changed = False
    for key in ("stamp_img", "signature_img"):
        if request.form.get(f"del_{key}"):
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,'')", (key,))
            changed = True
        f = request.files.get(key)
        if f and f.filename:
            data = f.read()
            if len(data) > 1_500_000:
                flash("الصورة كبيرة جدًا (الحد 1.5 ميغا)", "err")
                continue
            mime = "image/png" if data[:4] == b"\x89PNG" else ("image/jpeg" if data[:2] == b"\xff\xd8" else None)
            if not mime:
                flash("الصورة يجب أن تكون PNG أو JPG", "err")
                continue
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                       (key, f"data:{mime};base64," + base64.b64encode(data).decode()))
            changed = True
    if changed:
        db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('img_ver',?)", (str(int(time.time())),))
        flash("تم حفظ الصور", "ok")
    db.commit()
    return redirect(url_for("settings") + "#cert")


# ---------------------------------------------------------------- المصاريف
@app.route("/expenses", methods=["GET", "POST"])
@perm_required("expenses")
def expenses():
    db = get_db()
    u = current_user()
    admin = u["role"] == "admin"
    if request.method == "POST":
        f = request.form
        if f.get("action") == "delete":
            e = db.execute("SELECT * FROM expenses WHERE id=?", (f.get("id"),)).fetchone()
            if e and (admin or (e["created_by"] == u["id"] and e["day"] == date.today().isoformat())):
                db.execute("DELETE FROM expenses WHERE id=?", (e["id"],))
                audit("حذف مصروف", f"{e['category']} — {e['description'] or ''} — {e['amount']:g}", e["branch_id"])
                db.commit()
                flash("تم حذف المصروف", "ok")
            return redirect(request.referrer or url_for("expenses"))
        amount = fnum(f.get("amount"))
        if amount <= 0:
            flash("أدخل مبلغ المصروف", "err")
        else:
            if admin:
                br, day = int(f.get("branch_id") or work_branch()), f.get("day") or date.today().isoformat()
                from_cash = 1 if f.get("from_cash") else 0
                role = f.get("role") if from_cash and f.get("role") in PLACES else None
            else:  # العامل: مصروف من صندوق اليوم في مكانه فقط
                br, day, from_cash, role = u["branch_id"], date.today().isoformat(), 1, u["role"]
            db.execute("""INSERT INTO expenses(branch_id,day,category,description,amount,method,created_by,created_at,from_cash,role)
                VALUES(?,?,?,?,?,?,?,?,?,?)""", (br, day, f.get("category") if f.get("category") in EXPENSE_CATS else "أخرى",
                                                 f.get("description", "").strip(), amount, "cash" if from_cash else f.get("method", "cash"),
                                                 u["id"], now_str(), from_cash, role))
            audit("مصروف", f"{f.get('category')} — {f.get('description', '')} — {amount:g}" + (" (من الصندوق)" if from_cash else ""), br)
            db.commit()
            flash("تم تسجيل المصروف" + (" وخرج من صندوق اليوم" if from_cash else ""), "ok")
        return redirect(url_for("expenses", month=None if not admin else (f.get("day") or "")[:7] or None))
    if not admin:
        rows = db.execute("""SELECT e.*, b.name AS branch FROM expenses e JOIN branches b ON b.id=e.branch_id
            WHERE e.created_by=? AND e.day=? ORDER BY e.id DESC""", (u["id"], date.today().isoformat())).fetchall()
        return render_template("expenses.html", rows=rows, mm=None, br=u["branch_id"], by_cat=[], total=0, cat="", worker=True)
    mm, d1, d2 = month_bounds(request.args.get("month"))
    br = scope_branch()
    q = """SELECT e.*, b.name AS branch FROM expenses e JOIN branches b ON b.id=e.branch_id WHERE e.day BETWEEN ? AND ?"""
    args = [d1, d2]
    if br:
        q += " AND e.branch_id=?"
        args.append(br)
    if request.args.get("cat") in EXPENSE_CATS:
        q += " AND e.category=?"
        args.append(request.args["cat"])
    rows = db.execute(q + " ORDER BY e.day DESC, e.id DESC", args).fetchall()
    by_cat = {}
    for r in rows:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + r["amount"]
    return render_template("expenses.html", rows=rows, mm=mm, br=br, by_cat=sorted(by_cat.items(), key=lambda x: -x[1]),
                           total=sum(r["amount"] for r in rows), cat=request.args.get("cat", ""), worker=False)


# ---------------------------------------------------------------- الصندوق اليومي
def day_cash(db, branch_id, day, role):
    """حساب صندوق مكان (استقبال/غرفة) ليوم واحد: يبدأ من صفر."""
    rows = db.execute("""SELECT p.method, COALESCE(SUM(p.amount),0) s, COUNT(*) n FROM payments p JOIN users u ON u.id=p.received_by
        WHERE p.branch_id=? AND substr(p.created_at,1,10)=? AND u.role=? AND p.cancelled=0 GROUP BY p.method""",
                      (branch_id, day, role)).fetchall()
    by = {r["method"]: r["s"] for r in rows}
    out = db.execute("""SELECT COALESCE(SUM(amount),0) FROM expenses WHERE branch_id=? AND day=? AND from_cash=1 AND role=?""",
                     (branch_id, day, role)).fetchone()[0]
    cash = by.get("cash", 0)
    return dict(cash=cash, card=by.get("card", 0), ccp=by.get("ccp", 0), total=sum(by.values()),
                n=sum(r["n"] for r in rows), out=out, expected=round(cash - out, 2))


@app.route("/cash/close", methods=["GET", "POST"])
@perm_required("cash_close")
def cash_close():
    """إغلاق صندوق اليوم: العامل يعدّ النقود ويكتب المبلغ دون أن يرى ما سجّله البرنامج."""
    db = get_db()
    u = current_user()
    if u["role"] == "admin":
        flash("إغلاق الصندوق يقوم به العامل في مكانه. المديرة ترى النتيجة في «الصندوق اليومي».", "ok")
        return redirect(url_for("cash_daily"))
    today = date.today().isoformat()
    ex = db.execute("SELECT * FROM cash_days WHERE branch_id=? AND day=? AND role=?",
                    (u["branch_id"], today, u["role"])).fetchone()
    if request.method == "POST":
        counted = fnum(request.form.get("counted"), -1)
        if counted < 0:
            flash("اكتب المبلغ الموجود في الصندوق بعد عدّه", "err")
            return redirect(url_for("cash_close"))
        exp = day_cash(db, u["branch_id"], today, u["role"])["expected"]
        if ex:
            db.execute("UPDATE cash_days SET counted=?, expected=?, note=?, closed_by=?, closed_at=? WHERE id=?",
                       (counted, exp, request.form.get("note", "").strip(), u["id"], now_str(), ex["id"]))
        else:
            db.execute("""INSERT INTO cash_days(branch_id,day,role,counted,expected,note,closed_by,closed_at)
                VALUES(?,?,?,?,?,?,?,?)""", (u["branch_id"], today, u["role"], counted, exp,
                                             request.form.get("note", "").strip(), u["id"], now_str()))
        audit("إغلاق الصندوق", f"{PLACES.get(u['role'])} — المبلغ المعدود {counted:g}", u["branch_id"])
        db.commit()
        flash("تم إغلاق صندوق اليوم. غدًا يبدأ صندوق جديد من صفر.", "ok")
        return redirect(url_for("dashboard"))
    return render_template("cash_close.html", ex=ex, today=today)


@app.route("/cash/daily")
@login_required("admin")
def cash_daily():
    """المديرة: الصندوق يومًا بيوم لكل فرع ومكان، للفترة التي تختارها."""
    db = get_db()
    d1 = request.args.get("from") or date.today().replace(day=1).isoformat()
    d2 = request.args.get("to") or date.today().isoformat()
    br = scope_branch()
    branches_ = [b for b in db.execute("SELECT * FROM branches WHERE active=1 ORDER BY id").fetchall() if not br or b["id"] == br]
    rows, tot = [], dict(cash=0, card=0, ccp=0, total=0, out=0, expected=0, counted=0, diff=0)
    d = datetime.strptime(d2, "%Y-%m-%d").date()
    start = datetime.strptime(d1, "%Y-%m-%d").date()
    while d >= start and len(rows) < 2000:
        ds = d.isoformat()
        for b in branches_:
            for role in ["reception"] + [k for k in branch_depts(b["id"]) if k in ("laser", "beauty")]:
                c = day_cash(db, b["id"], ds, role)
                cd = db.execute("""SELECT cd.*, us.full_name AS by_name FROM cash_days cd LEFT JOIN users us ON us.id=cd.closed_by
                    WHERE cd.branch_id=? AND cd.day=? AND cd.role=?""", (b["id"], ds, role)).fetchone()
                if not c["n"] and not c["out"] and not cd:
                    continue
                diff = round((cd["counted"] if cd else 0) - c["expected"], 2) if cd else None
                rows.append(dict(day=ds, branch=b["name"], bid=b["id"], role=role, c=c, cd=cd, diff=diff))
                for k in ("cash", "card", "ccp", "total", "out", "expected"):
                    tot[k] += c[k]
                if cd:
                    tot["counted"] += cd["counted"] or 0
                    tot["diff"] += diff
        d -= timedelta(days=1)
    admin_pay = db.execute("""SELECT COALESCE(SUM(p.amount),0) FROM payments p JOIN users u ON u.id=p.received_by
        WHERE u.role='admin' AND p.cancelled=0 AND substr(p.created_at,1,10) BETWEEN ? AND ?""" + (" AND p.branch_id=?" if br else ""),
                           [d1, d2] + ([br] if br else [])).fetchone()[0]
    return render_template("cash_daily.html", rows=rows, tot=tot, d1=d1, d2=d2, br=br, admin_pay=admin_pay)


@app.route("/audit")
@login_required("admin")
def audit_page():
    db = get_db()
    d1 = request.args.get("from") or (date.today() - timedelta(days=7)).isoformat()
    d2 = request.args.get("to") or date.today().isoformat()
    br = scope_branch()
    q = """SELECT a.*, u.full_name, u.username, u.role, b.name AS branch FROM audit a LEFT JOIN users u ON u.id=a.user_id
        LEFT JOIN branches b ON b.id=a.branch_id WHERE substr(a.created_at,1,10) BETWEEN ? AND ?"""
    args = [d1, d2]
    if br:
        q += " AND a.branch_id=?"
        args.append(br)
    if request.args.get("q"):
        q += " AND (a.action LIKE ? OR a.details LIKE ?)"
        args += [f"%{request.args['q']}%"] * 2
    rows = db.execute(q + " ORDER BY a.created_at DESC LIMIT 1000", args).fetchall()
    return render_template("audit.html", rows=rows, d1=d1, d2=d2, br=br, qq=request.args.get("q", ""))


@app.route("/staff/<int(signed=True):eid>/paid", methods=["POST"])
@login_required("admin")
def salary_paid(eid):
    """تسجيل دفع أجرة الشهر كمصروف."""
    db = get_db()
    mm, _, _ = month_bounds(request.form.get("month"))
    s_ = month_summary(None, mm, emp_id=eid)[0]
    if db.execute("SELECT 1 FROM expenses WHERE employee_id=? AND month=?", (eid, mm)).fetchone():
        flash("أجرة هذا الشهر مسجلة كمدفوعة مسبقًا", "err")
    else:
        db.execute("""INSERT INTO expenses(branch_id,day,category,description,amount,method,employee_id,month,created_by,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (s_["e"]["branch_id"], date.today().isoformat(), "أجور العمال",
                                             f"أجرة {s_['e']['name']} — {s_['d1']} إلى {s_['d2']}", fnum(request.form.get("amount"), s_["net"]),
                                             "cash", eid, mm, current_user()["id"], now_str()))
        db.commit()
        flash("تم تسجيل دفع الأجرة في المصاريف", "ok")
    return redirect(request.referrer or url_for("payslip", eid=eid, month=mm))


# ---------------------------------------------------------------- التقارير
def report_data(br, d1, d2):
    db = get_db()
    bw, ba = ("", [])
    if br:
        bw, ba = (" AND branch_id=?", [br])
    pays = db.execute(f"""SELECT * FROM payments WHERE cancelled=0 AND substr(created_at,1,10) BETWEEN ? AND ?{bw}""",
                      [d1, d2] + ba).fetchall()
    income = sum(p["amount"] for p in pays)
    exps = db.execute(f"SELECT * FROM expenses WHERE day BETWEEN ? AND ?{bw}", [d1, d2] + ba).fetchall()
    expense = sum(e["amount"] for e in exps)
    # تكلفة المنتجات المباعة
    cogs = db.execute(f"""SELECT COALESCE(SUM(si.qty*COALESCE(si.unit_cost,0)),0) FROM sale_items si JOIN payments p ON p.id=si.payment_id
        WHERE p.cancelled=0 AND substr(p.created_at,1,10) BETWEEN ? AND ?{bw.replace('branch_id','p.branch_id')}""",
                      [d1, d2] + ba).fetchone()[0]
    by_kind, by_dept, by_branch, by_day, by_method = {}, {}, {}, {}, {}
    names = {b["id"]: b["name"] for b in db.execute("SELECT id,name FROM branches")}
    for p in pays:
        by_kind[PAY_KINDS.get(p["kind"], p["kind"])] = by_kind.get(PAY_KINDS.get(p["kind"], p["kind"]), 0) + p["amount"]
        dk = DEPTS.get(p["dept"] or "reception", "")
        by_dept[dk] = by_dept.get(dk, 0) + p["amount"]
        by_branch[names.get(p["branch_id"], "")] = by_branch.get(names.get(p["branch_id"], ""), 0) + p["amount"]
        by_day[p["created_at"][:10]] = by_day.get(p["created_at"][:10], 0) + p["amount"]
        mk = METHODS.get(p["method"], p["method"])
        by_method[mk] = by_method.get(mk, 0) + p["amount"]
    exp_cat, exp_branch = {}, {}
    for e in exps:
        exp_cat[e["category"]] = exp_cat.get(e["category"], 0) + e["amount"]
        exp_branch[names.get(e["branch_id"], "")] = exp_branch.get(names.get(e["branch_id"], ""), 0) + e["amount"]
    top_products = db.execute(f"""SELECT pr.name, SUM(si.qty) q, SUM(si.qty*si.unit_price) rev,
        SUM(si.qty*(si.unit_price-COALESCE(si.unit_cost,0))) margin FROM sale_items si
        JOIN payments p ON p.id=si.payment_id JOIN products pr ON pr.id=si.product_id
        WHERE p.cancelled=0 AND substr(p.created_at,1,10) BETWEEN ? AND ?{bw.replace('branch_id','p.branch_id')}
        GROUP BY pr.id ORDER BY rev DESC LIMIT 15""", [d1, d2] + ba).fetchall()
    # الخدمات: من الزيارات (البنود) ومن المواعيد/الحصص المدفوعة
    top_services = db.execute(f"""SELECT name, SUM(n) n, SUM(rev) rev FROM (
        SELECT i.description AS name, SUM(i.qty) n, SUM(i.qty*i.unit_price) rev FROM visit_items i
          JOIN visits v ON v.id=i.visit_id WHERE v.status='paid' AND i.kind<>'product'
          AND substr(v.created_at,1,10) BETWEEN ? AND ?{bw.replace('branch_id','v.branch_id')} GROUP BY i.description
        UNION ALL
        SELECT COALESCE(s.name, 'خدمة'), COUNT(*), SUM(p.amount) FROM charges ch JOIN payments p ON p.id=ch.payment_id
          LEFT JOIN services s ON s.id=ch.service_id WHERE ch.status='paid' AND ch.visit_id IS NULL AND p.cancelled=0
          AND substr(p.created_at,1,10) BETWEEN ? AND ?{bw.replace('branch_id','p.branch_id')} GROUP BY s.id
        ) GROUP BY name ORDER BY rev DESC LIMIT 15""", [d1, d2] + ba + [d1, d2] + ba).fetchall()
    new_clients = db.execute(f"SELECT COUNT(*) FROM clients WHERE substr(created_at,1,10) BETWEEN ? AND ?{bw}",
                             [d1, d2] + ba).fetchone()[0]
    served = db.execute(f"""SELECT COUNT(DISTINCT client_id) FROM payments WHERE cancelled=0 AND client_id IS NOT NULL
        AND substr(created_at,1,10) BETWEEN ? AND ?{bw}""", [d1, d2] + ba).fetchone()[0]
    debts = db.execute(f"SELECT COALESCE(SUM(amount),0) FROM charges WHERE status='debt'{bw}", ba).fetchone()[0]
    days, d = [], datetime.strptime(d1, "%Y-%m-%d").date()
    end = datetime.strptime(d2, "%Y-%m-%d").date()
    while d <= end and len(days) < 400:
        days.append((d.isoformat(), by_day.get(d.isoformat(), 0)))
        d += timedelta(days=1)

    def srt(x):
        return sorted(x.items(), key=lambda kv: -kv[1])
    return dict(income=income, expense=expense, cogs=cogs, profit=income - expense, n_pay=len(pays),
                by_kind=srt(by_kind), by_dept=srt(by_dept), by_branch=srt(by_branch), by_method=srt(by_method),
                exp_cat=srt(exp_cat), exp_branch=srt(exp_branch), top_products=top_products, top_services=top_services,
                new_clients=new_clients, served=served, debts=debts, days=days,
                max_day=max([v for _, v in days] or [0]) or 1)


@app.route("/reports")
@login_required("admin")
def reports():
    br = scope_branch()
    if request.args.get("from"):
        d1 = request.args["from"]
        d2 = request.args.get("to") or d1
        mm = None
    else:
        mm, d1, d2 = month_bounds(request.args.get("month"))
    r = report_data(br, d1, d2)
    # مقارنة بالأشهر الستة الأخيرة
    months = []
    base = datetime.strptime(d1[:7] + "-01", "%Y-%m-%d").date()
    for i in range(5, -1, -1):
        y, m = base.year, base.month - i
        while m <= 0:
            m += 12
            y -= 1
        k, a, b = month_bounds(f"{y:04d}-{m:02d}")
        x = report_data(br, a, b)
        months.append((k, x["income"], x["expense"]))
    mx = max([max(a, b) for _, a, b in months] or [1]) or 1
    return render_template("reports.html", r=r, br=br, mm=mm, d1=d1, d2=d2, months=months, mx=mx)


# ---------------------------------------------------------------- الملف الطبي ووثيقة الموافقة
def can_see_photos(u=None):
    return has_perm("medical", u)


@app.route("/clients/<int(signed=True):cid>/notes", methods=["POST"])
@perm_required("medical")
def client_note(cid):
    db = get_db()
    u = current_user()
    db.execute("SELECT 1 FROM clients WHERE id=?", (cid,)).fetchone() or abort(404)
    if request.form.get("action") == "delete" and u["role"] == "admin":
        db.execute("DELETE FROM client_notes WHERE id=? AND client_id=?", (request.form.get("id"), cid))
    else:
        note = request.form.get("note", "").strip()
        if note:
            db.execute("INSERT INTO client_notes(client_id,branch_id,visit_id,note,created_by,created_at) VALUES(?,?,?,?,?,?)",
                       (cid, u["branch_id"] or work_branch(), request.form.get("visit_id") or None, note, u["id"], now_str()))
            flash("تمت إضافة الملاحظة إلى الملف", "ok")
    db.commit()
    return redirect(request.referrer or url_for("client_view", cid=cid))


@app.route("/clients/<int(signed=True):cid>/photos", methods=["POST"])
@perm_required("medical")
def client_photo(cid):
    db = get_db()
    u = current_user()
    db.execute("SELECT 1 FROM clients WHERE id=?", (cid,)).fetchone() or abort(404)
    if request.form.get("action") == "delete":
        if u["role"] == "admin":
            db.execute("DELETE FROM client_photos WHERE id=? AND client_id=?", (request.form.get("id"), cid))
            db.commit()
        return redirect(request.referrer or url_for("client_view", cid=cid))
    n = 0
    for f in request.files.getlist("photo"):
        if not f or not f.filename:
            continue
        raw = f.read()
        try:  # تصغير الصورة لتخفيف قاعدة البيانات والمزامنة
            from PIL import Image, ImageOps
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
            im.thumbnail((1280, 1280))
            out = io.BytesIO()
            im.save(out, "JPEG", quality=75, optimize=True)
            raw, mime = out.getvalue(), "image/jpeg"
        except Exception:
            mime = "image/png" if raw[:4] == b"\x89PNG" else "image/jpeg"
            if len(raw) > 3_000_000:
                flash("الصورة كبيرة جدًا", "err")
                continue
        db.execute("INSERT INTO client_photos(client_id,branch_id,kind,note,data,created_by,created_at) VALUES(?,?,?,?,?,?,?)",
                   (cid, u["branch_id"] or work_branch(), request.form.get("kind", "before"),
                    request.form.get("note", "").strip(), f"data:{mime};base64," + base64.b64encode(raw).decode(),
                    u["id"], now_str()))
        n += 1
    db.commit()
    if n:
        flash(f"تم حفظ {n} صورة", "ok")
    return redirect(request.referrer or url_for("client_view", cid=cid))


@app.route("/photos/<int(signed=True):phid>")
@perm_required("medical")
def photo(phid):
    r = get_db().execute("SELECT data FROM client_photos WHERE id=?", (phid,)).fetchone() or abort(404)
    head, b64 = r["data"].split(",", 1)
    return Response(base64.b64decode(b64), mimetype=head[5:].split(";")[0],
                    headers={"Cache-Control": "private, max-age=86400"})


@app.route("/clients/<int(signed=True):cid>/consent", methods=["GET", "POST"])
@perm_required("consent")
def consent(cid):
    db = get_db()
    c = db.execute("SELECT * FROM clients WHERE id=?", (cid,)).fetchone() or abort(404)
    proc = request.values.get("procedure", "").strip() or "...................."
    if request.method == "POST":  # تسجيل الطباعة في الملف
        db.execute("INSERT INTO client_notes(client_id,branch_id,note,created_by,created_at) VALUES(?,?,?,?,?)",
                   (cid, current_user()["branch_id"] or work_branch(), f"طُبعت وثيقة الموافقة على: {proc}",
                    current_user()["id"], now_str()))
        db.commit()
        return {"ok": True}
    vals = dict(name=c["name"], procedure=proc, center=setting("center_name"), phone=c["phone"] or "",
                birth_date=fmt_date(c["birth_date"]), date=fmt_date(date.today().isoformat()))

    def fill(x):
        try:
            return x.format(**vals)
        except (KeyError, IndexError, ValueError):
            return x
    body = fill(setting("consent_body") or DEFAULT_SETTINGS["consent_body"])
    return render_template("consent.html", c=c, proc=proc, vals=vals,
                           title=setting("consent_title") or DEFAULT_SETTINGS["consent_title"],
                           lines=body.split("\n"), services=services_for(work_branch()))


# ---------------------------------------------------------------- الموردون وطلبيات الشراء
def supplier_balance(db, sid):
    total = db.execute("""SELECT COALESCE(SUM(i.qty*i.unit_cost),0) FROM purchase_items i JOIN purchases p ON p.id=i.purchase_id
        WHERE p.supplier_id=? AND p.status='received'""", (sid,)).fetchone()[0]
    paid = db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE supplier_id=?", (sid,)).fetchone()[0]
    return round(total, 2), round(paid, 2)


@app.route("/suppliers", methods=["GET", "POST"])
@login_required("admin")
def suppliers():
    db = get_db()
    if request.method == "POST":
        f = request.form
        vals = (f.get("name", "").strip(), f.get("phone", "").strip(), f.get("address", "").strip(),
                f.get("notes", "").strip(), 1 if f.get("active", "1") == "1" else 0)
        if not vals[0]:
            flash("اسم المورد مطلوب", "err")
        elif f.get("id"):
            db.execute("UPDATE suppliers SET name=?,phone=?,address=?,notes=?,active=? WHERE id=?", vals + (f["id"],))
            flash("تم التعديل", "ok")
        else:
            db.execute("INSERT INTO suppliers(name,phone,address,notes,active) VALUES(?,?,?,?,?)", vals)
            flash("تمت إضافة المورد", "ok")
        db.commit()
        return redirect(url_for("suppliers"))
    rows = []
    for sp in db.execute("SELECT * FROM suppliers ORDER BY active DESC, name").fetchall():
        t, p = supplier_balance(db, sp["id"])
        rows.append(dict(sp, total=t, paid=p, rest=round(t - p, 2)))
    edit = db.execute("SELECT * FROM suppliers WHERE id=?", (request.args.get("edit"),)).fetchone() \
        if request.args.get("edit") else None
    return render_template("suppliers.html", rows=rows, edit=edit)


@app.route("/purchases")
@perm_required("purchases")
def purchases():
    db = get_db()
    br = scope_branch()
    if current_user()["role"] != "admin":
        br = current_user()["branch_id"]
    q = """SELECT p.*, s.name AS supplier, b.name AS branch,
        (SELECT COALESCE(SUM(qty*unit_cost),0) FROM purchase_items i WHERE i.purchase_id=p.id) AS total,
        (SELECT COALESCE(SUM(amount),0) FROM expenses e WHERE e.purchase_id=p.id) AS paid
        FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id JOIN branches b ON b.id=p.branch_id WHERE 1=1"""
    args = []
    if br:
        q += " AND p.branch_id=?"
        args.append(br)
    if request.args.get("supplier"):
        q += " AND p.supplier_id=?"
        args.append(request.args["supplier"])
    rows = db.execute(q + " ORDER BY p.id DESC LIMIT 300", args).fetchall()
    return render_template("purchases.html", rows=rows, br=br)


@app.route("/purchases/new", methods=["GET", "POST"])
@perm_required("purchases")
def purchase_new():
    db = get_db()
    if request.method == "POST":
        f = request.form
        pids, qtys, costs = f.getlist("product_id"), f.getlist("qty"), f.getlist("cost")
        lines = [(int(p), fnum(q), fnum(c)) for p, q, c in zip(pids, qtys, costs) if p and fnum(q) > 0]
        if not lines:
            flash("أضف منتجًا واحدًا على الأقل بكمية", "err")
            return redirect(url_for("purchase_new"))
        pid = db.execute("""INSERT INTO purchases(supplier_id,branch_id,day,notes,created_by,created_at)
            VALUES(?,?,?,?,?,?)""", (f.get("supplier_id") or None, current_user()["branch_id"] or int(f.get("branch_id") or work_branch()),
                                     f.get("day") or date.today().isoformat(), f.get("notes", "").strip(),
                                     current_user()["id"], now_str())).lastrowid
        for p, q, c in lines:
            db.execute("INSERT INTO purchase_items(purchase_id,product_id,qty,unit_cost) VALUES(?,?,?,?)", (pid, p, q, c))
        db.commit()
        flash("تم إنشاء طلبية الشراء", "ok")
        return redirect(url_for("purchase_view", pid=pid))
    prods = db.execute("SELECT id,name,cost_price,category FROM products WHERE active=1 ORDER BY category,name").fetchall()
    pre = []
    for part in (request.args.get("items") or "").split(","):  # من صفحة تنبيهات المخزون: id:qty
        if ":" in part:
            a, b = part.split(":", 1)
            if a.lstrip("-").isdigit():
                pre.append((int(a), fnum(b)))
    return render_template("purchase_new.html", prods=[dict(p) for p in prods], pre=pre,
                           sups=db.execute("SELECT * FROM suppliers WHERE active=1 ORDER BY name").fetchall(),
                           br=int(request.args.get("branch") or 0) or scope_branch() or work_branch())


@app.route("/purchases/<int(signed=True):pid>", methods=["GET", "POST"])
@perm_required("purchases")
def purchase_view(pid):
    db = get_db()
    u = current_user()
    p = db.execute("""SELECT p.*, s.name AS supplier, s.phone AS sphone, s.address AS saddress, b.name AS branch
        FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id JOIN branches b ON b.id=p.branch_id
        WHERE p.id=?""", (pid,)).fetchone() or abort(404)
    if u["role"] != "admin" and p["branch_id"] != u["branch_id"]:
        abort(403)
    items = db.execute("""SELECT i.*, pr.name, pr.cost_price FROM purchase_items i JOIN products pr ON pr.id=i.product_id
        WHERE i.purchase_id=? ORDER BY i.id""", (pid,)).fetchall()
    total = round(sum(i["qty"] * i["unit_cost"] for i in items), 2)
    paid = db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE purchase_id=?", (pid,)).fetchone()[0]
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        if act == "receive" and p["status"] == "ordered":
            for i in items:
                q = fnum(f.get(f"rq_{i['id']}"), i["qty"])  # الكمية التي وصلت فعلًا
                c = fnum(f.get(f"rc_{i['id']}"), i["unit_cost"])
                db.execute("UPDATE purchase_items SET qty=?, unit_cost=? WHERE id=?", (q, c, i["id"]))
                if q > 0:
                    move_stock(db, i["product_id"], p["branch_id"], q, f"شراء — طلبية {pid}", u["id"])
                    if c > 0:
                        db.execute("UPDATE products SET cost_price=? WHERE id=?", (c, i["product_id"]))
            db.execute("UPDATE purchases SET status='received', received_at=? WHERE id=?", (now_str(), pid))
            amount = fnum(f.get("paid_now")) if has_perm("expenses") else 0
            if amount > 0:
                worker = u["role"] != "admin"
                db.execute("""INSERT INTO expenses(branch_id,day,category,description,amount,method,supplier_id,purchase_id,
                    created_by,created_at,from_cash,role) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (p["branch_id"], date.today().isoformat(), "شراء سلع (منتجات)",
                            f"طلبية {pid} — {p['supplier'] or ''}", amount, "cash" if worker else f.get("method", "cash"),
                            p["supplier_id"], pid, u["id"], now_str(), 1 if worker else 0, u["role"] if worker else None))
            audit("استلام سلعة", f"طلبية {pid} — {p['supplier'] or ''}", p["branch_id"])
            flash("تم استلام الطلبية: المخزون زاد، وسعر الشراء تحدّث", "ok")
        elif act == "pay":
            if u["role"] != "admin":
                abort(403)
            amount = fnum(f.get("amount"))
            if amount > 0:
                db.execute("""INSERT INTO expenses(branch_id,day,category,description,amount,method,supplier_id,purchase_id,
                    created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                           (p["branch_id"], date.today().isoformat(), "شراء سلع (منتجات)",
                            f"تسديد طلبية {pid} — {p['supplier'] or ''}", amount, f.get("method", "cash"),
                            p["supplier_id"], pid, u["id"], now_str()))
                flash("تم تسجيل الدفع للمورد", "ok")
        elif act == "cancel" and p["status"] == "ordered":
            db.execute("UPDATE purchases SET status='cancelled' WHERE id=?", (pid,))
            flash("أُلغيت الطلبية", "ok")
        elif act == "edit" and p["status"] == "ordered":
            for i in items:
                q = fnum(f.get(f"q_{i['id']}"), i["qty"])
                if q <= 0:
                    db.execute("DELETE FROM purchase_items WHERE id=?", (i["id"],))
                else:
                    db.execute("UPDATE purchase_items SET qty=?, unit_cost=? WHERE id=?",
                               (q, fnum(f.get(f"c_{i['id']}"), i["unit_cost"]), i["id"]))
            flash("تم حفظ الطلبية", "ok")
        db.commit()
        return redirect(url_for("purchase_view", pid=pid))
    return render_template("purchase_view.html", p=p, items=items, total=total, paid=paid,
                           now=datetime.now().strftime("%Y-%m-%d %H:%M"))


@app.route("/permissions", methods=["GET", "POST"])
@login_required("admin")
def permissions():
    """لوحة المديرة: تشغيل أو إيقاف كل مهمة لكل مكان في كل فرع."""
    db = get_db()
    if request.method == "POST":
        b, role, perm = request.form.get("branch_id"), request.form.get("role"), request.form.get("perm")
        on = 1 if request.form.get("enabled") == "1" else 0
        if role in PLACES and perm in PERM_LABELS and b:
            ex = db.execute("SELECT id FROM perms WHERE branch_id=? AND role=? AND perm=?", (b, role, perm)).fetchone()
            if ex:
                db.execute("UPDATE perms SET enabled=? WHERE id=?", (on, ex["id"]))
            else:
                db.execute("INSERT INTO perms(branch_id,role,perm,enabled) VALUES(?,?,?,?)", (b, role, perm, on))
            audit("صلاحيات", f"{'تشغيل' if on else 'إيقاف'} «{PERM_LABELS[perm]}» — {PLACES[role]} — {branch_name(int(b))}", int(b))
            db.commit()
        if request.headers.get("X-Requested-With") == "fetch":
            return {"ok": True, "enabled": on}
        return redirect(url_for("permissions", branch=b) + f"#b{b}")
    data = []
    for br in db.execute("SELECT * FROM branches WHERE active=1 ORDER BY id").fetchall():
        places = ["reception"] + [k for k in branch_depts(br["id"]) if k in ("laser", "beauty")]
        staff = {r["role"]: r["n"] for r in db.execute(
            "SELECT role, COUNT(*) n FROM users WHERE branch_id=? AND active=1 GROUP BY role", (br["id"],))}
        data.append(dict(b=br, places=places, staff=staff, perms={p: place_perms(br["id"], p) for p in places}))
    return render_template("permissions.html", data=data, PERMS=PERMS, PLACES=PLACES)


# ---------------------------------------------------------------- النسخ الاحتياطي
def backup_status():
    db = get_db()
    last = setting("backup_last")
    age = None
    if last:
        try:
            age = (datetime.now() - datetime.strptime(last, "%Y-%m-%d %H:%M:%S")).total_seconds() / 3600
        except ValueError:
            age = None
    return dict(last=last, age=age, err=setting("backup_error"), size=setting("backup_last_size"),
                dir=setting("backup_dir") or backup.default_dir(), dir2=setting("backup_dir2"),
                every=setting("backup_every_hours") or "6",
                warn=(age is None or age > 48) and not sync.NODE)


@app.route("/backup", methods=["GET", "POST"])
@login_required("admin")
def backup_page():
    db = get_db()
    if request.method == "POST":
        act = request.form.get("action")
        if act == "now":
            ok, msg = backup.run_backup(connect, DB_PATH, "يدوي")
            audit("نسخة احتياطية", "يدوية")
            db.commit()
            flash(("تمت النسخة الاحتياطية: " if ok else "فشلت النسخة: ") + msg, "ok" if ok else "err")
        elif act == "settings":
            for k in ("backup_dir", "backup_dir2"):
                db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, request.form.get(k, "").strip()))
            h = max(1, int(fnum(request.form.get("backup_every_hours"), 6)))
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('backup_every_hours',?)", (str(h),))
            db.commit()
            flash("تم حفظ إعدادات النسخ", "ok")
        elif act == "restore":
            name = os.path.basename(request.form.get("name", ""))
            path = os.path.join(backup_status()["dir"], name)
            if not os.path.exists(path):
                flash("الملف غير موجود", "err")
            else:
                backup.run_backup(connect, DB_PATH, "قبل الاسترجاع")
                with open(os.path.join(BASE_DIR, "restore_pending.txt"), "w", encoding="utf-8") as f:
                    f.write(path)
                audit("طلب استرجاع نسخة", name)
                db.commit()
                flash("سيُسترجع هذا اليوم عند إعادة تشغيل البرنامج. أعد تشغيل الحاسوب (أو البرنامج) الآن.", "ok")
        return redirect(url_for("backup_page"))
    st = backup_status()
    files = backup.list_backups(st["dir"])
    total = sum(f["size"] for f in files)
    dbsize = sum(os.path.getsize(DB_PATH + e) for e in ("", "-wal") if os.path.exists(DB_PATH + e))
    return render_template("backup.html", st=st, files=files, total=total, dbsize=dbsize,
                           pending=os.path.exists(os.path.join(BASE_DIR, "restore_pending.txt")))


@app.route("/backup/download/<name>")
@login_required("admin")
def backup_download(name):
    from flask import send_file
    path = os.path.join(backup_status()["dir"], os.path.basename(name))
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True)

# ---------------------------------------------------------------- الوظائف والغرف
@app.route("/branches/<int(signed=True):bid>/posts", methods=["POST"])
@login_required("admin")
def branch_posts(bid):
    db = get_db()
    pid = request.form.get("id")
    name = request.form.get("name", "").strip()
    dept = request.form.get("dept") if request.form.get("dept") in DEPTS else None
    if request.form.get("action") == "delete" and pid:
        used = db.execute("SELECT COUNT(*) n FROM employees WHERE post_id=?", (pid,)).fetchone()["n"]
        if used:
            db.execute("UPDATE posts SET active=0 WHERE id=?", (pid,))
            flash("الوظيفة مرتبطة بعمال، تم إيقافها بدل حذفها", "ok")
        else:
            db.execute("DELETE FROM posts WHERE id=? AND branch_id=?", (pid, bid))
            flash("تم الحذف", "ok")
    elif not name:
        flash("اكتب اسم الوظيفة أو الغرفة", "err")
    elif pid:
        db.execute("UPDATE posts SET name=?, dept=?, active=? WHERE id=? AND branch_id=?",
                   (name, dept, 1 if request.form.get("active", "1") == "1" else 0, pid, bid))
        flash("تم التعديل", "ok")
    else:
        db.execute("INSERT INTO posts(branch_id,name,dept) VALUES(?,?,?)", (bid, name, dept))
        flash("تمت الإضافة", "ok")
    db.commit()
    return redirect(url_for("branch_view", bid=bid) + "#posts")


# ---------------------------------------------------------------- خطط الجلسات (مواعيد بحصص متعددة)
def plan_data(plan_id):
    db = get_db()
    p = db.execute("""SELECT pl.*, c.name AS client, c.phone, b.name AS branch, s.name AS service, po.name AS room
        FROM plans pl JOIN clients c ON c.id=pl.client_id JOIN branches b ON b.id=pl.branch_id
        LEFT JOIN services s ON s.id=pl.service_id LEFT JOIN posts po ON po.id=pl.post_id
        WHERE pl.id=?""", (plan_id,)).fetchone()
    if not p:
        abort(404)
    sessions = db.execute("""SELECT a.*, po.name AS room,
        (SELECT COUNT(*) FROM charges ch WHERE ch.appointment_id=a.id AND ch.status='pending') AS pending_charge
        FROM appointments a LEFT JOIN posts po ON po.id=a.post_id
        WHERE a.plan_id=? ORDER BY a.session_no, a.id""", (plan_id,)).fetchall()
    st = dict(
        n=len(sessions),
        done=sum(1 for x in sessions if x["status"] == "done"),
        sum_price=sum(x["price"] or 0 for x in sessions),
        paid=sum(x["price"] or 0 for x in sessions if x["paid"]),
        paid_n=sum(1 for x in sessions if x["paid"]),
    )
    total = p["total_price"] if p["price_mode"] == "total" else st["sum_price"]
    st["total"] = total
    st["remaining"] = round(total - st["paid"], 2)
    return p, sessions, st


def check_plan_access(p):
    u = current_user()
    if u["role"] != "admin" and p["branch_id"] != u["branch_id"]:
        abort(403)
    if u["role"] in ("laser", "beauty") and p["dept"] != u["role"]:
        abort(403)


def renumber(db, plan_id):
    for i, r in enumerate(db.execute("SELECT id FROM appointments WHERE plan_id=? ORDER BY session_no, id",
                                     (plan_id,)).fetchall(), 1):
        db.execute("UPDATE appointments SET session_no=? WHERE id=?", (i, r["id"]))


@app.route("/plans")
@login_required()
def plans():
    db = get_db()
    u = current_user()
    br = scope_branch()
    q = """SELECT pl.*, c.name AS client, c.phone, b.name AS branch, s.name AS service,
        (SELECT COUNT(*) FROM appointments a WHERE a.plan_id=pl.id) AS n,
        (SELECT COUNT(*) FROM appointments a WHERE a.plan_id=pl.id AND a.status='done') AS done,
        (SELECT COALESCE(SUM(price),0) FROM appointments a WHERE a.plan_id=pl.id) AS sum_price,
        (SELECT COALESCE(SUM(price),0) FROM appointments a WHERE a.plan_id=pl.id AND a.paid=1) AS paid,
        (SELECT MIN(start_at) FROM appointments a WHERE a.plan_id=pl.id AND a.status='scheduled'
            AND a.start_at IS NOT NULL) AS next_at
        FROM plans pl JOIN clients c ON c.id=pl.client_id JOIN branches b ON b.id=pl.branch_id
        LEFT JOIN services s ON s.id=pl.service_id WHERE 1=1"""
    args = []
    if br:
        q += " AND pl.branch_id=?"
        args.append(br)
    if u["role"] in ("laser", "beauty"):
        q += " AND pl.dept=?"
        args.append(u["role"])
    status = request.args.get("status", "active")
    if status in PLAN_STATUS:
        q += " AND pl.status=?"
        args.append(status)
    s_ = request.args.get("q", "").strip()
    if s_:
        q += " AND (c.name LIKE ? OR c.phone LIKE ? OR pl.title LIKE ?)"
        args += [f"%{s_}%"] * 3
    rows = db.execute(q + " ORDER BY pl.id DESC LIMIT 300", args).fetchall()
    return render_template("plans.html", rows=rows, br=br, status=status, s=s_)


@app.route("/plans/new", methods=["GET", "POST"])
@perm_required("plans")
def plan_new():
    db = get_db()
    u = current_user()
    br = u["branch_id"] or int(request.values.get("branch_id") or work_branch())
    if request.method == "POST":
        f = request.form
        dept = u["role"] if u["role"] in ("laser", "beauty") else f.get("dept")
        if dept not in branch_depts(br):
            flash("هذا القسم غير موجود في هذا الفرع", "err")
            return redirect(url_for("plan_new"))
        if not f.get("client_id"):
            flash("اختر الزبون", "err")
            return redirect(url_for("plan_new"))
        n = max(1, min(100, int(fnum(f.get("n"), 1))))
        mode = "total" if f.get("price_mode") == "total" else "session"
        if price_locked(u):
            mode = "session"
            f = f.copy()
            f["session_price"] = str(service_price(f.get("service_id")))
        if mode == "total":
            total = fnum(f.get("total_price"))
            prices = [round(total / n, 2)] * n
            prices[-1] = round(total - sum(prices[:-1]), 2)
        else:
            total = 0
            prices = [fnum(f.get("session_price"))] * n
        srv = f.get("service_id") or None
        title = f.get("title", "").strip()
        if not title and srv:
            r = db.execute("SELECT name FROM services WHERE id=?", (srv,)).fetchone()
            title = r["name"] if r else ""
        title = title or f"{DEPTS.get(dept)} — {n} حصص"
        post = f.get("post_id") or None
        pid = db.execute("""INSERT INTO plans(client_id,branch_id,dept,service_id,post_id,title,total_price,price_mode,
            notes,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                         (int(f["client_id"]), br, dept, srv, post, title, total, mode,
                          f.get("notes", "").strip(), u["id"], now_str())).lastrowid
        start = None
        if f.get("first_date"):
            try:
                start = datetime.strptime(f"{f['first_date']} {f.get('time') or '09:00'}", "%Y-%m-%d %H:%M")
            except ValueError:
                start = None
        step = int(fnum(f.get("interval"), 0))
        for i in range(n):
            at = None
            if start and (i == 0 or step > 0):
                at = (start + timedelta(days=step * i)).strftime("%Y-%m-%d %H:%M")
            db.execute("""INSERT INTO appointments(client_id,branch_id,dept,service_id,start_at,status,created_by,
                created_at,plan_id,session_no,price,paid,post_id) VALUES(?,?,?,?,?,'scheduled',?,?,?,?,?,0,?)""",
                       (int(f["client_id"]), br, dept, srv, at, u["id"], now_str(), pid, i + 1, prices[i], post))
        db.commit()
        flash(f"تم إنشاء خطة من {n} حصص", "ok")
        return redirect(url_for("plan_view", pid=pid))
    sel_client = None
    if request.args.get("client_id"):
        sel_client = db.execute("SELECT id,name,phone FROM clients WHERE id=?", (request.args["client_id"],)).fetchone()
    return render_template("plan_new.html", br=br, depts=branch_depts(br), services=services_for(br),
                           posts=posts_for(br), sel_client=sel_client)


@app.route("/plans/<int(signed=True):pid>", methods=["GET", "POST"])
@login_required()
def plan_view(pid):
    db = get_db()
    u = current_user()
    p, sessions, st = plan_data(pid)
    check_plan_access(p)
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        need("collect" if act == "pay" else "plans")
        if price_locked(u) and act in ("distribute",):
            abort(403)
        if act == "plan":
            mode = "total" if f.get("price_mode") == "total" else "session"
            if price_locked(u):
                mode, f = p["price_mode"], f.copy()
                f["total_price"] = str(p["total_price"])
            db.execute("UPDATE plans SET title=?, total_price=?, price_mode=?, notes=?, status=?, post_id=? WHERE id=?",
                       (f.get("title", "").strip() or p["title"], fnum(f.get("total_price")), mode,
                        f.get("notes", "").strip(), f.get("status") if f.get("status") in PLAN_STATUS else p["status"],
                        f.get("post_id") or None, pid))
            if f.get("status") == "cancelled":
                db.execute("UPDATE appointments SET status='cancelled' WHERE plan_id=? AND status='scheduled'", (pid,))
            flash("تم حفظ الخطة", "ok")
        elif act == "distribute":
            total = fnum(f.get("total_price"), p["total_price"])
            unpaid = [x for x in sessions if not x["paid"]]
            rest = round(total - st["paid"], 2)
            if unpaid and rest >= 0:
                each = round(rest / len(unpaid), 2)
                for i, x in enumerate(unpaid):
                    v = each if i < len(unpaid) - 1 else round(rest - each * (len(unpaid) - 1), 2)
                    db.execute("UPDATE appointments SET price=? WHERE id=?", (v, x["id"]))
                db.execute("UPDATE plans SET total_price=?, price_mode='total' WHERE id=?", (total, pid))
                flash("تم توزيع السعر على الحصص غير المدفوعة", "ok")
            else:
                flash("لا توجد حصص غير مدفوعة أو المبلغ أقل من المدفوع", "err")
        elif act == "add":
            k = max(1, min(50, int(fnum(f.get("count"), 1))))
            price = fnum(f.get("price"), sessions[-1]["price"] if sessions else 0)
            if price_locked(u):
                price = (sessions[-1]["price"] if sessions else 0) or service_price(p["service_id"])
            last = max([x["session_no"] or 0 for x in sessions] or [0])
            for i in range(k):
                db.execute("""INSERT INTO appointments(client_id,branch_id,dept,service_id,start_at,status,created_by,
                    created_at,plan_id,session_no,price,paid,post_id) VALUES(?,?,?,?,NULL,'scheduled',?,?,?,?,?,0,?)""",
                           (p["client_id"], p["branch_id"], p["dept"], p["service_id"], u["id"], now_str(), pid,
                            last + i + 1, price, p["post_id"]))
            if p["status"] == "done":
                db.execute("UPDATE plans SET status='active' WHERE id=?", (pid,))
            flash(f"تمت إضافة {k} حصة", "ok")
        elif act == "save":
            for x in sessions:
                k = str(x["id"])
                d_, t_ = f.get(f"d_{k}", ""), f.get(f"t_{k}", "")
                at = f"{d_} {t_ or '09:00'}" if d_ else None
                stt = f.get(f"s_{k}") if f.get(f"s_{k}") in APPT_STATUS else x["status"]
                price = x["price"] if (x["paid"] or price_locked(u)) else fnum(f.get(f"p_{k}"), x["price"] or 0)
                if at != (x["start_at"] or None):
                    db.execute("UPDATE appointments SET sms_sent_at=NULL WHERE id=?", (x["id"],))
                db.execute("UPDATE appointments SET start_at=?, status=?, price=?, post_id=? WHERE id=?",
                           (at, stt, price, f.get(f"r_{k}") or None, x["id"]))
            if p["price_mode"] == "session":
                db.execute("UPDATE plans SET total_price=(SELECT COALESCE(SUM(price),0) FROM appointments WHERE plan_id=?) WHERE id=?",
                           (pid, pid))
            left = db.execute("SELECT COUNT(*) n FROM appointments WHERE plan_id=? AND status='scheduled'", (pid,)).fetchone()["n"]
            if not left and p["status"] == "active":
                db.execute("UPDATE plans SET status='done' WHERE id=?", (pid,))
            flash("تم حفظ الحصص", "ok")
        elif act == "pay":
            if not can_collect(u):
                abort(403)
            ids = [int(i) for i in f.getlist("sel") if i.lstrip("-").isdigit()]
            chosen = [x for x in sessions if x["id"] in ids and not x["paid"]]
            if not chosen:
                flash("حدد الحصص غير المدفوعة التي يدفعها الزبون", "err")
            else:
                amount = round(sum(x["price"] or 0 for x in chosen), 2)
                if f.get("amount") and not price_locked(u):
                    amount = fnum(f.get("amount"), amount)
                nums = "، ".join(str(x["session_no"]) for x in chosen)
                pay_id = make_payment(db, p["branch_id"], p["client_id"], amount, f.get("method", "cash"), "service",
                                      f"{p['title']} — الحصص: {nums}", u["id"], dept=p["dept"])
                for x in chosen:
                    db.execute("UPDATE appointments SET paid=1, payment_id=? WHERE id=?", (pay_id, x["id"]))
                    db.execute("UPDATE charges SET status='paid', payment_id=? WHERE appointment_id=? AND status='pending'",
                               (pay_id, x["id"]))
                db.commit()
                flash(f"تم تسجيل دفع {len(chosen)} حصة في الصندوق", "ok")
                return redirect(url_for("receipt", pid=pay_id))
        elif act == "send":
            ids = [int(i) for i in f.getlist("sel") if i.lstrip("-").isdigit()]
            n_ = 0
            for x in sessions:
                if x["id"] in ids and not x["paid"] and not x["pending_charge"] and (x["price"] or 0) > 0:
                    db.execute("""INSERT INTO charges(branch_id,client_id,dept,service_id,appointment_id,description,
                        amount,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                               (p["branch_id"], p["client_id"], p["dept"], p["service_id"], x["id"],
                                f"{p['title']} — حصة {x['session_no']}", x["price"], u["id"], now_str()))
                    n_ += 1
            flash(f"تم إرسال {n_} حصة إلى الاستقبال للتحصيل" if n_ else "لا توجد حصص صالحة للإرسال", "ok" if n_ else "err")
        db.commit()
        return redirect(url_for("plan_view", pid=pid))
    return render_template("plan_view.html", p=p, sessions=sessions, st=st, posts=posts_for(p["branch_id"]))


@app.route("/sessions/<int(signed=True):aid>/delete", methods=["POST"])
@perm_required("plans")
def session_delete(aid):
    db = get_db()
    a = db.execute("SELECT * FROM appointments WHERE id=?", (aid,)).fetchone() or abort(404)
    if not a["plan_id"]:
        abort(400)
    p, _, _ = plan_data(a["plan_id"])
    check_plan_access(p)
    if a["paid"]:
        flash("لا يمكن حذف حصة مدفوعة. ألغِ الدفعة أولًا من الوصل.", "err")
    else:
        db.execute("UPDATE charges SET status='cancelled' WHERE appointment_id=? AND status='pending'", (aid,))
        audit("حذف حصة", f"{p['title']} — حصة {a['session_no']}", a["branch_id"])
        db.execute("DELETE FROM appointments WHERE id=?", (aid,))
        renumber(db, a["plan_id"])
        if p["price_mode"] == "session":
            db.execute("UPDATE plans SET total_price=(SELECT COALESCE(SUM(price),0) FROM appointments WHERE plan_id=?) WHERE id=?",
                       (a["plan_id"], a["plan_id"]))
        db.commit()
        flash("تم حذف الحصة", "ok")
    return redirect(url_for("plan_view", pid=a["plan_id"]))

# ---------------------------------------------------------------- الفروع
@app.route("/branches", methods=["GET", "POST"])
@login_required("admin")
def branches():
    db = get_db()
    if request.method == "POST":
        bid = request.form.get("id")
        name = request.form.get("name", "").strip()
        kinds = [k for k in request.form.getlist("depts") if k in DEPTS]
        if not name:
            flash("اسم الفرع مطلوب", "err")
            return redirect(url_for("branches"))
        if "reception" not in kinds:
            kinds.append("reception")
        vals = (name, request.form.get("address", "").strip(), request.form.get("phone", "").strip(),
                1 if request.form.get("active", "1") == "1" else 0)
        if bid:
            db.execute("UPDATE branches SET name=?,address=?,phone=?,active=? WHERE id=?", vals + (bid,))
            db.execute("DELETE FROM departments WHERE branch_id=?", (bid,))
            flash("تم تعديل الفرع", "ok")
        else:
            bid = db.execute("INSERT INTO branches(name,address,phone,active) VALUES(?,?,?,?)", vals).lastrowid
            flash("تمت إضافة الفرع. أضف له مستخدمين من صفحة المستخدمين.", "ok")
        coll = set(request.form.getlist("collect"))
        for k in kinds:
            db.execute("INSERT INTO departments(branch_id,kind,can_collect) VALUES(?,?,?)",
                       (bid, k, 1 if k in coll else 0))
        db.commit()
        return redirect(url_for("branches"))
    rows = db.execute("SELECT * FROM branches ORDER BY active DESC, id").fetchall()
    depts, collect = {}, {}
    for r in db.execute("SELECT * FROM departments"):
        depts.setdefault(r["branch_id"], []).append(r["kind"])
        if r["can_collect"]:
            collect.setdefault(r["branch_id"], []).append(r["kind"])
    edit = db.execute("SELECT * FROM branches WHERE id=?", (request.args.get("edit"),)).fetchone() \
        if request.args.get("edit") else None
    last_sync = {r["key"][10:]: r["value"] for r in db.execute("SELECT * FROM settings WHERE key LIKE 'sync_last_%'")}
    return render_template("branches.html", rows=rows, depts=depts, edit=edit, last_sync=last_sync,
                           collect=collect, edit_collect=collect.get(edit["id"], []) if edit else [],
                           edit_depts=depts.get(edit["id"], []) if edit else ["reception"])


@app.route("/branches/<int(signed=True):bid>")
@login_required("admin")
def branch_view(bid):
    """لوحة فرع واحد في الحاسوب المركزي: صندوقه، مخزونه، مواعيده."""
    db = get_db()
    b = db.execute("SELECT * FROM branches WHERE id=?", (bid,)).fetchone() or abort(404)
    today = date.today()
    t = today.isoformat()
    m1 = today.replace(day=1).isoformat()

    def total(d1, d2):
        return db.execute("""SELECT COALESCE(SUM(amount),0) s, COUNT(*) n FROM payments WHERE branch_id=?
            AND cancelled=0 AND substr(created_at,1,10) BETWEEN ? AND ?""", (bid, d1, d2)).fetchone()
    day, month = total(t, t), total(m1, t)
    by_kind = db.execute("""SELECT kind, SUM(amount) s FROM payments WHERE branch_id=? AND cancelled=0
        AND substr(created_at,1,10) BETWEEN ? AND ? GROUP BY kind""", (bid, m1, t)).fetchall()
    pending = db.execute("""SELECT ch.*, c.name AS client FROM charges ch LEFT JOIN clients c ON c.id=ch.client_id
        WHERE ch.branch_id=? AND ch.status='pending' ORDER BY ch.id""", (bid,)).fetchall()
    pays = db.execute("""SELECT p.*, c.name AS client, us.full_name AS by_name FROM payments p
        LEFT JOIN clients c ON c.id=p.client_id LEFT JOIN users us ON us.id=p.received_by
        WHERE p.branch_id=? AND substr(p.created_at,1,10)=? ORDER BY p.id DESC""", (bid, t)).fetchall()
    appts = db.execute("""SELECT a.*, c.name AS client, c.phone, s.name AS service, s.price AS sprice, b.name AS branch,
           po.name AS room, pl.title AS plan_title, (SELECT COUNT(*) FROM appointments x WHERE x.plan_id=a.plan_id) AS plan_n FROM appointments a
        JOIN clients c ON c.id=a.client_id LEFT JOIN services s ON s.id=a.service_id
        JOIN branches b ON b.id=a.branch_id LEFT JOIN posts po ON po.id=a.post_id
        LEFT JOIN plans pl ON pl.id=a.plan_id
        WHERE a.branch_id=? AND substr(a.start_at,1,10)=? ORDER BY a.start_at""", (bid, t)).fetchall()
    stock = db.execute("""SELECT p.id, p.name, p.category, p.price, p.expiry, COALESCE(s.qty,0) qty,
        COALESCE(s.min_qty,0) min_qty FROM products p
        LEFT JOIN stock s ON s.product_id=p.id AND s.branch_id=? WHERE p.active=1
        ORDER BY p.category, p.name""", (bid,)).fetchall()
    stock_value = sum(r["qty"] * r["price"] for r in stock if r["qty"] > 0)
    staff = db.execute("SELECT * FROM users WHERE branch_id=? AND active=1", (bid,)).fetchall()
    workers = db.execute("""SELECT e.*, a.status AS today_status, a.check_in, po.name AS post FROM employees e
        LEFT JOIN attendance a ON a.employee_id=e.id AND a.day=? LEFT JOIN posts po ON po.id=e.post_id
        WHERE e.branch_id=? AND e.active=1
        ORDER BY e.name""", (t, bid)).fetchall()
    msum = month_summary(bid, today.strftime("%Y-%m"))
    return render_template("branch_view.html", b=b, day=day, month=month, by_kind=by_kind, pending=pending,
                           pays=pays, appts=appts, stock=stock, stock_value=stock_value, staff=staff,
                           alerts=stock_alerts(bid), depts=branch_depts(bid),
                           workers=workers, msum=msum, posts=posts_for(bid, only_active=False),
                           post_counts={r["post_id"]: r["n"] for r in db.execute(
                               "SELECT post_id, COUNT(*) n FROM employees WHERE branch_id=? AND active=1 GROUP BY post_id",
                               (bid,))})


# ---------------------------------------------------------------- الخدمات
@app.route("/services", methods=["GET", "POST"])
@login_required("admin")
def services():
    db = get_db()
    if request.method == "POST":
        sid = request.form.get("id")
        vals = (request.form.get("name", "").strip(), request.form.get("kind"), request.form.get("dept"),
                fnum(request.form.get("price")), request.form.get("branch_id") or None,
                1 if request.form.get("active", "1") == "1" else 0, int(fnum(request.form.get("duration"), 30)) or 30)
        if not vals[0]:
            flash("اسم الخدمة مطلوب", "err")
        elif sid:
            old = db.execute("SELECT price FROM services WHERE id=?", (sid,)).fetchone()
            if old and old["price"] != vals[3]:
                audit("تغيير سعر خدمة", f"{vals[0]}: {old['price']:g} ← {vals[3]:g}")
            db.execute("UPDATE services SET name=?,kind=?,dept=?,price=?,branch_id=?,active=?,duration=? WHERE id=?", vals + (sid,))
            flash("تم التعديل", "ok")
        else:
            db.execute("INSERT INTO services(name,kind,dept,price,branch_id,active,duration) VALUES(?,?,?,?,?,?,?)", vals)
            flash("تمت الإضافة", "ok")
        db.commit()
        return redirect(url_for("services"))
    rows = db.execute("""SELECT s.*, b.name AS branch FROM services s LEFT JOIN branches b ON b.id=s.branch_id
        ORDER BY s.active DESC, s.dept, s.name""").fetchall()
    edit = db.execute("SELECT * FROM services WHERE id=?", (request.args.get("edit"),)).fetchone() \
        if request.args.get("edit") else None
    return render_template("services.html", rows=rows, edit=edit)


# ---------------------------------------------------------------- المستخدمون
@app.route("/users", methods=["GET", "POST"])
@login_required("admin")
def users():
    db = get_db()
    if request.method == "POST":
        uid = request.form.get("id")
        role = request.form.get("role")
        br = request.form.get("branch_id") or None
        if role != "admin" and not br:
            flash("اختر الفرع لهذا المستخدم", "err")
            return redirect(url_for("users"))
        if role in ("laser", "beauty") and role not in branch_depts(int(br)):
            flash("هذا القسم غير موجود في الفرع المختار", "err")
            return redirect(url_for("users"))
        if role == "admin":
            br = None
        if uid:
            db.execute("UPDATE users SET full_name=?, role=?, branch_id=?, active=? WHERE id=?",
                       (request.form.get("full_name"), role, br,
                        1 if request.form.get("active", "1") == "1" else 0, uid))
            if request.form.get("password"):
                db.execute("UPDATE users SET pw_hash=? WHERE id=?",
                           (generate_password_hash(request.form["password"]), uid))
            flash("تم التعديل", "ok")
        else:
            un = request.form.get("username", "").strip()
            if not un or not request.form.get("password"):
                flash("اسم المستخدم وكلمة المرور مطلوبان", "err")
                return redirect(url_for("users"))
            try:
                db.execute("INSERT INTO users(username,pw_hash,full_name,role,branch_id) VALUES(?,?,?,?,?)",
                           (un, generate_password_hash(request.form["password"]),
                            request.form.get("full_name"), role, br))
                flash("تمت إضافة المستخدم", "ok")
            except sqlite3.IntegrityError:
                flash("اسم المستخدم موجود مسبقًا", "err")
        db.commit()
        return redirect(url_for("users"))
    rows = db.execute("""SELECT u.*, b.name AS branch FROM users u LEFT JOIN branches b ON b.id=u.branch_id
        ORDER BY u.active DESC, u.branch_id, u.role""").fetchall()
    edit = db.execute("SELECT * FROM users WHERE id=?", (request.args.get("edit"),)).fetchone() \
        if request.args.get("edit") else None
    return render_template("users.html", rows=rows, edit=edit)


# ---------------------------------------------------------------- الإعدادات وSMS
@app.route("/settings", methods=["GET", "POST"])
@login_required("admin")
def settings():
    db = get_db()
    if request.method == "POST":
        for k in DEFAULT_SETTINGS:
            if k == "sms_enabled":
                v = "1" if request.form.get("sms_enabled") else "0"
            elif k == "stock_sms_enabled":
                v = "1" if request.form.get("stock_sms_enabled") else "0"
            elif k in ("consent_body", "cert_body") and not request.form.get(k, "").strip():
                continue
            elif k in ("stamp_img", "signature_img", "img_ver"):
                continue  # تُرفع من نموذج الصور
            elif k in ("sms_confirm", "sms_birthday"):
                v = "1" if request.form.get(k) else "0"
            elif k == "last_birthday_run":
                continue
            elif k in ("backup_dir", "backup_dir2", "backup_every_hours"):
                continue  # من صفحة النسخ الاحتياطي
            elif k == "staff_can_edit_prices":
                v = "1" if request.form.get(k) else "0"
            elif k == "director_branch":
                v = request.form.get(k, "") if request.form.get(k, "").isdigit() else ""
            elif k == "weekly_off":
                v = ",".join(x for x in request.form.getlist("weekly_off") if x in "0123456")
            elif k == "paid_statuses":
                v = ",".join(x for x in request.form.getlist("paid_statuses") if x in ATT_STATUS)
            elif k == "deduct_absence":
                v = "1" if request.form.get("deduct_absence") else "0"
            elif k == "last_stock_sms":
                continue
            elif k == "sms_depts":
                v = ",".join(request.form.getlist("sms_depts"))
            elif k == "sms_pass" and not request.form.get("sms_pass"):
                continue
            else:
                v = request.form.get(k, "").strip()
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, v))
        db.commit()
        flash("تم حفظ الإعدادات", "ok")
        return redirect(url_for("settings"))
    s = {r["key"]: r["value"] for r in db.execute("SELECT * FROM settings")}
    return render_template("settings.html", s=s)


def norm_phone(p):
    p = "".join(ch for ch in (p or "") if ch.isdigit() or ch == "+")
    if p.startswith("00"):
        p = "+" + p[2:]
    if p.startswith("0") and len(p) == 10:
        p = "+213" + p[1:]
    elif p.startswith("213"):
        p = "+" + p
    return p


def send_sms(con, phone, message):
    """يرسل الرسالة عبر بوابة SMS (تطبيق SMS Gateway على هاتف أندرويد أو خدمة متوافقة)."""
    s = {r["key"]: r["value"] for r in con.execute("SELECT * FROM settings")}
    if s.get("sms_enabled") != "1" or not s.get("sms_url"):
        return False, "بوابة SMS غير مفعلة"
    body = json.dumps({"message": message, "phoneNumbers": [norm_phone(phone)]}).encode("utf-8")
    req = urlreq.Request(s["sms_url"], data=body, method="POST",
                         headers={"Content-Type": "application/json"})
    if s.get("sms_user"):
        tok = base64.b64encode(f"{s['sms_user']}:{s.get('sms_pass', '')}".encode()).decode()
        req.add_header("Authorization", "Basic " + tok)
    try:
        with urlreq.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300, r.read(500).decode("utf-8", "replace")
    except Exception as e:
        return False, str(e)[:300]


def reminder_text(con, a):
    s = {r["key"]: r["value"] for r in con.execute("SELECT * FROM settings")}
    dt = datetime.strptime(a["start_at"][:16], "%Y-%m-%d %H:%M")
    try:
        return s["sms_template"].format(name=a["client"], center=s["center_name"], branch=a["branch"],
                                        date=dt.strftime("%d/%m/%Y"), time=dt.strftime("%H:%M"))
    except (KeyError, IndexError, ValueError):
        return s["sms_template"]


def due_reminders(con):
    s = {r["key"]: r["value"] for r in con.execute("SELECT * FROM settings")}
    hours = fnum(s.get("sms_hours_before"), 24)
    depts = [d for d in (s.get("sms_depts") or "").split(",") if d]
    if not depts:
        return []
    now = datetime.now()
    q = f"""SELECT a.*, c.name AS client, c.phone, b.name AS branch FROM appointments a
        JOIN clients c ON c.id=a.client_id JOIN branches b ON b.id=a.branch_id
        WHERE a.status='scheduled' AND a.sms_sent_at IS NULL AND c.phone<>''
        AND a.dept IN ({','.join('?' * len(depts))}) AND a.start_at > ? AND a.start_at <= ?
        ORDER BY a.start_at"""
    return con.execute(q, depts + [now.strftime("%Y-%m-%d %H:%M"),
                                   (now + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")]).fetchall()


def send_reminder(con, a):
    msg = reminder_text(con, a)
    ok, resp = send_sms(con, a["phone"], msg)
    con.execute("INSERT INTO sms_log(appointment_id,phone,message,status,response,created_at) VALUES(?,?,?,?,?,?)",
                (a["id"], a["phone"], msg, "sent" if ok else "failed", resp, now_str()))
    if ok:
        con.execute("UPDATE appointments SET sms_sent_at=? WHERE id=?", (now_str(), a["id"]))
    con.commit()
    return ok


def stock_sms_check():
    """مرة في اليوم (بعد الساعة 9 صباحًا) يرسل للمدير رسالة بالمنتجات التي قاربت على النفاد."""
    if setting("stock_sms_enabled") != "1" or not setting("manager_phone"):
        return
    today = date.today().isoformat()
    if setting("last_stock_sms") == today or datetime.now().hour < 9:
        return
    db = get_db()
    rows = stock_alerts(None)
    db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('last_stock_sms',?)", (today,))
    db.commit()
    if not rows:
        return
    parts = []
    for r in rows[:8]:
        tag = "انتهت الصلاحية" if r["expired"] else ("نفد" if r["out"] else (f"بقي {r['qty']:g}" if r["low"] else "صلاحية قريبة"))
        parts.append(f"{r['name']} ({r['branch']}): {tag}")
    msg = f"{setting('center_name')} - تنبيه مخزون ({len(rows)}): " + "؛ ".join(parts)
    if len(rows) > 8:
        msg += " ..."
    ok, resp = send_sms(db, setting("manager_phone"), msg)
    db.execute("INSERT INTO sms_log(appointment_id,phone,message,status,response,created_at) VALUES(NULL,?,?,?,?,?)",
               (setting("manager_phone"), msg, "sent" if ok else "failed", resp, now_str()))
    db.commit()



def appt_duration(service_id):
    r = get_db().execute("SELECT duration FROM services WHERE id=?", (service_id,)).fetchone() if service_id else None
    return (r["duration"] if r and r["duration"] else 30)


def room_conflicts(db, post_id, start_at, minutes, exclude_id=None):
    """المواعيد في نفس الغرفة التي يتداخل وقتها مع الموعد الجديد."""
    try:
        s0 = datetime.strptime(start_at[:16], "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return []
    e0 = s0 + timedelta(minutes=minutes)
    rows = db.execute("""SELECT a.*, c.name AS client, COALESCE(s.duration,30) AS dur FROM appointments a
        JOIN clients c ON c.id=a.client_id LEFT JOIN services s ON s.id=a.service_id
        WHERE a.post_id=? AND substr(a.start_at,1,10)=? AND a.status IN ('scheduled','done') AND a.id IS NOT ?""",
                      (post_id, start_at[:10], exclude_id)).fetchall()
    out = []
    for r in rows:
        s1 = datetime.strptime(r["start_at"][:16], "%Y-%m-%d %H:%M")
        if s1 < e0 and s0 < s1 + timedelta(minutes=r["dur"]):
            out.append(r)
    return out


@app.route("/calendar")
@perm_required("calendar")
def calendar():
    """جدول أسبوعي لكل غرفة."""
    db = get_db()
    u = current_user()
    br = u["branch_id"] or scope_branch() or work_branch()
    try:
        d0 = datetime.strptime(request.args.get("week", ""), "%Y-%m-%d").date()
    except ValueError:
        d0 = date.today()
    start = d0 - timedelta(days=(d0.weekday() - 5) % 7)  # الأسبوع يبدأ يوم السبت
    days = [start + timedelta(days=i) for i in range(7)]
    rooms = list(posts_for(br)) + [{"id": None, "name": "بدون غرفة"}]
    q = """SELECT a.*, c.name AS client, s.name AS service, COALESCE(s.duration,30) AS dur, pl.title AS plan_title
        FROM appointments a JOIN clients c ON c.id=a.client_id LEFT JOIN services s ON s.id=a.service_id
        LEFT JOIN plans pl ON pl.id=a.plan_id
        WHERE a.branch_id=? AND substr(a.start_at,1,10) BETWEEN ? AND ? AND a.status<>'cancelled'"""
    args = [br, days[0].isoformat(), days[-1].isoformat()]
    if u["role"] in ("laser", "beauty"):
        q += " AND a.dept=?"
        args.append(u["role"])
    grid = {}
    for a in db.execute(q + " ORDER BY a.start_at", args).fetchall():
        grid.setdefault((a["post_id"], a["start_at"][:10]), []).append(a)
    used = {k[0] for k in grid}
    if u["role"] in ("laser", "beauty"):
        rooms = [r for r in rooms if r["id"] in used or (r["id"] and dict(r).get("dept") == u["role"])]
    return render_template("calendar.html", days=days, rooms=rooms, grid=grid, br=br,
                           prev=(start - timedelta(days=7)).isoformat(), next=(start + timedelta(days=7)).isoformat())


# ---------------------------------------------------------------- رسائل SMS: تأكيد الحجز، عيد الميلاد، الرسائل الجماعية
def sms_fill(tpl, **kw):
    try:
        return tpl.format(**kw)
    except (KeyError, IndexError, ValueError):
        return tpl


def sms_extra_jobs(con):
    s = {r["key"]: r["value"] for r in con.execute("SELECT * FROM settings")}
    if s.get("sms_enabled") != "1":
        return
    now = datetime.now()
    # 1) تأكيد الحجز
    if s.get("sms_confirm") == "1":
        rows = con.execute("""SELECT a.*, c.name AS client, c.phone, b.name AS branch FROM appointments a
            JOIN clients c ON c.id=a.client_id JOIN branches b ON b.id=a.branch_id
            WHERE a.confirm_sent_at IS NULL AND a.status='scheduled' AND a.start_at > ? AND c.phone<>''
            AND a.created_at >= ? AND (a.plan_id IS NULL OR a.session_no=1) LIMIT 20""",
                           (now.strftime("%Y-%m-%d %H:%M"), (now - timedelta(days=2)).strftime("%Y-%m-%d"))).fetchall()
        for a in rows:
            dt = datetime.strptime(a["start_at"][:16], "%Y-%m-%d %H:%M")
            msg = sms_fill(s.get("sms_confirm_template", ""), name=a["client"], center=s.get("center_name"),
                           branch=a["branch"], date=dt.strftime("%d/%m/%Y"), time=dt.strftime("%H:%M"))
            ok, resp = send_sms(con, a["phone"], msg)
            con.execute("INSERT INTO sms_log(appointment_id,phone,message,status,response,created_at) VALUES(?,?,?,?,?,?)",
                        (a["id"], a["phone"], msg, "sent" if ok else "failed", resp, now_str()))
            con.execute("UPDATE appointments SET confirm_sent_at=? WHERE id=?", (now_str(), a["id"]))
            con.commit()
    # 2) تهنئة عيد الميلاد مرة في اليوم بعد العاشرة صباحًا
    today = date.today().isoformat()
    if s.get("sms_birthday") == "1" and s.get("last_birthday_run") != today and now.hour >= 10:
        con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('last_birthday_run',?)", (today,))
        con.commit()
        for c in con.execute("""SELECT name, phone FROM clients WHERE phone<>'' AND birth_date IS NOT NULL
                AND substr(birth_date,6,5)=? LIMIT 300""", (today[5:],)).fetchall():
            con.execute("INSERT INTO sms_log(phone,message,status,created_at) VALUES(?,?,'queued',?)",
                        (c["phone"], sms_fill(s.get("sms_birthday_template", ""), name=c["name"],
                                              center=s.get("center_name")), now_str()))
        con.commit()
    # 3) إرسال الرسائل المنتظرة (الجماعية وأعياد الميلاد): 15 رسالة كل دقيقة
    for q in con.execute("SELECT * FROM sms_log WHERE status='queued' ORDER BY id LIMIT 15").fetchall():
        ok, resp = send_sms(con, q["phone"], q["message"])
        con.execute("UPDATE sms_log SET status=?, response=?, created_at=? WHERE id=?",
                    ("sent" if ok else "failed", resp, now_str(), q["id"]))
        con.commit()
        time.sleep(2)


@app.route("/sms/campaign", methods=["GET", "POST"])
@login_required("admin")
def sms_campaign():
    db = get_db()
    f = request.values
    q = "SELECT DISTINCT c.id, c.name, c.phone FROM clients c WHERE c.phone IS NOT NULL AND c.phone<>''"
    args = []
    if f.get("branch"):
        q += " AND c.branch_id=?"
        args.append(f["branch"])
    if f.get("gender") in ("ذكر", "أنثى"):
        q += " AND c.gender=?"
        args.append(f["gender"])
    if f.get("since"):
        q += " AND c.id IN (SELECT client_id FROM payments WHERE cancelled=0 AND substr(created_at,1,10)>=?)"
        args.append(f["since"])
    if f.get("dept") in DEPTS:
        q += " AND c.id IN (SELECT client_id FROM payments WHERE cancelled=0 AND dept=?)"
        args.append(f["dept"])
    targets = db.execute(q + " ORDER BY c.name", args).fetchall()
    msg = f.get("message", "").strip()
    if request.method == "POST" and f.get("action") == "send":
        if not msg:
            flash("اكتب نص الرسالة", "err")
        elif not targets:
            flash("لا يوجد زبائن بهذه الشروط", "err")
        else:
            for c in targets:
                db.execute("INSERT INTO sms_log(phone,message,status,created_at) VALUES(?,?,'queued',?)",
                           (c["phone"], sms_fill(msg, name=c["name"], center=setting("center_name")), now_str()))
            db.commit()
            flash(f"أُضيفت {len(targets)} رسالة إلى قائمة الإرسال (حوالي 15 رسالة كل دقيقة)", "ok")
            return redirect(url_for("sms_page"))
    return render_template("sms_campaign.html", targets=targets, f=f, msg=msg,
                           sample=sms_fill(msg, name=targets[0]["name"], center=setting("center_name")) if msg and targets else "")


def reminder_loop():
    """يفحص كل دقيقة المواعيد القريبة ويرسل التذكير تلقائيًا."""
    while True:
        try:
            with app.app_context():
                stock_sms_check()
        except Exception as e:
            print("stock sms error:", e)
        try:
            con = connect()
            if con.execute("SELECT value FROM settings WHERE key='sms_enabled'").fetchone()["value"] == "1":
                for a in due_reminders(con):
                    # لا نعيد المحاولة تلقائيًا لنفس الموعد أكثر من 3 مرات
                    fails = con.execute("SELECT COUNT(*) n FROM sms_log WHERE appointment_id=? AND status='failed'",
                                        (a["id"],)).fetchone()["n"]
                    if fails < 3:
                        send_reminder(con, a)
            sms_extra_jobs(con)
            con.close()
        except Exception as e:
            print("reminder error:", e)
        time.sleep(60)


@app.route("/sms", methods=["GET", "POST"])
@login_required("admin")
def sms_page():
    db = get_db()
    if request.method == "POST":
        if request.form.get("action") == "test":
            ok, resp = send_sms(db, request.form.get("phone"), "رسالة تجريبية من " + setting("center_name"))
            flash(("تم الإرسال: " if ok else "فشل الإرسال: ") + resp[:200], "ok" if ok else "err")
        elif request.form.get("action") == "send":
            a = db.execute("""SELECT a.*, c.name AS client, c.phone, b.name AS branch FROM appointments a
                JOIN clients c ON c.id=a.client_id JOIN branches b ON b.id=a.branch_id WHERE a.id=?""",
                           (request.form.get("aid"),)).fetchone()
            if a:
                ok = send_reminder(db, a)
                flash("تم إرسال التذكير" if ok else "فشل الإرسال، راجع السجل", "ok" if ok else "err")
        return redirect(url_for("sms_page"))
    upcoming = due_reminders(db)
    log = db.execute("""SELECT l.*, c.name AS client FROM sms_log l LEFT JOIN appointments a ON a.id=l.appointment_id
        LEFT JOIN clients c ON c.id=a.client_id ORDER BY l.id DESC LIMIT 100""").fetchall()
    queued = db.execute("SELECT COUNT(*) n FROM sms_log WHERE status='queued'").fetchone()["n"]
    return render_template("sms.html", upcoming=upcoming, log=log, enabled=setting("sms_enabled") == "1", queued=queued)



# ---------------------------------------------------------------- الحواسيب
def device_rows(db):
    return db.execute("""SELECT u.*, b.name AS branch FROM users u LEFT JOIN branches b ON b.id=u.branch_id
        WHERE u.device=1 ORDER BY u.branch_id DESC, u.role='reception' DESC, u.id""").fetchall()


def new_pair_code(db, uid):
    db.execute("DELETE FROM pair_codes WHERE user_id=? OR expires<?", (uid, now_str()))
    while True:
        code = f"{secrets.randbelow(10**6):06d}"
        if not db.execute("SELECT 1 FROM pair_codes WHERE code=?", (code,)).fetchone():
            break
    exp = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute("INSERT INTO pair_codes(code,user_id,expires) VALUES(?,?,?)", (code, uid, exp))
    return code


@app.route("/devices", methods=["GET", "POST"])
@login_required("admin")
def devices():
    if sync.NODE:
        abort(404)
    db = get_db()
    code = None
    if request.method == "POST":
        act = request.form.get("act")
        did = request.form.get("id", "")
        d = db.execute("SELECT * FROM users WHERE id=? AND device=1", (did,)).fetchone() if did.lstrip("-").isdigit() else None
        if act == "add":
            br, role = request.form.get("branch_id", ""), request.form.get("role")
            pw = request.form.get("password", "").strip()
            name = request.form.get("full_name", "").strip()
            if not br.isdigit() or role not in DEPTS or len(pw) < 4 or not name:
                flash("أكمل الاسم والفرع والمكان، وكلمة سر من 4 أحرف أو أكثر", "err")
                return redirect(url_for("devices"))
            if role != "reception" and role not in branch_depts(int(br)):
                flash("هذا المكان غير موجود في الفرع المختار", "err")
                return redirect(url_for("devices"))
            slot = max(100, db.execute("SELECT COALESCE(MAX(slot),0) FROM users").fetchone()[0]) + 1
            cur = db.execute("""INSERT INTO users(username,pw_hash,full_name,role,branch_id,device,slot)
                VALUES(?,?,?,?,?,1,?)""", (f"dev-{slot}", generate_password_hash(pw), name, role, int(br), slot))
            code = new_pair_code(db, cur.lastrowid)
            audit("إضافة حاسوب", name)
            flash(f"تمت إضافة الحاسوب «{name}». رمز الربط: {code}", "ok")
        elif d and act == "password":
            pw = request.form.get("password", "").strip()
            if len(pw) < 4:
                flash("كلمة السر قصيرة جدًا (4 على الأقل)", "err")
            else:
                db.execute("UPDATE users SET pw_hash=? WHERE id=?", (generate_password_hash(pw), d["id"]))
                audit("تغيير كلمة سر حاسوب", d["full_name"])
                flash(f"تم تغيير كلمة سر «{d['full_name']}». تصل للحاسوب عند اتصاله بالإنترنت.", "ok")
        elif d and act == "toggle":
            db.execute("UPDATE users SET active=? WHERE id=?", (0 if d["active"] else 1, d["id"]))
            audit("إيقاف حاسوب" if d["active"] else "تشغيل حاسوب", d["full_name"])
            flash(("تم إيقاف" if d["active"] else "تم تشغيل") + f" «{d['full_name']}»", "ok")
        elif d and act == "rename":
            nm = request.form.get("full_name", "").strip()
            if nm:
                db.execute("UPDATE users SET full_name=? WHERE id=?", (nm, d["id"]))
        elif d and act == "code":
            code = new_pair_code(db, d["id"])
            flash(f"رمز الربط الجديد لـ «{d['full_name']}»: {code} (صالح يومين، لمرة واحدة)", "ok")
        db.commit()
        return redirect(url_for("devices"))
    codes = {r["user_id"]: r for r in db.execute("SELECT * FROM pair_codes WHERE expires>=?", (now_str(),))}
    return render_template("devices.html", rows=device_rows(db), codes=codes,
                           branches=db.execute("SELECT * FROM branches WHERE active=1 ORDER BY id").fetchall(),
                           now=datetime.now())


@app.route("/pair", methods=["POST"])
def pair_api():
    """حاسوب جديد يرسل رمز الربط فيأخذ إعداداته (الفرع، المكان، مفتاح المزامنة)."""
    if sync.NODE:
        abort(404)
    if not limiter_ok():
        return {"ok": False, "error": "محاولات كثيرة، انتظر دقيقة"}, 429
    data = request.get_json(force=True, silent=True) or {}
    db = get_db()
    r = db.execute("""SELECT u.* FROM pair_codes p JOIN users u ON u.id=p.user_id
        WHERE p.code=? AND p.expires>=? AND u.active=1""", (str(data.get("code", "")).strip(), now_str())).fetchone()
    if not r:
        limiter_fail()
        return {"ok": False, "error": "الرمز غير صحيح أو انتهت صلاحيته"}, 403
    db.execute("DELETE FROM pair_codes WHERE user_id=?", (r["id"],))
    audit("ربط حاسوب جديد", r["full_name"], branch_id=r["branch_id"])
    db.commit()
    return {"ok": True, "node": {"branch_id": r["branch_id"], "slot": r["slot"], "device": r["username"],
                                 "key": setting("sync_key"), "name": r["full_name"]}}


# ---------------------------------------------------------------- المزامنة
def sync_auth():
    if sync.NODE:
        abort(404)
    key = request.headers.get("X-Sync-Key", "")
    real = setting("sync_key")
    if not real or not secrets.compare_digest(key, real):
        abort(403)
    data = request.get_json(force=True, silent=True) or {}
    b = data.get("branch_id")
    db = get_db()
    if not db.execute("SELECT 1 FROM branches WHERE id=?", (b,)).fetchone():
        abort(400)
    dv = data.get("device")
    if dv:
        d = db.execute("SELECT id,active,branch_id FROM users WHERE username=? AND device=1", (dv,)).fetchone()
        if not d or not d["active"] or d["branch_id"] != int(b):
            abort(423)  # الحاسوب موقوف أو محذوف
        db.execute("UPDATE users SET last_seen=? WHERE id=?", (now_str(), d["id"]))
        db.commit()
    return data, int(b)


@app.route("/sync/push", methods=["POST"])
def sync_push():
    data, b = sync_auth()
    n = sync.central_push(get_db(), b, data)
    return {"ok": True, "applied": n}


@app.route("/sync/pull", methods=["POST"])
def sync_pull():
    data, b = sync_auth()
    out = sync.central_pull(get_db(), b, data.get("since") or "", data.get("img_ver"))
    out["ok"] = True
    return app.response_class(json.dumps(out, ensure_ascii=False), mimetype="application/json")


@app.route("/sync/now", methods=["GET", "POST"])
def sync_now_route():
    if not sync.NODE:
        abort(404)
    ok, msg = sync.sync_now(connect)
    flash(("تمت المزامنة مع الحاسوب المركزي" if ok else "تعذر الاتصال بالحاسوب المركزي: " + msg), "ok" if ok else "err")
    return redirect(request.referrer or url_for("dashboard"))


@app.errorhandler(403)
def forbidden(e):
    return render_template("msg.html", msg="ليست لديك صلاحية الدخول إلى هذه الصفحة"), 403


@app.errorhandler(404)
def notfound(e):
    return render_template("msg.html", msg="الصفحة أو العنصر غير موجود"), 404


RESTORE_MSG = backup.apply_pending_restore(DB_PATH)
from templates import TEMPLATES  # noqa: E402
app.jinja_loader = DictLoader(TEMPLATES)

# ---------------------------------------------------------------- حاسوب جديد لم يُربط بعد
# ملف التثبيت العام يضع pair.flag: الحاسوب يطلب رمز الربط من المديرة قبل أي شيء
PAIR_MODE = not sync.NODE and os.path.exists(os.path.join(BASE_DIR, "pair.flag"))
DEFAULT_CENTRAL = "http://bilsan-central:5000"

SETUP_HTML = r"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>ربط الحاسوب - بيلسان</title>{% if done %}<meta http-equiv="refresh" content="8;url=/login">{% endif %}
<style>body{font-family:Tahoma,Arial;background:radial-gradient(circle at 50% 20%,#1f6b63,#0b3b36);color:#163;margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center}
.c{background:#fbf6ec;border-radius:16px;padding:26px;width:min(420px,92vw);box-shadow:0 10px 40px #0005;text-align:center}
img{width:200px}input{width:100%;box-sizing:border-box;padding:12px;margin:6px 0;border:1px solid #c9b48f;border-radius:10px;font-size:18px;text-align:center}
.code{letter-spacing:8px;font-size:28px}button{background:#0f4c45;color:#f3d6a8;border:0;border-radius:10px;padding:12px 30px;font-size:18px;cursor:pointer;margin-top:8px}
.err{background:#fde2e2;color:#8a1c1c;padding:10px;border-radius:8px}.ok{background:#e2f5e9;color:#145c32;padding:10px;border-radius:8px}
details{margin-top:10px;color:#555;font-size:13px}</style></head><body><div class="c">
<img src="/static/logo.png" alt="بيلسان"><h2>ربط هذا الحاسوب</h2>
{% if done %}<p class="ok">تم الربط: <b>{{ done }}</b><br>البرنامج يُعاد تشغيله... انتظر قليلًا.</p>
{% else %}<p>اطلب من المديرة <b>رمز الربط</b> (6 أرقام) من صفحة «الحواسيب».</p>
{% if err %}<p class="err">{{ err }}</p>{% endif %}
<form method="post"><input class="code" name="code" inputmode="numeric" maxlength="6" placeholder="------" required autofocus>
<details><summary>عنوان الحاسوب المركزي</summary><input name="central" value="{{ central }}" dir="ltr"></details>
<button>ربط</button></form>{% endif %}</div></body></html>"""


def restart_self():
    """يعيد تشغيل البرنامج بعد الربط (ليعمل كحاسوب فرع)."""
    import subprocess

    def go():
        time.sleep(1.5)
        args = [sys.executable] + ([] if getattr(sys, "frozen", False) else [os.path.abspath(sys.argv[0])])
        args += [a for a in sys.argv[1:] if a != "--restart"] + ["--restart"]
        try:
            subprocess.Popen(args, close_fds=True)
        finally:
            os._exit(0)
    threading.Thread(target=go, daemon=True).start()


if PAIR_MODE:
    @app.before_request
    def _pair_only():
        if request.endpoint not in ("setup_pair", "static"):
            return redirect("/setup")

    @app.route("/setup", methods=["GET", "POST"])
    def setup_pair():
        from jinja2 import Template
        def render_template_string(src, **kw):  # بدون سياق البرنامج (القاعدة لم تُنشأ بعد)
            return Template(src, autoescape=True).render(**kw)
        central = (request.form.get("central") or DEFAULT_CENTRAL).strip().rstrip("/")
        if request.method == "POST":
            try:
                body = json.dumps({"code": request.form.get("code", "").strip()}).encode()
                req = urlreq.Request(central + "/pair", data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
                try:
                    with urlreq.urlopen(req, timeout=20) as r:
                        res = json.loads(r.read().decode("utf-8"))
                except Exception as e:  # noqa: BLE001
                    rd = getattr(e, "read", None)
                    res = json.loads(rd().decode("utf-8")) if rd else {"ok": False, "error":
                          "تعذّر الوصول إلى الحاسوب المركزي. تأكد من الإنترنت ومن تشغيل Tailscale وحاسوب المديرة."}
                if not res.get("ok"):
                    return render_template_string(SETUP_HTML, err=res.get("error"), central=central, done=None)
                node = dict(res["node"], central_url=central)
                name = node.pop("name", "")
                with open(os.path.join(BASE_DIR, "node.json"), "w", encoding="utf-8") as f:
                    json.dump(node, f, ensure_ascii=False, indent=1)
                os.remove(os.path.join(BASE_DIR, "pair.flag"))
                restart_self()
                return render_template_string(SETUP_HTML, done=name, central=central, err=None)
            except ValueError:
                return render_template_string(SETUP_HTML, err="رد غير مفهوم من الحاسوب المركزي",
                                              central=central, done=None)
        return render_template_string(SETUP_HTML, central=central, err=None, done=None)
else:
    init_db()


def wait_port_free(port, secs=15):
    import socket
    for _ in range(secs * 4):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return
        time.sleep(0.25)


def run_server(port=None):
    if sys.stdout is None or sys.stderr is None:  # تشغيل خفي (pythonw / Bilsan.exe): السجل في ملف
        _log = open(os.path.join(BASE_DIR, "bilsan.log"), "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = _log
    if RESTORE_MSG:
        print(RESTORE_MSG)
    port = port or int(os.environ.get("BILSAN_PORT", "5000"))
    if "--restart" in sys.argv:
        wait_port_free(port)
    if not PAIR_MODE:
        threading.Thread(target=backup.backup_loop, args=(connect, DB_PATH), daemon=True).start()
        if sync.NODE:
            print(f"  وضع الحاسوب الفرعي: يتزامن مع {sync.NODE['central_url']}")
            threading.Thread(target=sync.node_loop, args=(connect,), daemon=True).start()
        else:
            threading.Thread(target=reminder_loop, daemon=True).start()
    # الحاسوب المركزي يستقبل الحواسيب الأخرى، أما الحاسوب الفرعي فلا يفتح إلا لنفسه
    host = "127.0.0.1" if (sync.NODE or PAIR_MODE) else "0.0.0.0"
    print(f"\n  {DEFAULT_SETTINGS['center_name']}\n  البرنامج يعمل على: http://localhost:{port}\n")
    try:
        from waitress import serve
        serve(app, host=host, port=port, threads=8)
    except ImportError:
        app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    run_server()
