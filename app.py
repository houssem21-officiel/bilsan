# -*- coding: utf-8 -*-
"""
برنامج تسيير مركز الطب البديل بيلسان
الخادم يعمل على الحاسوب المركزي، والفروع (سكيكدة، الحروش) تتصل به عبر المتصفح.
"""
import os, sys, re, csv, io, json, sqlite3, threading, time, base64, math
from datetime import datetime, timedelta, date
from functools import wraps
from urllib import request as urlreq, error as urlerr
from urllib.parse import urlsplit

from flask import (Flask, g, request, redirect, url_for, session, flash,
                   render_template, abort, Response, send_file)
from jinja2 import DictLoader
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import sync
from sync import center_now, center_today
import i18n
import catalog
import backup

import paths  # noqa: E402
try:
    with open(os.path.join(paths.APP_DIR, "VERSION")) as _f:
        APP_VERSION = _f.read().strip()
except OSError:
    APP_VERSION = "0"
APP_VERSION = os.environ.get("BILSAN_VERSION", APP_VERSION)  # للاختبار فقط
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
VISIT_TARGETS = {"beauty": "قسم التجميل", "reception": "قسم العلاج", "laser": "قسم الليزر",
                 "director": "المديرة"}  # «المديرة» باقية غير للزيارات القديمة؛ ما عادش تتبعث ليها
SEND_TARGETS = ("beauty", "reception", "laser")
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
CREATE TABLE IF NOT EXISTS cancelled_ops(id INTEGER PRIMARY KEY, kind TEXT, ref_id INTEGER, branch_id INTEGER, day TEXT,
    summary TEXT, amount REAL DEFAULT 0, reason TEXT, requested_by INTEGER, done_by INTEGER, created_at TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS course_days(id INTEGER PRIMARY KEY, trainee_id INTEGER, day_no INTEGER, day_date TEXT,
    status TEXT, note TEXT, created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS skin_cards(id INTEGER PRIMARY KEY, client_id INTEGER, skin_type TEXT, phototype TEXT,
    concerns TEXT, contra TEXT, sensitivities TEXT, routine TEXT, notes TEXT, updated_by INTEGER, updated_at TEXT);
CREATE TABLE IF NOT EXISTS service_materials(id INTEGER PRIMARY KEY, service_id INTEGER, product_id INTEGER, qty REAL DEFAULT 1);
CREATE TABLE IF NOT EXISTS perms(id INTEGER PRIMARY KEY, branch_id INTEGER, role TEXT, perm TEXT, enabled INTEGER,
    UNIQUE(branch_id, role, perm));
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, branch_id INTEGER, user_id INTEGER, action TEXT,
    details TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS cash_days(id INTEGER PRIMARY KEY, branch_id INTEGER, day TEXT, role TEXT, counted REAL,
    expected REAL, note TEXT, closed_by INTEGER, closed_at TEXT, UNIQUE(branch_id, day, role));
CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY, branch_id INTEGER, kind TEXT, ref_id INTEGER,
    amount REAL DEFAULT 0, reason TEXT, status TEXT DEFAULT 'pending', requested_by INTEGER, requested_at TEXT,
    decided_by INTEGER, decided_at TEXT, note TEXT, info TEXT);
CREATE TABLE IF NOT EXISTS sms_log(id INTEGER PRIMARY KEY, appointment_id INTEGER, phone TEXT,
    message TEXT, status TEXT, response TEXT, created_at TEXT);
"""

DEFAULT_SETTINGS = {
    "center_name": "مركز الطب البديل بيلسان",
    "currency": "دج",
    "sms_enabled": "0",
    "sms_url": "https://api.sms-gate.app/3rdparty/v1/messages",
    "sms_user": "",
    "sms_pass": "",
    "sms_hours_before": "24",
    "sms_depts": "beauty",
    "sms_template": "مرحبا {name}، نذكركم بموعدكم في {center} - {branch} يوم {date} على الساعة {time}. للإلغاء اتصلوا بنا.",
    "sms_morning": "1",
    "sms_morning_hour": "8",
    "sms_morning_template": "صباح الخير {name}، نذكّركم بموعدكم اليوم على الساعة {time} في {center} - {branch}. في انتظاركم.",
    "sms_confirm": "0",
    "sms_confirm_template": "مرحبا {name}، تم تسجيل موعدكم في {center} - {branch} يوم {date} على الساعة {time}. شكرا لثقتكم.",
    "sms_birthday": "0",
    "sms_birthday_template": "{center} يتمنى لكم {name} عيد ميلاد سعيد وسنة مليئة بالصحة والعافية.",
    "last_birthday_run": "",
    "expiry_days": "30",
    "default_min_qty": "5",
    "manager_phone": "",
    "daily_summary": "0",
    "daily_summary_time": "21:00",
    "approvals_sms": "1",
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
    "staff_direct_cancel": "1",
    "cert_en_center": "BAYLASSAN CENTER",
    "cert_en_signer_title": "TRAINING INSTRUCTOR / BAYLASSAN CEO",
    "cert_en_signer": "Mechhoud Chahra",
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
    return center_now().strftime("%Y-%m-%d %H:%M:%S")


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
    add_col("appointments", "morning_sent_at", "TEXT")
    add_col("sms_log", "client_id", "INTEGER")
    add_col("services", "category", "TEXT")
    add_col("courses", "days", "INTEGER")
    add_col("payments", "plan_id", "INTEGER")
    add_col("appointments", "credit_used", "INTEGER DEFAULT 0")
    add_col("payments", "fix_note", "TEXT")
    add_col("clients", "name_latin", "TEXT")
    add_col("courses", "name_en", "TEXT")
    add_col("course_trainees", "cert_en", "TEXT")
    add_col("branches", "name_en", "TEXT")
    add_col("services", "aftercare", "TEXT")
    add_col("users", "lang", "TEXT")
    add_col("stock_moves", "cancelled", "INTEGER DEFAULT 0")
    add_col("appointments", "missed", "INTEGER DEFAULT 0")
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
    add_col("users", "app_version", "TEXT")
    con.execute("CREATE TABLE IF NOT EXISTS pair_codes(code TEXT PRIMARY KEY, user_id INTEGER, expires TEXT)")
    for k, v in DEFAULT_SETTINGS.items():
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
    add_col("products", "needs_review", "INTEGER DEFAULT 0")
    add_col("products", "added_by", "INTEGER")
    add_col("products", "review_note", "TEXT")
    add_col("products", "usage", "TEXT DEFAULT 'sale'")
    add_col("stock_moves", "kind", "TEXT")
    # الباقات: عدد الحصص، المدة بينها، سعر الباقة، وطريقة الدفع (بالحصة / الباقة كاملة)
    add_col("services", "pkg_sessions", "INTEGER DEFAULT 1")
    add_col("services", "pkg_interval", "INTEGER DEFAULT 0")
    add_col("services", "pkg_total", "REAL DEFAULT 0")
    add_col("services", "pkg_pay", "TEXT DEFAULT 'session'")
    add_col("plans", "pay_mode", "TEXT DEFAULT 'session'")
    add_col("charges", "plan_id", "INTEGER")
    add_col("visit_items", "appt_id", "INTEGER")
    add_col("visits", "appointment_id", "INTEGER")
    add_col("stock_moves", "dept", "TEXT")
    add_col("stock_moves", "visit_id", "INTEGER")
    sync.install(con)
    sync.migrate_v2(con)
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
    # النسخة 22.4: إعادة إدخال كل المنتجات والخدمات الأصلية مرة واحدة (بعد مسحها)
    if not sync.NODE and not os.environ.get("BILSAN_NO_CATALOG") and \
            not con.execute("SELECT 1 FROM settings WHERE key='catalog_restore_1'").fetchone():
        catalog.restore_catalog(con)
        con.execute("INSERT INTO settings(key,value) VALUES('catalog_restore_1','1')")
    if not sync.NODE and not os.environ.get("BILSAN_NO_CATALOG") and \
            not con.execute("SELECT 1 FROM settings WHERE key='catalog_v2'").fetchone():
        catalog.apply_catalog(con)  # يضيف الناقص (حتى بعد مسح البيانات) ويصنّف الكل
        con.execute("INSERT INTO settings(key,value) VALUES('catalog_v2','1')")
    if not sync.NODE and not os.environ.get("BILSAN_NO_CATALOG") and \
            not con.execute("SELECT 1 FROM settings WHERE key='catalog_v3'").fetchone():
        catalog.apply_catalog(con)  # النسخة 23.4: الرنين الحيوي والتشخيص الكمي
        con.execute("INSERT INTO settings(key,value) VALUES('catalog_v3','1')")
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
    ("products_edit", "إضافة المنتجات وتعديلها وتعديل المخزون", ("reception",)),
    ("sale_prices", "تعديل أسعار بيع المنتجات", ("reception",)),
    ("cost_prices", "إدخال أسعار الشراء ورؤيتها (المنتجات والمخزون)", ("reception",)),
    ("purchases", "إدخال فاتورة شراء (استلام سلعة)", ("reception",)),
    ("cancel_ops", "طلب إلغاء العمليات (المديرة توافق)", ("reception",)),
    ("stock_use", "تسجيل استهلاك المواد (مواد العمل)", ("reception", "laser", "beauty")),
    ("expenses", "إخراج مبلغ من الصندوق (مصروف)", ()),
    ("medical", "الملف الطبي وصور قبل/بعد", ("laser", "beauty")),
    ("consent", "طباعة وثيقة الموافقة", ("reception", "laser", "beauty")),
]
PERM_LABELS = {k: v for k, v, _ in PERMS}
# الأقسام/الغرف في حساب الصندوق (من أين جاء المال)
SECTIONS = {"hijama": "غرفة الحجامة", "herbs": "الأعشاب والعلاج", "laser": "غرفة الليزر", "beauty": "غرفة التجميل",
            "director": "علاج المديرة", "product": "بيع المنتجات", "course": "الدورات", "other": "أخرى"}
# أين تُستعمل المادة (للاستهلاك)
USE_ROOMS = {"hijama": "غرفة الحجامة", "laser": "غرفة الليزر", "beauty": "غرفة التجميل",
             "director": "غرفة المديرة", "reception": "الاستقبال / عام"}
# ---- غرفة التجميل: بطاقة البشرة
SKIN_TYPES = ["عادية", "جافة", "دهنية", "مختلطة", "حساسة"]
PHOTOTYPES = ["I — بيضاء جدًا", "II — بيضاء", "III — قمحية فاتحة", "IV — قمحية", "V — سمراء", "VI — سمراء داكنة"]
SKIN_CONCERNS = ["حب الشباب", "آثار حب الشباب", "تصبغات / كلف", "تجاعيد وخطوط", "ترهل", "مسام واسعة", "رؤوس سوداء",
                 "جفاف", "لمعان ودهون", "هالات سوداء", "احمرار", "تساقط الشعر", "شعر زائد", "سيلوليت", "علامات تمدد"]
SKIN_CONTRA = ["حمل", "رضاعة", "دواء حب الشباب (روكيتان)", "تعرض للشمس مؤخرًا", "تقشير أو ليزر مؤخرًا",
               "مرض جلدي (إكزيما، صدفية...)", "هربس / جروح في المنطقة", "حساسية من مواد التجميل", "سكري", "مميّع الدم"]
TREAT_AREAS = ["الوجه", "الجبهة", "حول العينين", "الرقبة", "الصدر", "الإبطين", "الذراعين", "اليدين", "البطن", "الظهر",
               "الساقين", "المنطقة الحساسة", "فروة الرأس"]
SKIN_REACTIONS = ["عادية", "احمرار خفيف", "احمرار قوي", "تهيّج / حكة", "تورم", "ألم"]
AFTERCARE_DEFAULTS = [
    (("تقشير", "كربون"), "تجنبي الشمس 7 أيام واستعملي واقي الشمس (SPF 50) كل 3 ساعات.\nلا تقشّري البشرة ولا تحكّيها حتى يسقط التقشير من تلقاء نفسه.\nرطّبي البشرة صباحًا ومساءً.\nدون مكياج 24 ساعة، وتجنبي حمام البخار والسباحة 3 أيام."),
    (("هيدرا", "تنظيف", "أوكسيجين"), "دون مكياج 12 ساعة.\nاشربي الماء بكثرة ورطّبي البشرة.\nواقي الشمس كل يوم.\nلا تستعملي مقشّرًا ولا منتجات قوية 3 أيام."),
    (("ميزو", "إبر", "بلازما", "فيلر", "حقن"), "لا تلمسي المنطقة ولا تدلكيها 24 ساعة.\nدون مكياج 24 ساعة.\nتجنبي الرياضة والحمام والساونا مدة يومين.\nالاحمرار والانتفاخ الخفيف طبيعيان ويزولان خلال يوم أو يومين.\nإذا شعرتِ بألم شديد أو حرارة فاتصلي بالمركز."),
    (("ليزر", "إزالة الشعر", "إليكتروليز"), "تجنبي الشمس أسبوعين وضعي واقي الشمس.\nلا شمع ولا ملقاط بين الجلسات (الحلاقة مسموحة).\nتجنبي الحمام الساخن والساونا 48 ساعة.\nرطّبي المنطقة بكريم مهدّئ إذا كان احمرار."),
    (("تبييض",), "واقي الشمس ضروري كل يوم.\nلا تحكّي المنطقة.\nاستعملي الكريم الموصوف حسب التعليمات.\nتظهر النتيجة مع توالي الحصص."),
    (("تخسيس", "نحت", "مساج", "تدليك"), "اشربي 2 لتر ماء في اليوم.\nقلّلي الملح والسكر.\nامشي 30 دقيقة على الأقل.\nتجنبي الأكل الثقيل ساعتين بعد الجلسة."),
]


def aftercare_for(service):
    """نصائح ما بعد الجلسة: المكتوبة في الخدمة، وإلا نصائح جاهزة حسب نوعها."""
    if service["aftercare"]:
        return service["aftercare"]
    for keys, txt in AFTERCARE_DEFAULTS:
        if any(k in (service["name"] or "") for k in keys):
            return txt.replace("\\n", "\n")
    return ""


PRODUCT_USAGE = {"sale": "للبيع", "use": "للاستعمال (مواد العمل)", "both": "للبيع وللاستعمال"}
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
        today=center_today().isoformat(),
        view_branch=session.get("view_branch"),
        alerts_count=len(stock_alerts(scope_branch())) if current_user() else 0,
        branch_name=branch_name,
        NODE=sync.NODE, perm=has_perm, LANGS=i18n.LANGS, cur_lang=current_lang(), bk=backup_status() if (current_user() and current_user()["role"] == "admin") else None, PLACES=PLACES, SECTIONS=SECTIONS, napprovals=pending_approvals(get_db()) if (current_user() and current_user()["role"] == "admin" and not sync.NODE) else 0, USE_ROOMS=USE_ROOMS, PRODUCT_USAGE=PRODUCT_USAGE, SKIN_TYPES=SKIN_TYPES, PHOTOTYPES=PHOTOTYPES, SKIN_CONCERNS=SKIN_CONCERNS, SKIN_CONTRA=SKIN_CONTRA, TREAT_AREAS=TREAT_AREAS, SKIN_REACTIONS=SKIN_REACTIONS, locked=price_locked() if current_user() else False, can_collect=can_collect() if current_user() else False, node_status=node_status() if sync.NODE else None,
    )


def node_status():
    db = get_db()
    return dict(ok=sync.state_get(db, "last_ok"), err=sync.state_get(db, "last_error"),
                newver=sync.central_is_newer(db), ms=sync.LAST_MS[0],
                pending=sync.pending_count(db), first=not db.execute("SELECT 1 FROM users").fetchone(),
                clock_off=int(abs(sync.CLOCK_SKEW[0]) // 60))


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
    t = center_today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


@app.template_filter("dmy")
def dmy_filter(v):
    v = (v or "")[:10]
    return f"{v[8:10]}/{v[5:7]}/{v[0:4]}" if len(v) == 10 and v[4] == "-" else v


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
            lang, picked = session.get("lang"), session.get("lang_pick")
            session.clear()
            session["uid"] = u["id"]
            if picked and lang in i18n.LANGS:  # اللغة اللي اختارها في صفحة الدخول تتحفظ في حسابو
                session["lang"] = lang
                db.execute("UPDATE users SET lang=? WHERE id=?", (lang, u["id"]))
                db.commit()
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
    lang = current_lang()
    session.clear()
    session["lang"] = lang  # صفحة الدخول تبقى بنفس اللغة
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
    today = center_today().isoformat()
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
        due = due_salaries()
        chk = setup_checklist(db) if not sync.NODE else []
        return render_template("dash_admin.html", per_branch=per_branch, grand=grand, due=due, chk=chk,
                               recent=recent, low=low, alerts=director_alerts(db, due),
                               rooms=room_accounts(today, today, None, db.execute(
                                   """SELECT p.*, b.name AS branch FROM payments p JOIN branches b ON b.id=p.branch_id
                                      WHERE p.cancelled=0 AND substr(p.created_at,1,10)=?""", (today,)).fetchall()),
                               waiting=db.execute("SELECT COUNT(*) FROM visits WHERE status IN ('waiting','treating') AND substr(created_at,1,10)>=?",
                                              (center_today().isoformat(),)).fetchone()[0])
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


def setup_checklist(db):
    """قائمة تجهيز المركز للمديرة: تظهر حتى يكتمل كل شيء."""
    items = []
    u = current_user()
    if u and check_password_hash(u["pw_hash"], "admin123"):
        items.append((False, "غيّري كلمة مرور المديرة (ما زالت الافتراضية)", url_for("change_password")))
    n = db.execute("SELECT COUNT(*) FROM services WHERE active=1 AND COALESCE(price,0)=0 AND kind<>'course'").fetchone()[0]
    items.append((n == 0, f"حدّدي أسعار الخدمات ({n} خدمة بلا سعر)" if n else "أسعار الخدمات محدّدة", url_for("services")))
    n = db.execute("SELECT COUNT(*) FROM products WHERE active=1 AND COALESCE(usage,'sale')<>'use' AND COALESCE(price,0)=0").fetchone()[0]
    items.append((n == 0, f"حدّدي أسعار بيع المنتجات ({n} منتج بلا سعر)" if n else "أسعار بيع المنتجات محدّدة", url_for("products")))
    for b in active_branches():
        has = db.execute("SELECT 1 FROM stock_moves WHERE branch_id=? LIMIT 1", (b["id"],)).fetchone()
        items.append((bool(has), f"أدخلي المخزون الموجود في {b['name']}" if not has else f"المخزون مُدخل في {b['name']}",
                      url_for("stock_opening", branch=b["id"])))
    n = db.execute("SELECT COUNT(*) FROM employees WHERE active=1").fetchone()[0]
    items.append((n > 0, "سجّلي العمال (للحضور والأجور وتقرير اليوم)" if not n else f"العمال مسجّلون ({n})", url_for("staff")))
    ok = bool(setting("stamp_img") and setting("signature_img"))
    items.append((ok, "أضيفي صورة الختم والإمضاء (للشهادات والوثائق)" if not ok else "الختم والإمضاء موجودان", url_for("settings") + "#images"))
    ok = bool(setting("backup_dir2"))
    items.append((ok, "اختاري مكانًا ثانيًا للنسخ الاحتياطي (فلاشة أو قرص آخر)" if not ok else "النسخ الاحتياطي في مكانين", url_for("backup_page")))
    return items


def director_alerts(db, due=None):
    """كل ما يحتاج انتباه المديرة، في قائمة وحدة، وكل عنصر برابط للحل."""
    al = []
    nfix = db.execute("""SELECT COUNT(*) FROM audit WHERE substr(created_at,1,10)=? AND action IN
        ('تصحيح وصل','إلغاء وصل','تصحيح موعد','تصحيح قسم الزيارة','إلغاء عملية') AND user_id IN (SELECT id FROM users WHERE role<>'admin')""",
                      (center_today().isoformat(),)).fetchone()[0]
    if nfix:
        al.append(("amber", "audit", f"صحّح العمال أو ألغوا {nfix} عملية اليوم — للاطلاع", url_for("audit_page")))
    n = pending_approvals(db)
    if n:
        al.append(("red", "key", f"{n} طلب ينتظر موافقتك (تخفيض أو إلغاء)", url_for("approvals")))
    n = db.execute("""SELECT COUNT(*) FROM cash_days WHERE day>=? AND counted IS NOT NULL
        AND ABS(counted-expected)>=1""", ((center_today() - timedelta(days=2)).isoformat(),)).fetchone()[0]
    if n:
        al.append(("red", "safe", f"فرق في عدّ الصندوق ({n})", url_for("cash_daily")))
    n = db.execute("SELECT COUNT(*) FROM products WHERE needs_review=1").fetchone()[0]
    if n:
        al.append(("amber", "products", f"{n} منتج جديد أو سعر تغيّر يحتاج مراجعتك", url_for("products")))
    st = stock_alerts(None)
    if st:
        out = sum(1 for s in st if s["out"])
        al.append(("amber", "alert", f"{len(st)} منتج قارب على النفاد أو الصلاحية" + (f" ({out} نفد)" if out else ""),
                   url_for("stock_alerts_page")))
    for b in active_branches():
        n = sum(1 for r in reorder_suggestions(b["id"]) if r["suggest"] > 0)
        if n:
            al.append(("amber", "truck", f"{b['name']}: {n} مادة لازم تتشرى — الطلبية جاهزة، ما عليكِ إلا الموافقة",
                       url_for("purchase_auto", branch=b["id"])))
    due = due if due is not None else due_salaries()
    if due:
        late = sum(1 for d in due if d.get("late"))
        al.append(("red" if late else "amber", "staff", f"{len(due)} أجرة حان وقتها" + (f" ({late} متأخرة)" if late else ""),
                   url_for("staff")))
    if not sync.NODE:
        lim = (center_now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        off = db.execute("""SELECT full_name FROM users WHERE device=1 AND active=1 AND last_seen IS NOT NULL
            AND last_seen<?""", (lim,)).fetchall()
        if off and 8 <= center_now().hour < 20:
            al.append(("amber", "monitor", "حواسيب غير متصلة: " + "، ".join(o[0] for o in off[:4]), url_for("devices")))
    n = db.execute("""SELECT COUNT(*) FROM appointments WHERE plan_id IS NOT NULL AND status='scheduled'
        AND start_at IS NOT NULL AND substr(start_at,1,10)<?""", (center_today().isoformat(),)).fetchone()[0]
    if n:
        al.append(("amber", "calendar", f"{n} حصة فائتة لم تُسجَّل (الزبونة لم تحضر؟)", url_for("appts_missed")))
    n = db.execute("SELECT COUNT(*) FROM charges WHERE status='pending' AND substr(created_at,1,10)<?",
                   (center_today().isoformat(),)).fetchone()[0]
    if n:
        al.append(("amber", "debt", f"{n} مبلغ من أيام سابقة لم يُدفع بعد", url_for("reception")))
    return al


# ---------------------------------------------------------------- الزبائن
@app.route("/clients", methods=["GET", "POST"])
@login_required()
def clients():
    db = get_db()
    u = current_user()
    if request.method == "POST":
        need("clients_edit")
        name = request.form.get("name", "").strip()
        dup = find_by_phone(db, request.form.get("phone", ""))
        if name and dup:
            flash(f"هذا الرقم مسجّل من قبل باسم «{dup['name']}»، فهذا ملفه (لا يُفتح ملف ثانٍ لنفس الشخص).", "ok")
            back = request.form.get("back")
            if back and back.startswith("/"):
                sep = "&" if "?" in back else "?"
                return redirect(f"{back}{sep}client_id={dup['id']}")
            return redirect(url_for("client_view", cid=dup["id"]))
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


def client_timeline(db, cid):
    """الملف الطبي الموحّد: كل ما قام به الزبون في المركز، حصة بعد حصة، من الأقدم إلى الأحدث."""
    names = {r["id"]: r["full_name"] for r in db.execute("SELECT id, full_name FROM users")}
    ev = []
    photos = [dict(r) for r in db.execute(
        "SELECT id,kind,note,created_at FROM client_photos WHERE client_id=? ORDER BY id", (cid,))] \
        if can_see_photos() else []
    notes = [dict(r) for r in db.execute(
        "SELECT * FROM client_notes WHERE client_id=? ORDER BY id", (cid,))] if has_perm("medical") else []
    used_ph, used_nt, appt_in_visit = set(), set(), set()
    visits = db.execute("""SELECT v.*, b.name AS branch FROM visits v JOIN branches b ON b.id=v.branch_id
        WHERE v.client_id=? ORDER BY v.created_at""", (cid,)).fetchall()
    for v in visits:
        items = db.execute("""SELECT i.*, s.name AS sname, s.category AS scat, a.session_no, pl.title AS plan
            FROM visit_items i LEFT JOIN services s ON s.id=i.service_id
            LEFT JOIN appointments a ON a.id=i.appt_id LEFT JOIN plans pl ON pl.id=a.plan_id
            WHERE i.visit_id=? ORDER BY i.id""", (v["id"],)).fetchall()
        for i in items:
            if i["appt_id"]:
                appt_in_visit.add(i["appt_id"])
        if v["appointment_id"]:
            appt_in_visit.add(v["appointment_id"])
        mats = db.execute("""SELECT pr.name, -SUM(m.qty) AS q FROM stock_moves m JOIN products pr ON pr.id=m.product_id
            WHERE m.visit_id=? AND m.qty<0 AND COALESCE(m.cancelled,0)=0 GROUP BY pr.name""", (v["id"],)).fetchall()
        day = (v["created_at"] or "")[:10]
        vn = [n for n in notes if n["visit_id"] == v["id"] or
              (not n["visit_id"] and (n["created_at"] or "")[:10] == day and n["id"] not in used_nt)]
        used_nt.update(n["id"] for n in vn)
        vp = [ph for ph in photos if (ph["created_at"] or "")[:10] == day and ph["id"] not in used_ph]
        used_ph.update(ph["id"] for ph in vp)
        svc = [i for i in items if i["kind"] == "service"]
        prods = [i for i in items if i["kind"] != "service"]
        title = "، ".join((i["sname"] or i["description"] or "") for i in svc) or (v["request"] or "زيارة")
        ev.append(dict(kind="visit", at=v["created_at"] or "", dept=v["target"], branch=v["branch"], title=title,
                       status=v["status"], vid=v["id"], who=names.get(v["done_by"]) or "",
                       request=v["request"] or "", svc=svc, prods=prods, mats=mats, notes=vn, photos=vp,
                       total=sum((i["qty"] or 0) * (i["unit_price"] or 0) for i in items)))
    for ap in db.execute("""SELECT a.*, s.name AS sname, b.name AS branch, pl.title AS plan FROM appointments a
            LEFT JOIN services s ON s.id=a.service_id JOIN branches b ON b.id=a.branch_id
            LEFT JOIN plans pl ON pl.id=a.plan_id WHERE a.client_id=?""", (cid,)):
        if ap["id"] in appt_in_visit or (ap["status"] == "done" and not ap["start_at"]):
            continue
        st = "noshow" if (ap["missed"] or ap["status"] == "noshow") else ap["status"]
        ev.append(dict(kind="appt", at=ap["start_at"] or ap["created_at"] or "", dept=ap["dept"], branch=ap["branch"],
                       title=ap["sname"] or "موعد", status=st, session_no=ap["session_no"], plan=ap["plan"],
                       note=ap["notes"] or "", aid=ap["id"]))
    for pl in db.execute("""SELECT pl.*, s.name AS sname, (SELECT COUNT(*) FROM appointments a WHERE a.plan_id=pl.id) n
            FROM plans pl LEFT JOIN services s ON s.id=pl.service_id WHERE pl.client_id=?""", (cid,)):
        ev.append(dict(kind="plan", at=pl["created_at"] or "", dept=pl["dept"], title=pl["title"] or pl["sname"] or "",
                       n=pl["n"], status=pl["status"], pid=pl["id"], note=pl["notes"] or ""))
    for p in db.execute("""SELECT p.*, b.name AS branch FROM payments p JOIN branches b ON b.id=p.branch_id
            WHERE p.client_id=? AND p.kind='product' AND p.cancelled=0""", (cid,)):
        its = db.execute("""SELECT si.qty, pr.name FROM sale_items si JOIN products pr ON pr.id=si.product_id
            WHERE si.payment_id=?""", (p["id"],)).fetchall()
        ev.append(dict(kind="sale", at=p["created_at"] or "", dept="sale", branch=p["branch"],
                       title="شراء منتجات", items=its or [], desc=p["description"] or "", total=p["amount"], pay=p["id"]))
    for n in notes:
        if n["id"] not in used_nt:
            ev.append(dict(kind="note", at=n["created_at"] or "", dept="note", title="ملاحظة طبية", note=n["note"],
                           who=names.get(n["created_by"]) or "", nid=n["id"]))
    rest = [ph for ph in photos if ph["id"] not in used_ph]
    for day in sorted({(ph["created_at"] or "")[:10] for ph in rest}):
        ev.append(dict(kind="photos", at=day, dept="note", title="صور",
                       photos=[ph for ph in rest if (ph["created_at"] or "")[:10] == day]))
    sc = db.execute("SELECT updated_at, updated_by FROM skin_cards WHERE client_id=?", (cid,)).fetchone()
    if sc and sc["updated_at"] and has_perm("medical"):
        ev.append(dict(kind="skin", at=sc["updated_at"], dept="beauty", title="تحديث بطاقة البشرة",
                       who=names.get(sc["updated_by"]) or ""))
    ev.sort(key=lambda e: e["at"] or "")
    today = center_today().isoformat()
    past = [e for e in ev if not (e["kind"] == "appt" and e["status"] == "scheduled" and e["at"][:10] >= today)]
    future = [e for e in ev if e not in past]
    n = 0
    for e in past:
        if e["kind"] == "visit" and e["status"] != "cancelled":
            n += 1
            e["no"] = n
    return past, future


def client_summary(db, cid):
    rows = db.execute("""SELECT COALESCE(s.name, i.description) AS nm, COUNT(*) AS n FROM visit_items i
        JOIN visits v ON v.id=i.visit_id LEFT JOIN services s ON s.id=i.service_id
        WHERE v.client_id=? AND i.kind='service' AND v.status<>'cancelled' GROUP BY nm ORDER BY n DESC""", (cid,)).fetchall()
    first = db.execute("SELECT MIN(created_at) FROM visits WHERE client_id=? AND status<>'cancelled'", (cid,)).fetchone()[0]
    return rows, first


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
    past, future = client_timeline(db, cid)
    deletable = client_is_empty(db, cid)
    summ, first = client_summary(db, cid)
    return render_template("client_view.html", c=c, appts=appts, pays=pays, cplans=cplans, cvisits=cvisits,
                           past=past, future=future, summ=summ, first=first, deletable=deletable,
                           skin=skin_card(db, cid) if has_perm("medical") else None,
                           cdebts=cdebts, notes=notes, photos=photos, can_photos=can_see_photos(),
                           services=services_for(current_user()["branch_id"] or work_branch()))


def phone_digits(p):
    d = re.sub(r"\D", "", p or "")
    if d.startswith("213") and len(d) > 9:
        d = "0" + d[3:]
    return d


def find_by_phone(db, phone):
    d = phone_digits(phone)
    if len(d) < 8:
        return None
    for r in db.execute("""SELECT id, name, phone FROM clients
            WHERE replace(replace(replace(replace(phone,' ',''),'-',''),'.',''),'/','') LIKE ?""", (f"%{d[-8:]}%",)):
        if phone_digits(r["phone"]) == d:
            return r
    return None


@app.route("/api/clients")
@login_required()
def api_clients():
    s = request.args.get("q", "").strip()
    db = get_db()
    rows = db.execute("""SELECT c.id, c.name, c.phone,
        (SELECT MAX(substr(created_at,1,10)) FROM visits v WHERE v.client_id=c.id) AS last_visit,
        (SELECT COUNT(*) FROM visits v WHERE v.client_id=c.id AND v.status<>'cancelled') AS n_visits
        FROM clients c WHERE c.name LIKE ? OR c.phone LIKE ? ORDER BY (c.name LIKE ?) DESC, c.name LIMIT 15""",
                      (f"%{s}%", f"%{s}%", f"{s}%")).fetchall()
    return {"items": [dict(r) for r in rows]}


@app.route("/api/slots")
@login_required()
def api_slots():
    """الساعات المحجوزة في يوم معيّن (للقسم في الفرع)، لتظهر في اختيار الساعة."""
    db = get_db()
    br = int(request.args.get("branch") or work_branch())
    q = "SELECT substr(start_at,12,5) AS t, COUNT(*) AS n FROM appointments WHERE substr(start_at,1,10)=? AND branch_id=? AND status='scheduled'"
    args = [request.args.get("date", ""), br]
    if request.args.get("dept"):
        q += " AND dept=?"
        args.append(request.args["dept"])
    return {r["t"]: r["n"] for r in db.execute(q + " GROUP BY t", args)}


def plan_credit(db, pid):
    """التسبيق المتبقّي على خطة حصص: مجموع التسبيقات ناقص الحصص التي دُفعت منه."""
    adv = db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE plan_id=? AND cancelled=0", (pid,)).fetchone()[0]
    used = db.execute("SELECT COALESCE(SUM(price),0) FROM appointments WHERE plan_id=? AND credit_used=1", (pid,)).fetchone()[0]
    return round(adv, 2), round(adv - used, 2)


@app.route("/appointments/quick", methods=["POST"])
@perm_required("appointments")
def appt_quick():
    """موعد جديد في صفحة واحدة: الشخص (ملفه أو تسجيل جديد)، القسم والخدمة، وحصة أو عدة حصص بسعر لكل حصة."""
    db = get_db()
    u = current_user()
    f = request.form
    br = u["branch_id"] or int(f.get("branch_id") or work_branch())
    dept = u["role"] if u["role"] in ("laser", "beauty") else f.get("dept")
    if dept not in branch_depts(br):
        flash("اختر القسم", "err")
        return redirect(url_for("appointments"))
    cid = f.get("client_id")
    if not cid:
        name, phone = f.get("new_name", "").strip(), f.get("new_phone", "").strip()
        dup = find_by_phone(db, phone)
        if dup:
            cid = dup["id"]
            flash(f"الرقم {phone} مسجّل باسم «{dup['name']}»، فأُضيف الموعد إلى ملفه.", "ok")
        elif name:
            cid = db.execute("INSERT INTO clients(name,phone,branch_id,created_at) VALUES(?,?,?,?)",
                             (name, phone, br, now_str())).lastrowid
        else:
            flash("اختر الشخص أو اكتب اسمه", "err")
            return redirect(url_for("appointments"))
    cid = int(cid)
    srv = f.get("service_id") or None
    srow = db.execute("SELECT * FROM services WHERE id=?", (srv or 0,)).fetchone()
    ds, ts, ps = f.getlist("sd"), f.getlist("st"), f.getlist("sp")
    rows = [(d, ts[i] if i < len(ts) else "", ps[i] if i < len(ps) else "") for i, d in enumerate(ds)]
    rows = [r for r in rows if r[0]] or [("", "", "")]
    post = f.get("post_id") or None
    locked = price_locked(u)
    list_price = (srow["price"] or 0) if srow else 0
    if len(rows) == 1 and not f.get("multi"):
        d, t, _ = rows[0]
        if not d:
            flash("اختر التاريخ", "err")
            return redirect(url_for("appointments"))
        db.execute("""INSERT INTO appointments(client_id,branch_id,dept,service_id,start_at,notes,created_by,created_at,post_id)
            VALUES(?,?,?,?,?,?,?,?,?)""", (cid, br, dept, srv, f"{d} {t or '09:00'}", f.get("notes", "").strip(),
                                           u["id"], now_str(), post))
        audit("موعد جديد", f"{d} {t}", br)
        db.commit()
        flash("تم تسجيل الموعد", "ok")
        return redirect(url_for("appointments", date=d))
    title = f.get("title", "").strip() or ((srow["name"] if srow else DEPTS.get(dept)) + f" — {len(rows)} حصص")
    pid = db.execute("""INSERT INTO plans(client_id,branch_id,dept,service_id,post_id,title,total_price,price_mode,
        notes,created_by,created_at,pay_mode) VALUES(?,?,?,?,?,?,0,'session',?,?,?,'session')""",
                     (cid, br, dept, srv, post, title, f.get("notes", "").strip(), u["id"], now_str())).lastrowid
    for i, (d, t, pr) in enumerate(rows):
        price = list_price if (locked or pr.strip() == "") else fnum(pr)
        db.execute("""INSERT INTO appointments(client_id,branch_id,dept,service_id,start_at,status,created_by,
            created_at,plan_id,session_no,price,paid,post_id) VALUES(?,?,?,?,?,'scheduled',?,?,?,?,?,0,?)""",
                   (cid, br, dept, srv, f"{d} {t or '09:00'}" if d else None, u["id"], now_str(), pid, i + 1, price, post))
    db.execute("UPDATE plans SET total_price=(SELECT COALESCE(SUM(price),0) FROM appointments WHERE plan_id=?) WHERE id=?",
               (pid, pid))
    adv = fnum(f.get("advance"))
    audit("حصص جديدة", f"{title}", br)
    if adv > 0 and can_collect(u):
        pay = make_payment(db, br, cid, adv, f.get("method", "cash"), "service", f"تسبيق: {title}", u["id"], dept=dept)
        db.execute("UPDATE payments SET plan_id=? WHERE id=?", (pid, pay))
        db.commit()
        flash(f"تم تسجيل {len(rows)} حصص والتسبيق", "ok")
        return redirect(url_for("receipt", pid=pay))
    db.commit()
    flash(f"تم تسجيل {len(rows)} حصص", "ok")
    return redirect(url_for("plan_view", pid=pid))


# ---------------------------------------------------------------- المواعيد
def services_for(branch_id, dept=None):
    q = "SELECT * FROM services WHERE active=1 AND (branch_id IS NULL OR branch_id=?)"
    args = [branch_id]
    if dept:
        q += " AND dept=?"
        args.append(dept)
    return get_db().execute(q + " ORDER BY COALESCE(category,'ي'), id", args).fetchall()


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
    d = request.args.get("date") or center_today().isoformat()
    rng = request.args.get("range", "day")
    br = scope_branch()
    dept = request.args.get("dept") or (u["role"] if u["role"] in ("laser", "beauty") else "")
    q = """SELECT a.*, c.name AS client, c.phone, s.name AS service, s.price AS sprice, b.name AS branch,
           po.name AS room, pl.title AS plan_title, (SELECT COUNT(*) FROM appointments x WHERE x.plan_id=a.plan_id) AS plan_n
           FROM appointments a JOIN clients c ON c.id=a.client_id LEFT JOIN services s ON s.id=a.service_id
           JOIN branches b ON b.id=a.branch_id LEFT JOIN posts po ON po.id=a.post_id
           LEFT JOIN plans pl ON pl.id=a.plan_id WHERE substr(a.start_at,1,10) BETWEEN ? AND ?"""
    try:
        d0 = datetime.strptime(d, "%Y-%m-%d").date()
    except ValueError:
        d0 = center_today()
        d = d0.isoformat()
    d_end = (d0 + timedelta(days=6)).isoformat() if rng == "week" else d
    args = [d, d_end]
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
    today = center_today()
    return render_template("appointments.html", rows=rows, d=d, br=br, dept=dept, rng=rng, d_end=d_end,
                           t0=today.isoformat(), t1=(today + timedelta(days=1)).isoformat(),
                           slots=WORK_SLOTS, open_form=bool(request.args.get("new") or request.args.get("client_id")),
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
        if st == "noshow" and a["status"] != "noshow":
            db.execute("UPDATE appointments SET missed=COALESCE(missed,0)+1 WHERE id=?", (aid,))
        db.commit()
        if st == "noshow":  # لم تحضر: نقترحو موعد جديد مباشرة
            return redirect(url_for("appt_reschedule", aid=aid))
    return redirect(request.referrer or url_for("appointments"))


WORK_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 18) for m in (0, 30)]


def suggest_slot(db, a, start_day=None):
    """أقرب يوم عمل فيه نفس الساعة فارغة في نفس الغرفة (ولا أقرب ساعة فارغة في ذاك اليوم)."""
    t0 = (a["start_at"] or "")[11:16] or "09:00"
    dur = appt_duration(a["service_id"])
    d = start_day or (center_today() + timedelta(days=1))
    for _ in range(21):
        d = next_free_day(d)
        times = [t0] + sorted(WORK_SLOTS, key=lambda x: abs(int(x[:2]) * 60 + int(x[3:]) - int(t0[:2]) * 60 - int(t0[3:5])))
        for t in times:
            at = f"{d.isoformat()} {t}"
            if not a["post_id"] or not room_conflicts(db, a["post_id"], at, dur, exclude_id=a["id"]):
                return at
        d += timedelta(days=1)
    return f"{next_free_day(center_today() + timedelta(days=1)).isoformat()} {t0}"


def following_sessions(db, a):
    if not a["plan_id"]:
        return []
    return db.execute("""SELECT * FROM appointments WHERE plan_id=? AND session_no>? AND status='scheduled'
        AND start_at IS NOT NULL ORDER BY session_no""", (a["plan_id"], a["session_no"] or 0)).fetchall()


def shift_plan(at_old, at_new, rows):
    """الحصص اللي من بعد تتأخر بنفس عدد الأيام (وتتفادى يوم الراحة)، وتبقى في نفس الساعة."""
    try:
        delta = (datetime.strptime(at_new[:10], "%Y-%m-%d").date() - datetime.strptime(at_old[:10], "%Y-%m-%d").date()).days
    except (TypeError, ValueError):
        return []
    out, last = [], datetime.strptime(at_new[:10], "%Y-%m-%d").date()
    for r in rows:
        d0 = datetime.strptime(r["start_at"][:10], "%Y-%m-%d").date()
        d1 = next_free_day(max(d0 + timedelta(days=max(delta, 0)), last + timedelta(days=1)))
        last = d1
        out.append((r, f"{d1.isoformat()} {r['start_at'][11:16]}"))
    return out


@app.route("/appointments/<int(signed=True):aid>/reschedule", methods=["GET", "POST"])
@login_required()
def appt_reschedule(aid):
    """الزبونة لم تحضر: البرنامج يقترح أقرب موعد فارغ في نفس الغرفة، والحصص اللي من بعد تتأخر وحدها."""
    db = get_db()
    u = current_user()
    a = db.execute("""SELECT a.*, c.name AS client, c.phone, s.name AS service, pl.title AS plan_title, po.name AS room,
        (SELECT COUNT(*) FROM appointments x WHERE x.plan_id=a.plan_id) AS plan_n
        FROM appointments a JOIN clients c ON c.id=a.client_id LEFT JOIN services s ON s.id=a.service_id
        LEFT JOIN plans pl ON pl.id=a.plan_id LEFT JOIN posts po ON po.id=a.post_id WHERE a.id=?""", (aid,)).fetchone() or abort(404)
    if u["role"] != "admin" and a["branch_id"] != u["branch_id"]:
        abort(403)
    need("appointments")
    if request.method == "POST":
        d, t = request.form.get("date"), request.form.get("time") or "09:00"
        if not d:
            flash("اختر التاريخ", "err")
            return redirect(url_for("appt_reschedule", aid=aid))
        at = f"{d} {t}"
        if a["post_id"] and not request.form.get("force"):
            cf = room_conflicts(db, a["post_id"], at, appt_duration(a["service_id"]), exclude_id=aid)
            if cf:
                flash("الغرفة محجوزة في هذا الوقت: " + "، ".join(f"{x['start_at'][11:16]} {x['client']}" for x in cf)
                      + " — اختر وقتًا آخر أو أشّر على «حجز رغم التعارض».", "err")
                return redirect(url_for("appt_reschedule", aid=aid, at=at))
        old = a["start_at"]
        if a["status"] == "scheduled" and old and old < center_now().strftime("%Y-%m-%d %H:%M"):
            db.execute("UPDATE appointments SET missed=COALESCE(missed,0)+1 WHERE id=?", (aid,))
        db.execute("""UPDATE appointments SET start_at=?, status='scheduled', sms_sent_at=NULL, morning_sent_at=NULL
            WHERE id=?""", (at, aid))
        moved = 0
        if request.form.get("shift") and old:
            for r, nat in shift_plan(old, at, following_sessions(db, a)):
                if nat != r["start_at"]:
                    db.execute("UPDATE appointments SET start_at=?, sms_sent_at=NULL, morning_sent_at=NULL WHERE id=?",
                               (nat, r["id"]))
                    moved += 1
        audit("موعد جديد بعد غياب", f"{a['client']}: {old or '-'} ← {at}" + (f" (+{moved} حصة تأخرت)" if moved else ""),
              a["branch_id"])
        db.commit()
        flash(f"الموعد الجديد: {d} على {t}" + (f" — و{moved} حصة من بعد تأخرت معاها" if moved else ""), "ok")
        return redirect(url_for("appointments", date=d))
    at = request.args.get("at") or suggest_slot(db, a)
    preview = shift_plan(a["start_at"], at, following_sessions(db, a)) if a["start_at"] else []
    return render_template("appt_reschedule.html", a=a, at=at, preview=preview)


@app.route("/appointments/missed")
@perm_required("appointments")
def appts_missed():
    """الحصص الفائتة والزبونة لم تحضر، ولم تأخذ موعدًا جديدًا بعد."""
    db = get_db()
    u = current_user()
    br = u["branch_id"] or scope_branch()
    q = """SELECT a.*, c.name AS client, c.phone, s.name AS service, pl.title AS plan_title, b.name AS branch,
        (SELECT COUNT(*) FROM appointments x WHERE x.plan_id=a.plan_id) AS plan_n
        FROM appointments a JOIN clients c ON c.id=a.client_id LEFT JOIN services s ON s.id=a.service_id
        LEFT JOIN plans pl ON pl.id=a.plan_id JOIN branches b ON b.id=a.branch_id
        WHERE ((a.status='scheduled' AND a.start_at < ?) OR a.status='noshow') AND a.start_at >= ?
        AND NOT EXISTS (SELECT 1 FROM visits v WHERE v.appointment_id=a.id)"""
    args = [center_now().strftime("%Y-%m-%d %H:%M"), (center_today() - timedelta(days=60)).isoformat()]
    if br:
        q += " AND a.branch_id=?"
        args.append(br)
    if u["role"] in ("laser", "beauty"):
        q += " AND a.dept=?"
        args.append(u["role"])
    rows = db.execute(q + " ORDER BY a.start_at DESC", args).fetchall()
    return render_template("appts_missed.html", rows=rows, br=br)


@app.route("/appointments/<int(signed=True):aid>/arrived", methods=["POST"])
@login_required()
def appt_arrived(aid):
    """«الزبونة وصلت»: تتبعث للغرفة كزيارة. الغرفة تشوف رقم الحصة، وتزيد واش طلبت الزبونة.
    ثمن الحصة يدخل في الزيارة إذا ما تخلّصش (الدفع بالحصة)، وإلا يبان «مدفوعة»."""
    db = get_db()
    u = current_user()
    a = db.execute("""SELECT a.*, s.name AS service, pl.title AS plan_title, pl.pay_mode,
        (SELECT COUNT(*) FROM appointments x WHERE x.plan_id=a.plan_id) AS plan_n
        FROM appointments a LEFT JOIN services s ON s.id=a.service_id LEFT JOIN plans pl ON pl.id=a.plan_id
        WHERE a.id=?""", (aid,)).fetchone() or abort(404)
    if u["role"] != "admin" and a["branch_id"] != u["branch_id"]:
        abort(403)
    need("appointments")
    ex = db.execute("SELECT id FROM visits WHERE appointment_id=? AND status IN ('waiting','treating')", (aid,)).fetchone()
    if ex:
        return redirect(url_for("visit_view", vid=ex["id"]))
    target = a["dept"] if a["dept"] in ("laser", "beauty") else "reception"
    if target not in branch_depts(a["branch_id"]) and target != "reception":
        target = "reception"
    title = a["plan_title"] or a["service"] or "موعد"
    label = f"{title} — حصة {a['session_no']} من {a['plan_n']}" if a["plan_id"] else title
    pending_plan = a["plan_id"] and db.execute("SELECT 1 FROM charges WHERE plan_id=? AND status='pending'",
                                               (a["plan_id"],)).fetchone()
    price = 0 if (a["paid"] or (a["pay_mode"] == "full") or pending_plan) else (
        (a["price"] or 0) if a["plan_id"] else service_price(a["service_id"]))
    if a["plan_id"] and db.execute("SELECT 1 FROM charges WHERE appointment_id=? AND status='pending'", (aid,)).fetchone():
        price = 0  # ثمنها أُرسل للاستقبال من قبل
    from_credit = False
    if a["plan_id"] and price > 0 and plan_credit(db, a["plan_id"])[1] >= price - 0.001:
        db.execute("UPDATE appointments SET paid=1, credit_used=1 WHERE id=?", (aid,))  # تُخصم من التسبيق
        price, from_credit = 0, True
    vid = db.execute("""INSERT INTO visits(client_id,branch_id,target,request,status,created_by,created_at,appointment_id)
        VALUES(?,?,?,?,'waiting',?,?,?)""", (a["client_id"], a["branch_id"], target,
                                             (a["notes"] or "")[:300], u["id"], now_str(), aid)).lastrowid
    note = "" if price else (" (مدفوعة من التسبيق)" if from_credit else " (مدفوعة)" if a["paid"] else " (ضمن الباقة)" if a["plan_id"] else "")
    db.execute("""INSERT INTO visit_items(visit_id,kind,service_id,description,qty,unit_price,stage,added_by,created_at,appt_id)
        VALUES(?,'service',?,?,1,?,'reception',?,?,?)""", (vid, a["service_id"], label + note, price, u["id"], now_str(), aid))
    audit("وصول زبون لموعد", label, a["branch_id"])
    db.commit()
    flash(f"تم إرسال الزبونة إلى {VISIT_TARGETS.get(target, '')}", "ok")
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
    q = """SELECT ch.*, c.name AS client, c.phone, b.name AS branch, us.full_name AS by_name,
           (SELECT CASE ap.kind WHEN 'discount' THEN 'طلب تخفيض ' || ap.amount ELSE 'طلب إلغاء' END FROM approvals ap
            WHERE ap.ref_id=ch.id AND ap.kind IN ('discount','cancel_charge') AND ap.status='pending' LIMIT 1) AS req
           FROM charges ch LEFT JOIN clients c ON c.id=ch.client_id JOIN branches b ON b.id=ch.branch_id
           LEFT JOIN users us ON us.id=ch.created_by WHERE ch.status='pending'"""
    args = []
    if current_user()["role"] in ("laser", "beauty"):
        q += " AND ch.dept=?"
        args.append(current_user()["role"])
    if br:
        q += " AND ch.branch_id=?"
        args.append(br)
    today = center_today().isoformat()
    allp = db.execute(q + " ORDER BY ch.id", args).fetchall()
    # كل نهار وحدو: مبالغ الأيام الفايتة ما تبانش مع اليوم (تبان في جدول وحدها كي تطلبها)
    show_old = bool(request.args.get("old"))
    pending = [c for c in allp if (c["created_at"] or "")[:10] >= today or show_old]
    old_pending = sum(1 for c in allp if (c["created_at"] or "")[:10] < today)
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
    if current_user()["role"] in ("laser", "beauty"):
        qv += " AND v.target=?"  # لا تظهر زبائن المديرة في غرفة التجميل/الليزر
        av.append(current_user()["role"])
    allv = db.execute(qv + " ORDER BY v.id", av).fetchall()
    open_visits = [v for v in allv if v["created_at"][:10] >= today or show_old]
    old_visits = sum(1 for v in allv if v["created_at"][:10] < today)
    return render_template("reception.html", pending=pending, todays=todays, total=total, br=br,
                           open_visits=open_visits, old_pending=old_pending, old_visits=old_visits, show_old=show_old)


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
        # حصة خطة دُفع ثمنها مع الزيارة
        db.execute("""UPDATE appointments SET paid=1, payment_id=? WHERE paid=0 AND id IN
            (SELECT appt_id FROM visit_items WHERE visit_id=? AND appt_id IS NOT NULL AND unit_price>0)""", (pid, ch["visit_id"]))
    if ch["plan_id"]:  # الباقة كاملة مدفوعة: كل الحصص مدفوعة
        db.execute("UPDATE appointments SET paid=1, payment_id=? WHERE plan_id=? AND paid=0", (pid, ch["plan_id"]))
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
    approved = ch["discount"] or 0  # تخفيض وافقت عليه المديرة
    disc = approved if price_locked(u) else min(max(fnum(request.form.get("discount")), approved), ch["amount"])
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
    if u["role"] != "admin":  # العامل لا يلغي وحده: يطلب من المديرة
        request_approval(db, "cancel_charge", ch["id"], ch["branch_id"], ch["amount"],
                         request.form.get("reason", ""), f"{ch['description'] or ''}")
        db.commit()
        flash("أُرسل طلب الإلغاء للمديرة. يبقى المبلغ حتى توافق.", "ok")
        return redirect(url_for("reception"))
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


# ---------------------------------------------------------------- موافقة المديرة
APPROVAL_KINDS = {"discount": "تخفيض", "cancel_charge": "إلغاء مبلغ", "cancel_payment": "إلغاء وصل",
                  "plan_price": "سعر باقة", "cxl_payment": "إلغاء وصل", "cxl_visit": "إلغاء زيارة",
                  "cxl_charge": "إلغاء مبلغ", "cxl_expense": "إلغاء مصروف", "cxl_stock": "إلغاء حركة مخزون",
                  "cxl_day": "إلغاء كل عمليات اليوم"}


def request_approval(db, kind, ref_id, branch_id, amount, reason, info):
    u = current_user()
    if db.execute("SELECT 1 FROM approvals WHERE kind=? AND ref_id=? AND status='pending'", (kind, ref_id)).fetchone():
        return
    db.execute("""INSERT INTO approvals(branch_id,kind,ref_id,amount,reason,status,requested_by,requested_at,info)
        VALUES(?,?,?,?,?,'pending',?,?,?)""", (branch_id, kind, ref_id, amount, (reason or "").strip()[:300],
                                                u["id"], now_str(), (info or "")[:300]))
    audit("طلب موافقة", f"{APPROVAL_KINDS[kind]} {amount:g} — {info}", branch_id)
    if AUTO_SMS and setting("approvals_sms") == "1" and setting("sms_enabled") == "1" and setting("manager_phone"):
        msg = f"{setting('center_name')}: طلب {APPROVAL_KINDS[kind]} {amount:g} من {u['full_name'] or u['username']}" \
              + (f" - {reason.strip()}" if (reason or "").strip() else "")

        def go(m=msg):
            try:
                con = connect()
                send_sms(con, setting("manager_phone"), m)
                con.close()
            except Exception:
                pass
        if not sync.NODE:
            threading.Thread(target=go, daemon=True).start()


def pending_approvals(db):
    return db.execute("SELECT COUNT(*) FROM approvals WHERE status='pending'").fetchone()[0]


@app.route("/approvals/request", methods=["POST"])
@login_required()
def approval_request():
    db = get_db()
    u = current_user()
    kind = request.form.get("kind")
    ref = request.form.get("ref_id", "")
    if kind == "discount":
        ch = db.execute("SELECT * FROM charges WHERE id=? AND status='pending'", (ref,)).fetchone() or abort(404)
        check_charge_access(ch, u)
        amt = min(max(fnum(request.form.get("amount")), 0), ch["amount"])
        if amt <= 0:
            flash("اكتب مبلغ التخفيض", "err")
            return redirect(request.referrer or url_for("reception"))
        request_approval(db, "discount", ch["id"], ch["branch_id"], amt, request.form.get("reason"),
                         f"{ch['description'] or ''} ({ch['amount']:g})")
    elif kind == "cancel_payment":
        p = db.execute("SELECT * FROM payments WHERE id=? AND cancelled=0", (ref,)).fetchone() or abort(404)
        if u["role"] != "admin" and p["branch_id"] != u["branch_id"]:
            abort(403)
        request_approval(db, "cancel_payment", p["id"], p["branch_id"], p["amount"], request.form.get("reason"),
                         f"وصل {rid_filter(p['id'])}: {p['description'] or ''}")
    else:
        abort(400)
    db.commit()
    flash("أُرسل الطلب للمديرة. يظهر لك الجواب هنا.", "ok")
    return redirect(request.referrer or url_for("reception"))


@app.route("/approvals", methods=["GET", "POST"])
@login_required("admin")
def approvals():
    db = get_db()
    if request.method == "POST":
        a_ = db.execute("SELECT * FROM approvals WHERE id=? AND status='pending'", (request.form.get("id"),)).fetchone()
        dec = request.form.get("decision")
        if a_ and dec in ("approved", "rejected"):
            ok = True
            if dec == "approved":
                if a_["kind"] == "discount":
                    ch = db.execute("SELECT * FROM charges WHERE id=? AND status='pending'", (a_["ref_id"],)).fetchone()
                    ok = bool(ch)
                    if ch:
                        db.execute("UPDATE charges SET discount=? WHERE id=?", (min(a_["amount"], ch["amount"]), ch["id"]))
                elif a_["kind"] == "cancel_charge":
                    ok = db.execute("UPDATE charges SET status='cancelled' WHERE id=? AND status='pending'",
                                    (a_["ref_id"],)).rowcount > 0
                elif a_["kind"] == "cancel_payment":
                    ok = cancel_payment_now(db, a_["ref_id"])
                elif a_["kind"] == "plan_price":
                    ok = set_plan_price(db, a_["ref_id"], a_["amount"])
                elif a_["kind"] == "cxl_day":
                    day = (a_["info"] or "")[:10]
                    ok = bool(day) and cancel_day(db, a_["ref_id"], day, a_["reason"], a_["requested_by"]) >= 0
                elif a_["kind"].startswith("cxl_"):
                    ok = cancel_op(db, a_["kind"][4:], a_["ref_id"], a_["reason"], a_["requested_by"])
            if not ok:
                flash("تعذّر التنفيذ: العملية تغيّرت (دُفعت أو أُلغيت سابقًا)", "err")
                dec, note = "rejected", "لم يعد ممكنًا"
            else:
                note = request.form.get("note", "").strip()
            db.execute("UPDATE approvals SET status=?, decided_by=?, decided_at=?, note=? WHERE id=?",
                       (dec, current_user()["id"], now_str(), note, a_["id"]))
            audit("موافقة" if dec == "approved" else "رفض", f"{APPROVAL_KINDS[a_['kind']]} {a_['amount']:g} — {a_['info']}",
                  a_["branch_id"])
            if ok:
                flash("تمت الموافقة ونُفّذت" if dec == "approved" else "تم الرفض", "ok")
            db.commit()
        return redirect(url_for("approvals"))
    rows = db.execute("""SELECT a.*, u.full_name AS by_name, b.name AS branch FROM approvals a
        LEFT JOIN users u ON u.id=a.requested_by LEFT JOIN branches b ON b.id=a.branch_id
        ORDER BY a.status='pending' DESC, a.id DESC LIMIT 200""").fetchall()
    return render_template("approvals.html", rows=rows)


def set_plan_price(db, plan_id, total):
    """سعر جديد للباقة: يتوزع على الحصص غير المدفوعة، ويتعدّل مبلغ الباقة المنتظر في الاستقبال."""
    p = db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
    if not p:
        return False
    paid = db.execute("SELECT COALESCE(SUM(price),0) FROM appointments WHERE plan_id=? AND paid=1", (plan_id,)).fetchone()[0]
    unpaid = db.execute("SELECT id FROM appointments WHERE plan_id=? AND paid=0 ORDER BY session_no", (plan_id,)).fetchall()
    rest = round(total - paid, 2)
    if rest < 0:
        return False
    if unpaid:
        each = round(rest / len(unpaid), 2)
        for i, x in enumerate(unpaid):
            v = each if i < len(unpaid) - 1 else round(rest - each * (len(unpaid) - 1), 2)
            db.execute("UPDATE appointments SET price=? WHERE id=?", (v, x["id"]))
    db.execute("UPDATE plans SET total_price=?, price_mode='total' WHERE id=?", (total, plan_id))
    db.execute("UPDATE charges SET amount=? WHERE plan_id=? AND status='pending'", (rest, plan_id))
    return True


def next_free_day(d):
    """أول يوم عمل (يتجنب يوم الراحة الأسبوعي، الجمعة من الأصل)."""
    off = {int(x) for x in (setting("weekly_off") or "4").split(",") if x.strip().isdigit()}
    for _ in range(7):
        if d.weekday() not in off:
            return d
        d += timedelta(days=1)
    return d


def schedule_next_session(db, appt):
    """بعد ما تكمل حصة: إذا الحصة الجاية بلا تاريخ، نعطيها تاريخ (اليوم + المدة بين الحصص)."""
    if not appt["plan_id"]:
        return None
    nx = db.execute("""SELECT * FROM appointments WHERE plan_id=? AND session_no>? AND status='scheduled'
        ORDER BY session_no LIMIT 1""", (appt["plan_id"], appt["session_no"] or 0)).fetchone()
    if not nx or nx["start_at"]:
        return None
    srv = db.execute("SELECT pkg_interval FROM services WHERE id=?", (appt["service_id"],)).fetchone()
    step = (srv["pkg_interval"] if srv and srv["pkg_interval"] else 0) or 7
    t = (appt["start_at"] or now_str())[11:16] or "09:00"
    d = next_free_day(center_today() + timedelta(days=step))
    at = f"{d.isoformat()} {t}"
    db.execute("UPDATE appointments SET start_at=? WHERE id=?", (at, nx["id"]))
    return at


def cancel_payment_now(db, pid):
    p = db.execute("SELECT * FROM payments WHERE id=? AND cancelled=0", (pid,)).fetchone()
    if not p:
        return False
    audit("إلغاء وصل", f"وصل {rid_filter(pid)} — {p['amount']:g} — {p['description'] or ''}", p["branch_id"])
    db.execute("UPDATE payments SET cancelled=1 WHERE id=?", (pid,))
    for it in db.execute("SELECT * FROM sale_items WHERE payment_id=?", (pid,)).fetchall():
        move_stock(db, it["product_id"], p["branch_id"], it["qty"], f"إلغاء الوصل {rid_filter(pid)}")
    db.execute("UPDATE charges SET status='pending', payment_id=NULL WHERE payment_id=?", (pid,))
    db.execute("UPDATE appointments SET paid=0, payment_id=NULL WHERE payment_id=?", (pid,))
    db.execute("""UPDATE visits SET status='done' WHERE status='paid' AND id IN
        (SELECT visit_id FROM charges WHERE payment_id IS NULL AND status='pending' AND visit_id IS NOT NULL)""")
    return True


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


def can_fix(branch_id, created_at, u=None):
    """تصحيح أو إلغاء مباشر: المديرة دائمًا، والعامل لعمليات اليوم في فرعه (إن سمحت المديرة بذلك)."""
    u = u or current_user()
    if not u:
        return False
    if u["role"] == "admin":
        return True
    return (has_perm("cancel_ops", u) and branch_id == u["branch_id"] and setting("staff_direct_cancel") != "0"
            and (created_at or "")[:10] == center_today().isoformat())


def client_is_empty(db, cid):
    for q in ("SELECT 1 FROM visits WHERE client_id=?", "SELECT 1 FROM payments WHERE client_id=? AND cancelled=0",
              "SELECT 1 FROM appointments WHERE client_id=? AND status<>'cancelled'", "SELECT 1 FROM plans WHERE client_id=?",
              "SELECT 1 FROM course_trainees WHERE client_id=?", "SELECT 1 FROM charges WHERE client_id=? AND status IN ('pending','debt')"):
        if db.execute(q + " LIMIT 1", (cid,)).fetchone():
            return False
    return True


@app.route("/clients/<int(signed=True):cid>/delete", methods=["POST"])
@perm_required("clients_edit")
def client_delete(cid):
    """حذف ملف سُجّل خطأً (اسم مكرر أو خاطئ) ما دام فارغًا: لا زيارات ولا دفعات ولا مواعيد."""
    db = get_db()
    c = db.execute("SELECT * FROM clients WHERE id=?", (cid,)).fetchone() or abort(404)
    if not client_is_empty(db, cid):
        flash("لا يمكن حذف هذا الملف لأن فيه عمليات. صحّحي الاسم أو الهاتف بدلًا من ذلك.", "err")
        return redirect(url_for("client_view", cid=cid))
    for t_ in ("client_notes", "client_photos", "skin_cards", "appointments"):
        db.execute(f"DELETE FROM {t_} WHERE client_id=?", (cid,))
    db.execute("DELETE FROM clients WHERE id=?", (cid,))
    audit("حذف ملف سُجّل خطأً", f"{c['name']} {c['phone'] or ''}", c["branch_id"])
    db.commit()
    flash(f"حُذف الملف «{c['name']}»", "ok")
    return redirect(url_for("clients"))


@app.route("/payments/<int(signed=True):pid>/fix", methods=["GET", "POST"])
@login_required()
def payment_fix(pid):
    """تصحيح وصل أُدخل خطأً: الزبون، المبلغ، طريقة الدفع، البيان. يبقى أثر التصحيح ظاهرًا."""
    db = get_db()
    u = current_user()
    p = db.execute("""SELECT p.*, c.name AS client, c.phone FROM payments p LEFT JOIN clients c ON c.id=p.client_id
        WHERE p.id=? AND p.cancelled=0""", (pid,)).fetchone() or abort(404)
    if not can_fix(p["branch_id"], p["created_at"], u):
        flash("لا يمكنك تصحيح هذا الوصل مباشرة (ليس من عمليات اليوم في فرعك). اطلبي ذلك من المديرة.", "err")
        return redirect(url_for("receipt", pid=pid))
    has_items = db.execute("SELECT 1 FROM sale_items WHERE payment_id=?", (pid,)).fetchone()
    if request.method == "POST":
        f = request.form
        changes = []
        new_client = f.get("client_id") or p["client_id"]
        if str(new_client or "") != str(p["client_id"] or ""):
            nc = db.execute("SELECT name FROM clients WHERE id=?", (new_client,)).fetchone()
            if nc:
                changes.append(f"الزبون: {p['client'] or '-'} ← {nc['name']}")
                db.execute("UPDATE payments SET client_id=? WHERE id=?", (int(new_client), pid))
                db.execute("UPDATE charges SET client_id=? WHERE payment_id=?", (int(new_client), pid))
        amount = fnum(f.get("amount"), p["amount"])
        if not has_items and amount > 0 and abs(amount - p["amount"]) > 0.001:
            changes.append(f"المبلغ: {p['amount']:g} ← {amount:g}")
            db.execute("UPDATE payments SET amount=? WHERE id=?", (amount, pid))
        if f.get("method") in METHODS and f.get("method") != p["method"]:
            changes.append(f"الدفع: {METHODS.get(p['method'], p['method'])} ← {METHODS[f['method']]}")
            db.execute("UPDATE payments SET method=? WHERE id=?", (f["method"], pid))
        desc = f.get("description", "").strip()
        if desc and desc != (p["description"] or ""):
            changes.append("البيان")
            db.execute("UPDATE payments SET description=? WHERE id=?", (desc, pid))
        if changes:
            note = f"صُحّح في {now_str()[:16]} بواسطة {u['full_name'] or u['username']}: " + "، ".join(changes)
            if f.get("reason", "").strip():
                note += f" (السبب: {f['reason'].strip()})"
            db.execute("UPDATE payments SET fix_note=TRIM(COALESCE(fix_note,'') || ' ' || ?) WHERE id=?", (note, pid))
            audit("تصحيح وصل", f"وصل {rid_filter(pid)} — " + "، ".join(changes), p["branch_id"])
            db.commit()
            flash("تم تصحيح الوصل", "ok")
        else:
            flash("لم يتغيّر شيء", "ok")
        return redirect(url_for("receipt", pid=pid))
    sel = {"id": p["client_id"], "name": p["client"], "phone": p["phone"]} if p["client_id"] else None
    return render_template("payment_fix.html", p=p, has_items=has_items, sel_client=sel)


@app.route("/payments/<int(signed=True):pid>/void", methods=["POST"])
@login_required()
def payment_void(pid):
    """إلغاء وصل: مباشرة لعمليات اليوم، أو طلب للمديرة لما قبلها. يبقى محفوظًا في «العمليات الملغاة»."""
    db = get_db()
    u = current_user()
    p = db.execute("SELECT * FROM payments WHERE id=? AND cancelled=0", (pid,)).fetchone() or abort(404)
    reason = request.form.get("reason", "").strip() or "خطأ في الإدخال"
    if can_fix(p["branch_id"], p["created_at"], u):
        cancel_op(db, "payment", pid, reason, u["id"])
        audit("إلغاء وصل", f"وصل {rid_filter(pid)} — {p['amount']:g} — {reason}", p["branch_id"])
        db.commit()
        flash("أُلغي الوصل. هو محفوظ في «العمليات الملغاة» ولا يدخل في الحسابات.", "ok")
    else:
        if u["role"] != "admin" and p["branch_id"] != u["branch_id"]:
            abort(403)
        request_approval(db, "cxl_payment", pid, p["branch_id"], p["amount"] or 0, reason,
                         f"وصل {rid_filter(pid)} — {p['description'] or ''}")
        db.commit()
        flash("أُرسل طلب الإلغاء إلى المديرة", "ok")
    return redirect(url_for("receipt", pid=pid))


@app.route("/appointments/<int(signed=True):aid>/edit", methods=["GET", "POST"])
@perm_required("appointments")
def appt_edit(aid):
    """تصحيح موعد: الخدمة، القسم، التاريخ والساعة، الغرفة، الملاحظة، وسعر الحصة."""
    db = get_db()
    u = current_user()
    a = db.execute("""SELECT a.*, c.name AS client, c.phone FROM appointments a JOIN clients c ON c.id=a.client_id
        WHERE a.id=?""", (aid,)).fetchone() or abort(404)
    if u["role"] != "admin" and a["branch_id"] != u["branch_id"]:
        abort(403)
    if request.method == "POST":
        f = request.form
        dept = f.get("dept") if f.get("dept") in branch_depts(a["branch_id"]) else a["dept"]
        if u["role"] in ("laser", "beauty"):
            dept = a["dept"]
        at = f"{f.get('date')} {f.get('time') or '09:00'}" if f.get("date") else a["start_at"]
        price = a["price"]
        if a["plan_id"] and not a["paid"] and not price_locked(u) and f.get("price", "").strip() != "":
            price = fnum(f.get("price"))
        db.execute("""UPDATE appointments SET dept=?, service_id=?, start_at=?, post_id=?, notes=?, price=? WHERE id=?""",
                   (dept, f.get("service_id") or None, at, f.get("post_id") or None, f.get("notes", "").strip(), price, aid))
        if at != a["start_at"]:
            db.execute("UPDATE appointments SET sms_sent_at=NULL, morning_sent_at=NULL WHERE id=?", (aid,))
        if a["plan_id"]:
            db.execute("""UPDATE plans SET total_price=(SELECT COALESCE(SUM(price),0) FROM appointments WHERE plan_id=?)
                WHERE id=? AND price_mode='session'""", (a["plan_id"], a["plan_id"]))
        audit("تصحيح موعد", f"{a['client']} — {a['start_at'] or ''} ← {at}", a["branch_id"])
        db.commit()
        flash("تم تصحيح الموعد", "ok")
        return redirect(url_for("appointments", date=(at or "")[:10] or None))
    return render_template("appt_edit.html", a=a, depts=branch_depts(a["branch_id"]),
                           services=services_for(a["branch_id"]), posts=posts_for(a["branch_id"]), slots=WORK_SLOTS)


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
    return render_template("receipt.html", p=p, items=items, vitems=vitems, rest=rest,
                           fixable=can_fix(p["branch_id"], p["created_at"]))


# ---------------------------------------------------------------- نقطة البيع (منتجات)
def move_stock(db, product_id, branch_id, qty, reason, uid=None, kind=None, dept=None, visit_id=None):
    db.execute("INSERT OR IGNORE INTO stock(product_id,branch_id,qty) VALUES(?,?,0)", (product_id, branch_id))
    db.execute("UPDATE stock SET qty=qty+? WHERE product_id=? AND branch_id=?", (qty, product_id, branch_id))
    db.execute("""INSERT INTO stock_moves(product_id,branch_id,qty,reason,user_id,created_at,kind,dept,visit_id)
        VALUES(?,?,?,?,?,?,?,?,?)""", (product_id, branch_id, qty, reason, uid, now_str(), kind, dept, visit_id))


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
            pr = db.execute("SELECT * FROM products WHERE id=? AND active=1 AND COALESCE(usage,'sale')<>'use'",
                            (it.get("id"),)).fetchone()
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
        LEFT JOIN stock s ON s.product_id=p.id AND s.branch_id=? WHERE p.active=1 AND COALESCE(p.usage,'sale')<>'use'
        ORDER BY p.category, p.name""", (br,)).fetchall()
    return render_template("pos.html", prods=[dict(p, ic=icons.item_icon(p["name"], "product")) for p in prods], br=br)


# ---------------------------------------------------------------- الصندوق المركزي
def cash_query(args):
    d1 = args.get("from") or center_today().isoformat()
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
    rooms = room_accounts(d1, d2, br, valid)
    return render_template("cashbox.html", rows=rows, total=total, d1=d1, d2=d2, br=br,
                           kind=request.args.get("kind", ""), by_branch=by_branch,
                           by_kind=by_kind, by_method=by_method, rooms=rooms)


def room_accounts(d1, d2, br, valid):
    """حساب كل غرفة/قسم في كل فرع:
    - المداخيل: من أين جاء المال (الحجامة، الليزر، التجميل، علاج المديرة، بيع المنتجات...).
    - الصناديق: من استلم المال فعلًا (صندوق الاستقبال، صندوق غرفة التجميل...) ونقدًا كم.
    - مواد العمل المستهلكة في كل غرفة (بسعر الشراء)."""
    db = get_db()
    ids = [r["id"] for r in valid]
    charges, vitems = {}, {}
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        for c in db.execute(f"""SELECT ch.payment_id, ch.visit_id, ch.amount - COALESCE(ch.discount,0) AS amt, ch.dept,
                s.kind, v.target FROM charges ch LEFT JOIN services s ON s.id=ch.service_id
                LEFT JOIN visits v ON v.id=ch.visit_id
                WHERE ch.payment_id IN ({','.join('?' * len(chunk))})""", chunk):
            charges.setdefault(c["payment_id"], []).append(c)
    vids = sorted({c["visit_id"] for cs in charges.values() for c in cs if c["visit_id"]})
    for i in range(0, len(vids), 500):
        chunk = vids[i:i + 500]
        for it in db.execute(f"""SELECT vi.visit_id, vi.qty*vi.unit_price AS amt, vi.product_id, s.kind
                FROM visit_items vi LEFT JOIN services s ON s.id=vi.service_id
                WHERE vi.visit_id IN ({','.join('?' * len(chunk))})""", chunk):
            vitems.setdefault(it["visit_id"], []).append(it)
    out = {}

    def sec_of(kind, dept, target, product=False):
        if product:
            return "product"
        if target == "director":
            return "director"
        if kind in ("hijama", "herbs", "laser", "beauty", "course"):
            return kind
        if target in ("laser", "beauty"):
            return target
        return dept if dept in ("laser", "beauty") else "other"

    def charge_parts(c):
        """أجزاء المبلغ حسب الغرفة: زيارة فيها حجامة + منتج تُقسم على الحجامة وبيع المنتجات."""
        net = max(c["amt"] or 0, 0)
        its = vitems.get(c["visit_id"]) if c["visit_id"] else None
        if its:
            tot = sum(max(x["amt"] or 0, 0) for x in its)
            if tot > 0:
                return [(sec_of(x["kind"], c["dept"], c["target"], bool(x["product_id"])), net * max(x["amt"] or 0, 0) / tot)
                        for x in its]
        return [(sec_of(c["kind"], c["dept"], c["target"]), net)]

    for r in valid:
        b = out.setdefault(r["branch"], {"income": {}, "boxes": {}, "use": {}, "total": 0})
        b["total"] += r["amount"]
        box = b["boxes"].setdefault(r["dept"] or "reception", {"total": 0, "cash": 0, "n": 0})
        box["total"] += r["amount"]
        box["n"] += 1
        if r["method"] == "cash":
            box["cash"] += r["amount"]
        parts = []
        chs = charges.get(r["id"]) or []
        s = sum(max(c["amt"] or 0, 0) for c in chs)
        if r["kind"] == "product":
            parts = [("product", r["amount"])]
        elif r["kind"] == "course":
            parts = [("course", r["amount"])]
        elif chs and s > 0:
            parts = [(k, r["amount"] * v / s) for c in chs for k, v in charge_parts(c)]
        else:
            parts = [(r["dept"] if r["dept"] in ("laser", "beauty") else "other", r["amount"])]
        for k, v in parts:
            e = b["income"].setdefault(k, {"amount": 0, "n": 0})
            e["amount"] += v
            e["n"] += 1
    # مواد العمل المستهلكة
    q = """SELECT b.name AS branch, m.dept, SUM(-m.qty * COALESCE(p.cost_price,0)) AS cost, COUNT(*) AS n
           FROM stock_moves m JOIN products p ON p.id=m.product_id JOIN branches b ON b.id=m.branch_id
           WHERE m.kind='use' AND COALESCE(m.cancelled,0)=0 AND substr(m.created_at,1,10) BETWEEN ? AND ?"""
    args = [d1, d2]
    if br:
        q += " AND m.branch_id=?"
        args.append(br)
    for u in db.execute(q + " GROUP BY b.name, m.dept", args):
        b = out.setdefault(u["branch"], {"income": {}, "boxes": {}, "use": {}, "total": 0})
        b["use"][u["dept"] or "reception"] = {"cost": u["cost"] or 0, "n": u["n"]}
    for b in out.values():
        b["income"] = dict(sorted(b["income"].items(), key=lambda kv: -kv[1]["amount"]))
    return out


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
    limit = (center_today() + timedelta(days=days)).isoformat()
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
        d["expired"] = bool(d["expiry"]) and d["expiry"] < center_today().isoformat()
        d["suggest"] = max(0, d["min_qty"] * 2 - d["qty"]) if d["low"] else 0
        rows.append(d)
    return rows


@app.route("/products", methods=["GET", "POST"])
@perm_required("products_edit")
def products():
    """المنتجات والمخزون. المديرة: كل الفروع. الاستقبال: فرعه فقط، بلا سعر الشراء،
    وكل منتج جديد أو سعر تبدّل يظهر للمديرة لتراجعه."""
    db = get_db()
    u = current_user()
    admin = u["role"] == "admin"
    can_price = admin or has_perm("sale_prices")
    can_cost = admin or has_perm("cost_prices")
    branches = active_branches() if admin else [b for b in active_branches() if b["id"] == u["branch_id"]]
    if request.method == "POST":
        pid = request.form.get("id")
        old = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone() if pid else None
        name = request.form.get("name", "").strip()
        if not name:
            flash("اسم المنتج مطلوب", "err")
            return redirect(url_for("products"))
        price = fnum(request.form.get("price")) if can_price else (old["price"] if old else 0)
        cost = (fnum(request.form.get("cost_price")) if can_cost and request.form.get("cost_price", "") != ""
                else (old["cost_price"] if old else 0)) or 0
        usage = request.form.get("usage") if request.form.get("usage") in PRODUCT_USAGE else "sale"
        if usage == "use" and not can_price:
            price = old["price"] if old else 0
        vals = (name, request.form.get("barcode", "").strip(), request.form.get("category", "").strip(), price,
                request.form.get("expiry") or None, 1 if request.form.get("active", "1") == "1" else 0, cost)
        if old:
            note = None
            if old["price"] != price:
                audit("تغيير سعر منتج", f"{name}: {old['price']:g} ← {price:g}")
                note = f"تغيّر السعر: {old['price']:g} ← {price:g}"
            if (old["cost_price"] or 0) != cost:
                audit("تغيير سعر شراء", f"{name}: {(old['cost_price'] or 0):g} ← {cost:g}")
                note = ((note + " — ") if note else "") + f"تغيّر سعر الشراء: {(old['cost_price'] or 0):g} ← {cost:g}"
            db.execute("UPDATE products SET name=?,barcode=?,category=?,price=?,expiry=?,active=?,cost_price=? WHERE id=?",
                       vals + (pid,))
            if note and not admin:
                db.execute("UPDATE products SET needs_review=1, review_note=?, added_by=? WHERE id=?", (note, u["id"], pid))
            db.execute("UPDATE products SET usage=? WHERE id=?", (usage, pid))
            flash("تم تعديل المنتج", "ok")
        else:
            pid = db.execute("""INSERT INTO products(name,barcode,category,price,expiry,active,cost_price,needs_review,added_by,review_note)
                VALUES(?,?,?,?,?,?,?,?,?,?)""", vals + (0 if admin else 1, u["id"], None if admin else "منتج جديد")).lastrowid
            db.execute("UPDATE products SET usage=? WHERE id=?", (usage, pid))
            if not admin:
                audit("منتج جديد", f"{name} — سعر البيع {price:g}")
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
    br = scope_branch() if admin else u["branch_id"]
    show = [b for b in branches if not br or b["id"] == br]
    q = request.args.get("q", "").strip()
    usage = request.args.get("usage", "")
    sql = "SELECT * FROM products WHERE 1=1"
    args = []
    if q:
        sql += " AND (name LIKE ? OR category LIKE ? OR barcode=?)"
        args = [f"%{q}%", f"%{q}%", q]
    if usage == "sale":
        sql += " AND COALESCE(usage,'sale') IN ('sale','both')"
    elif usage == "use":
        sql += " AND usage IN ('use','both')"
    rows = db.execute(sql + " ORDER BY active DESC, COALESCE(category,'ي'), id", args).fetchall()
    counts = {k: db.execute(f"SELECT COUNT(*) FROM products WHERE active=1 AND {w}").fetchone()[0] for k, w in
              (("all", "1=1"), ("sale", "COALESCE(usage,'sale') IN ('sale','both')"), ("use", "usage IN ('use','both')"))}
    stock = {(r["product_id"], r["branch_id"]): r for r in db.execute("SELECT * FROM stock")}
    edit = db.execute("SELECT * FROM products WHERE id=?", (request.args.get("edit"),)).fetchone() \
        if request.args.get("edit") else None
    soon = (center_today() + timedelta(days=int(fnum(setting("expiry_days"), 30)))).isoformat()
    review = db.execute("""SELECT p.*, u.full_name AS by_name, b.name AS by_branch FROM products p
        LEFT JOIN users u ON u.id=p.added_by LEFT JOIN branches b ON b.id=u.branch_id
        WHERE p.needs_review=1 ORDER BY p.id DESC""").fetchall() if admin else []
    return render_template("products.html", rows=rows, branches=branches, show=show, stock=stock, edit=edit,
                           br=br, q=q, soon=soon, default_min=setting("default_min_qty"), review=review,
                           can_price=can_price, can_cost=can_cost, admin=admin, usage=usage, counts=counts)


@app.route("/catalog/restore", methods=["POST"])
@login_required("admin")
def catalog_restore():
    """زر «إعادة إدخال المنتجات والخدمات الأصلية» (المديرة فقط)."""
    if sync.NODE:
        abort(403)
    db = get_db()
    s_n, p_n, r_n = catalog.restore_catalog(db)
    db.commit()
    audit("إعادة إدخال القائمة الأصلية", f"خدمات مضافة {s_n}، منتجات مضافة {p_n}، أعيد تفعيل {r_n}")
    db.commit()
    if s_n or p_n or r_n:
        flash(f"تمت إعادة الإدخال: {s_n} خدمة و{p_n} منتج جديد، وأعيد تفعيل {r_n}. الموجود من قبل بقي بسعره.", "ok")
    else:
        flash("كل المنتجات والخدمات الأصلية موجودة من قبل، لم يُضف شيء.", "ok")
    return redirect(request.referrer or url_for("products"))


@app.route("/api/products/quick", methods=["POST"])
@login_required()
def product_quick():
    """منتج جديد غير مسجّل، من شاشة البيع أو الشراء. ما يضيفه العامل يظهر للمديرة لتراجعه."""
    u = current_user()
    if not (u["role"] == "admin" or has_perm("pos") or has_perm("purchases")):
        abort(403)
    db = get_db()
    f = request.get_json(force=True, silent=True) or request.form
    name = (f.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "اكتب اسم المنتج"}, 400
    barcode = (f.get("barcode") or "").strip()
    ex = db.execute("SELECT * FROM products WHERE active=1 AND (lower(trim(name))=lower(?) OR (?<>'' AND barcode=?))",
                    (name, barcode, barcode)).fetchone()
    if ex:
        p = ex
    else:
        price, cost = fnum(f.get("price")), fnum(f.get("cost"))
        pid = db.execute("""INSERT INTO products(name,barcode,category,price,active,cost_price,needs_review,added_by)
            VALUES(?,?,?,?,1,?,?,?)""", (name, barcode or None, (f.get("category") or "").strip() or None, price, cost,
                                         0 if u["role"] == "admin" else 1, u["id"])).lastrowid
        if u["role"] != "admin":
            db.execute("UPDATE products SET review_note='منتج جديد' WHERE id=?", (pid,))
        if (f.get("usage") or "") in PRODUCT_USAGE:
            db.execute("UPDATE products SET usage=? WHERE id=?", (f.get("usage"), pid))
        dm = setting("default_min_qty")
        for b in active_branches():
            if dm not in (None, ""):
                set_min(db, pid, b["id"], fnum(dm))
        audit("منتج جديد", f"{name} — سعر البيع {price:g}، سعر الشراء {cost:g}"
              + (" (أضافه عامل، بانتظار مراجعة المديرة)" if u["role"] != "admin" else ""))
        db.commit()
        p = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    br = work_branch()
    st = db.execute("SELECT qty FROM stock WHERE product_id=? AND branch_id=?", (p["id"], br)).fetchone()
    return {"ok": True, "existed": bool(ex), "product": dict(id=p["id"], name=p["name"], price=p["price"] or 0,
            cost_price=p["cost_price"] or 0, category=p["category"] or "", barcode=p["barcode"] or "",
            qty=(st["qty"] if st else 0), ic=icons.item_icon(p["name"], "product"))}


@app.route("/sessions/profit")
@login_required("admin")
def sessions_profit():
    """فائدة كل حصة: سعر الحصة، المواد المستعملة، والفائدة الصافية."""
    db = get_db()
    d1 = request.args.get("from") or center_today().isoformat()
    d2 = request.args.get("to") or d1
    br = scope_branch()
    room = request.args.get("room", "")
    q = """SELECT v.id FROM visits v WHERE v.status IN ('done','paid') AND substr(v.created_at,1,10) BETWEEN ? AND ?"""
    args = [d1, d2]
    if br:
        q += " AND v.branch_id=?"
        args.append(br)
    rows, tot = [], {}
    for (vid,) in db.execute(q + " ORDER BY v.id DESC LIMIT 1000", args).fetchall():
        v, items, _ = visit_data(vid)
        rk = visit_room(v)
        if room and rk != room:
            continue
        e = session_economics(db, v, items)
        label = (f"{v['plan_title']} — حصة {v['session_no']}/{v['plan_n']}" if v["plan_id"] else
                 "، ".join(i["description"] for i in items if i["kind"] == "service")[:80] or (v["request"] or ""))
        rows.append(dict(v=v, e=e, room=rk, label=label))
        t = tot.setdefault(rk, {"n": 0, "income": 0, "cost": 0, "profit": 0})
        t["n"] += 1
        for k in ("income", "cost", "profit"):
            t[k] += e[k]
    grand = {k: sum(t[k] for t in tot.values()) for k in ("n", "income", "cost", "profit")}
    return render_template("sessions_profit.html", rows=rows, tot=tot, grand=grand, d1=d1, d2=d2, br=br, room=room)


@app.route("/stock/use", methods=["GET", "POST"])
@perm_required("stock_use")
def stock_use():
    """استهلاك مواد العمل: ما تستعمله الغرف (كؤوس الحجامة، الجل، الكريمات...) يخرج من المخزون ويُحسب على الغرفة."""
    db = get_db()
    u = current_user()
    admin = u["role"] == "admin"
    br = (int(request.values.get("branch")) if admin and (request.values.get("branch") or "").isdigit()
          else (scope_branch() or u["branch_id"]) if admin else u["branch_id"]) or 1
    default_room = u["role"] if u["role"] in ("laser", "beauty") else ("director" if admin else "hijama")
    if request.method == "POST":
        room = request.form.get("room") if request.form.get("room") in USE_ROOMS else default_room
        n = 0
        for pid, q in zip(request.form.getlist("product_id"), request.form.getlist("qty")):
            q = fnum(q)
            if not pid.lstrip("-").isdigit() or q <= 0:
                continue
            p = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if not p:
                continue
            move_stock(db, p["id"], br, -q, f"استهلاك — {USE_ROOMS[room]}" +
                       (f": {request.form.get('note').strip()}" if request.form.get("note", "").strip() else ""),
                       u["id"], kind="use", dept=room)
            n += 1
        if n:
            audit("استهلاك مواد", f"{USE_ROOMS[room]} — {n} مادة", br)
            flash(f"تم تسجيل استهلاك {n} مادة على {USE_ROOMS[room]}", "ok")
        db.commit()
        return redirect(url_for("stock_use", branch=br if admin else None))
    mats = db.execute("""SELECT p.id, p.name, p.category, p.usage, COALESCE(s.qty,0) AS qty FROM products p
        LEFT JOIN stock s ON s.product_id=p.id AND s.branch_id=? WHERE p.active=1 AND p.usage IN ('use','both')
        ORDER BY p.usage='both', p.category, p.name""", (br,)).fetchall()
    d1 = request.args.get("from") or center_today().replace(day=1).isoformat()
    d2 = request.args.get("to") or center_today().isoformat()
    hist = db.execute("""SELECT m.*, p.name, u.full_name AS by_name, -m.qty*COALESCE(p.cost_price,0) AS cost
        FROM stock_moves m JOIN products p ON p.id=m.product_id LEFT JOIN users u ON u.id=m.user_id
        WHERE m.kind='use' AND COALESCE(m.cancelled,0)=0 AND m.branch_id=? AND substr(m.created_at,1,10) BETWEEN ? AND ?
        ORDER BY m.id DESC LIMIT 200""", (br, d1, d2)).fetchall()
    summary = db.execute("""SELECT m.dept, p.name, SUM(-m.qty) AS qty, SUM(-m.qty*COALESCE(p.cost_price,0)) AS cost
        FROM stock_moves m JOIN products p ON p.id=m.product_id
        WHERE m.kind='use' AND COALESCE(m.cancelled,0)=0 AND m.branch_id=? AND substr(m.created_at,1,10) BETWEEN ? AND ?
        GROUP BY m.dept, p.name ORDER BY m.dept, cost DESC""", (br, d1, d2)).fetchall()
    rooms = {k: v for k, v in USE_ROOMS.items()
             if k in ("hijama", "reception") or (k == "director" and str(br) == str(setting("director_branch")))
             or k in branch_depts(br)}
    return render_template("stock_use.html", mats=mats, hist=hist, summary=summary, br=br, rooms=rooms,
                           default_room=default_room, d1=d1, d2=d2, admin=admin,
                           branches=active_branches() if admin else [])


@app.route("/products/<int(signed=True):pid>/reviewed", methods=["POST"])
@login_required("admin")
def product_reviewed(pid):
    db = get_db()
    db.execute("UPDATE products SET needs_review=0, review_note=NULL WHERE id=?", (pid,))
    db.commit()
    return redirect(request.referrer or url_for("products"))


@app.route("/products/<int(signed=True):pid>/stock", methods=["POST"])
@perm_required("products_edit")
def product_stock(pid):
    db = get_db()
    bid = int(request.form["branch_id"])
    if current_user()["role"] != "admin" and bid != current_user()["branch_id"]:
        abort(403)  # الاستقبال يعدّل مخزون فرعه فقط
    q = fnum(request.form.get("qty"))
    cst = request.form.get("cost", "").strip()
    if cst and q > 0 and (current_user()["role"] == "admin" or has_perm("cost_prices")):
        p = db.execute("SELECT name, cost_price FROM products WHERE id=?", (pid,)).fetchone()
        new = fnum(cst)
        if p and new >= 0 and new != (p["cost_price"] or 0):
            db.execute("UPDATE products SET cost_price=? WHERE id=?", (new, pid))
            audit("تغيير سعر شراء", f"{p['name']}: {(p['cost_price'] or 0):g} ← {new:g} (عند إدخال سلعة)", bid)
            if current_user()["role"] != "admin":
                db.execute("UPDATE products SET needs_review=1, review_note=?, added_by=? WHERE id=?",
                           (f"تغيّر سعر الشراء: {(p['cost_price'] or 0):g} ← {new:g}", current_user()["id"], pid))
            flash("تم تحديث سعر الشراء", "ok")
    if q:
        audit("تعديل مخزون", f"منتج {pid}: {q:+g} — {branch_name(bid)}", bid)
        move_stock(db, pid, bid, q,
                   request.form.get("reason") or ("إدخال سلعة" if q > 0 else "إخراج / تلف"), current_user()["id"],
                   kind="adjust")
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
    for p in db.execute("SELECT * FROM products WHERE active=1 ORDER BY COALESCE(category,'ي'), id"):
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
                           now=center_now().strftime("%Y-%m-%d %H:%M"))



# ---------------------------------------------------------------- العمال، الحضور، المنح
def month_bounds(m):
    try:
        d1 = datetime.strptime(m + "-01", "%Y-%m-%d").date()
    except (TypeError, ValueError):
        d1 = center_today().replace(day=1)
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
    day = day or center_today()
    p = emp_pay_day(e)
    if day.day >= p:
        return day.strftime("%Y-%m")
    y, m = (day.year - 1, 12) if day.month == 1 else (day.year, day.month - 1)
    return f"{y:04d}-{m:02d}"


def work_dates(e, d1, d2):
    """أيام العمل للعامل في الفترة: من بداية الشهر (أو تاريخ توظيفه) إلى آخره (أو اليوم)، دون أيام الراحة."""
    off = {int(x) for x in (setting("weekly_off") or "").split(",") if x.strip().isdigit()}
    start = datetime.strptime(d1, "%Y-%m-%d").date()
    end = min(datetime.strptime(d2, "%Y-%m-%d").date(), center_today())
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
                elif r["day"] <= center_today().isoformat():  # عمل في يوم الراحة: يُضاف
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
    t = center_today().isoformat()
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
    d = request.values.get("date") or center_today().isoformat()
    if u["role"] != "admin" and d != center_today().isoformat():
        # الاستقبال يسجّل حضور اليوم وأمس فقط
        if d < (center_today() - timedelta(days=1)).isoformat() or d > center_today().isoformat():
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
            day = request.form.get("day") or center_today().isoformat()
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
    return render_template("payslip.html", s=s_, att=att, mm=mm, now=center_now().strftime("%Y-%m-%d %H:%M"))



@app.route("/staff/<int(signed=True):eid>/leave", methods=["GET", "POST"])
@login_required("admin")
def employee_leave(eid):
    """مغادرة العمل نهائيًا: تصفية الحساب (أجرة الأيام الأخيرة − التسبيقات الباقية) ثم إيقاف العامل،
    فلا تُحسب له أجرة بعد ذلك ولا تظهر في المصاريف الشهرية."""
    db = get_db()
    e = db.execute("""SELECT e.*, b.name AS branch, po.name AS post FROM employees e JOIN branches b ON b.id=e.branch_id
        LEFT JOIN posts po ON po.id=e.post_id WHERE e.id=?""", (eid,)).fetchone() or abort(404)
    last = request.values.get("last_day") or center_today().isoformat()
    try:
        last_d = datetime.strptime(last, "%Y-%m-%d").date()
    except ValueError:
        last_d = center_today()
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
                VALUES(?,?,?,?,?,?,?,?,?,?)""", (e["branch_id"], center_today().isoformat(), "أجور العمال",
                                                 f"أجرة {e['name']} — {prev['d1']} إلى {prev['d2']}", prev["net"], "cash",
                                                 eid, prev_mm, current_user()["id"], now_str()))
            amount -= prev["net"]
        db.execute("""INSERT INTO expenses(branch_id,day,category,description,amount,method,employee_id,month,created_by,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (e["branch_id"], center_today().isoformat(), "أجور العمال",
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
                           done=bool(request.args.get("done")), now=center_now().strftime("%Y-%m-%d %H:%M"))


def due_salaries(branch_id=None):
    """أجور مستحقة: فترات انتهت (أو تنتهي خلال 7 أيام) ولم تُسجَّل كمدفوعة."""
    db = get_db()
    q = "SELECT * FROM employees WHERE active=1"
    args = []
    if branch_id:
        q += " AND branch_id=?"
        args.append(branch_id)
    out = []
    today = center_today()
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
    return render_template("payslips_all.html", rows=rows, mm=mm, now=center_now().strftime("%Y-%m-%d %H:%M"))


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
                           now=center_now().strftime("%Y-%m-%d %H:%M"))




# ---------------------------------------------------------------- ملف الزيارة (الاستقبال ← المديرة/القسم ← الاستقبال)
def queue_target():
    """قائمة الانتظار التي يعالجها هذا المستخدم: المديرة = المدير في فرعها، أو قسم الليزر/التجميل."""
    u = current_user()
    if u["role"] == "admin":
        return "all", scope_branch()  # المديرة تشوف كل الغرف في كل الفروع
    if u["role"] in ("laser", "beauty"):
        return u["role"], u["branch_id"]
    if u["role"] == "reception":
        return "reception", u["branch_id"]
    return None, None


def queue_count():
    tgt, br = queue_target()
    if not tgt:
        return 0
    q = "SELECT COUNT(*) n FROM visits WHERE (target=? OR ?='all') AND status IN ('waiting','treating') AND substr(created_at,1,10)>=?"
    args = [tgt, tgt, center_today().isoformat()]
    if br:
        q += " AND branch_id=?"
        args.append(br)
    return get_db().execute(q, args).fetchone()["n"]


def visit_room(v):
    return {"director": "director", "laser": "laser", "beauty": "beauty"}.get(v["target"], "hijama")


def session_economics(db, v, items):
    """سعر الحصة كلها، المواد المستعملة (بسعر الشراء)، وفائدة الحصة الصافية."""
    mats = db.execute("""SELECT m.id, m.qty, p.name, COALESCE(p.cost_price,0) AS unit, -m.qty*COALESCE(p.cost_price,0) AS cost,
        u.full_name AS by_name FROM stock_moves m JOIN products p ON p.id=m.product_id LEFT JOIN users u ON u.id=m.user_id
        WHERE m.visit_id=? AND m.kind='use' ORDER BY m.id""", (v["id"],)).fetchall()
    income = sum(i["qty"] * i["unit_price"] for i in items)
    prepaid = 0
    if v["appointment_id"]:  # حصة مدفوعة مسبقًا (باقة): نحسب ثمنها في دخل الحصة
        ap = db.execute("SELECT price, paid FROM appointments WHERE id=?", (v["appointment_id"],)).fetchone()
        if ap and not any((i["appt_id"] == v["appointment_id"] and i["unit_price"] > 0) for i in items):
            prepaid = ap["price"] or 0
    # المنتجات المبيعة في الحصة: نطرح سعر شرائها حتى تبقى الفائدة صافية
    sold_cost = 0
    for i in items:
        if i["product_id"]:
            c = db.execute("SELECT COALESCE(cost_price,0) FROM products WHERE id=?", (i["product_id"],)).fetchone()
            sold_cost += (c[0] if c else 0) * i["qty"]
    cost = sum(m["cost"] for m in mats) + sold_cost
    total_income = round(income + prepaid, 2)
    return dict(mats=mats, income=total_income, prepaid=prepaid, mat_cost=round(sum(m["cost"] for m in mats), 2),
                sold_cost=round(sold_cost, 2), cost=round(cost, 2), profit=round(total_income - cost, 2))


def visit_data(vid):
    db = get_db()
    v = db.execute("""SELECT v.*, c.name AS client, c.phone, c.birth_date, c.gender, c.address, c.chronic,
        c.allergies, c.medications, c.notes AS cnotes, b.name AS branch, u.full_name AS by_name,
        ap.plan_id, ap.session_no, ap.paid AS session_paid, pl.title AS plan_title,
        (SELECT COUNT(*) FROM appointments x WHERE x.plan_id=ap.plan_id) AS plan_n,
        (SELECT COUNT(*) FROM appointments x WHERE x.plan_id=ap.plan_id AND x.status='done') AS plan_done
        FROM visits v JOIN clients c ON c.id=v.client_id JOIN branches b ON b.id=v.branch_id
        LEFT JOIN users u ON u.id=v.created_by LEFT JOIN appointments ap ON ap.id=v.appointment_id
        LEFT JOIN plans pl ON pl.id=ap.plan_id WHERE v.id=?""", (vid,)).fetchone() or abort(404)
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
        target = f.get("target")
        if target not in SEND_TARGETS:
            flash("اختر القسم الذي يذهب إليه الزبون (التجميل، العلاج، الليزر)", "err")
            return redirect(url_for("visit_new", client_id=f.get("client_id")))
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
    targets = {k: VISIT_TARGETS[k] for k in SEND_TARGETS if k == "reception" or k in branch_depts(br)}
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
    q = """SELECT v.*, c.name AS client, c.phone, c.birth_date, c.gender, c.chronic, c.allergies, b.name AS branch,
        (SELECT COUNT(*) FROM visit_items i WHERE i.visit_id=v.id) AS n_items
        FROM visits v JOIN clients c ON c.id=v.client_id JOIN branches b ON b.id=v.branch_id
        WHERE v.status IN ('waiting','treating') AND (v.target=? OR ?='all')"""
    args = [tgt, tgt]
    if br:
        q += " AND v.branch_id=?"
        args.append(br)
    rows = db.execute(q + " ORDER BY v.id", args).fetchall()
    today = center_today().isoformat()
    old = [r for r in rows if r["created_at"][:10] < today]
    if not request.args.get("old"):
        rows = [r for r in rows if r["created_at"][:10] >= today]  # كل نهار وحدو
    return render_template("visit_queue_rows.html", rows=rows, all_rooms=tgt == "all", n_old=len(old),
                           show_old=bool(request.args.get("old")))


@app.route("/visits")
@perm_required("reception_visits")
def visits_list():
    db = get_db()
    br = scope_branch()
    d = request.args.get("date") or center_today().isoformat()
    q = """SELECT v.*, c.name AS client, b.name AS branch,
        (SELECT COALESCE(SUM(qty*unit_price),0) FROM visit_items i WHERE i.visit_id=v.id) AS total
        FROM visits v JOIN clients c ON c.id=v.client_id JOIN branches b ON b.id=v.branch_id
        WHERE substr(v.created_at,1,10)=?"""
    args = [d]
    if br:
        q += " AND v.branch_id=?"
        args.append(br)
    if current_user()["role"] in ("laser", "beauty"):
        q += " AND v.target=?"
        args.append(current_user()["role"])
    rows = db.execute(q + " ORDER BY v.id DESC", args).fetchall()
    return render_template("visits.html", rows=rows, d=d, br=br)


@app.route("/visits/<int(signed=True):vid>", methods=["GET", "POST"])
@login_required()
def visit_view(vid):
    db = get_db()
    u = current_user()
    v, items, total = visit_data(vid)
    if u["role"] in ("laser", "beauty") and v["target"] != u["role"]:
        abort(403)  # غرفة الليزر/التجميل لا ترى زبائن المديرة ولا الأقسام الأخرى
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
        elif act == "use_mat" and (can_treat or u["role"] == "admin") and v["status"] != "cancelled":
            n = 0
            for pid_, q in zip(request.form.getlist("mat_id"), request.form.getlist("mat_qty")):
                q = fnum(q)
                if pid_.lstrip("-").isdigit() and q > 0:
                    pr = db.execute("SELECT name FROM products WHERE id=?", (pid_,)).fetchone()
                    if pr:
                        move_stock(db, int(pid_), v["branch_id"], -q, f"استهلاك في حصة {rid_filter(vid)} — {v['client']}",
                                   u["id"], kind="use", dept=visit_room(v), visit_id=vid)
                        n += 1
            flash(f"تم تسجيل {n} مادة مستعملة" if n else "اختر المادة والكمية", "ok" if n else "err")
        elif act == "unuse_mat" and (can_treat or u["role"] == "admin"):
            m = db.execute("SELECT * FROM stock_moves WHERE id=? AND visit_id=? AND kind='use'",
                           (request.form.get("move_id"), vid)).fetchone()
            if m:
                db.execute("UPDATE stock SET qty=qty-? WHERE product_id=? AND branch_id=?", (m["qty"], m["product_id"], m["branch_id"]))
                db.execute("DELETE FROM stock_moves WHERE id=?", (m["id"],))
                flash("تم حذف المادة ورجعت للمخزون", "ok")
        elif act == "start" and can_treat and v["status"] == "waiting":
            db.execute("UPDATE visits SET status='treating', started_at=? WHERE id=?", (now_str(), vid))
        elif act == "finish" and can_treat and v["status"] in ("waiting", "treating"):
            _, items, total = visit_data(vid)
            db.execute("UPDATE visits SET status='done', done_at=?, done_by=? WHERE id=?", (now_str(), u["id"], vid))
            if v["appointment_id"]:  # حصة من خطة: تكمل، والحصة الجاية تاخذ تاريخها
                ap = db.execute("SELECT * FROM appointments WHERE id=?", (v["appointment_id"],)).fetchone()
                if ap:
                    db.execute("UPDATE appointments SET status='done' WHERE id=?", (ap["id"],))
                    nxt = schedule_next_session(db, ap)
                    if nxt:
                        flash(f"تحدّد موعد الحصة القادمة: {nxt}", "ok")
                    if ap["plan_id"] and not db.execute("SELECT 1 FROM appointments WHERE plan_id=? AND status='scheduled'",
                                                        (ap["plan_id"],)).fetchone():
                        db.execute("UPDATE plans SET status='done' WHERE id=? AND status='active'", (ap["plan_id"],))
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
        elif act == "move" and v["status"] == "waiting" and u["role"] in ("admin", "reception") \
                and request.form.get("target") in VISIT_TARGETS and request.form.get("target") != v["target"]:
            t_ = request.form["target"]
            db.execute("UPDATE visits SET target=? WHERE id=?", (t_, vid))
            audit("تصحيح قسم الزيارة", f"{v['client']}: {VISIT_TARGETS.get(v['target'])} ← {VISIT_TARGETS[t_]}", v["branch_id"])
            flash(f"نُقل الزبون إلى {VISIT_TARGETS[t_]}", "ok")
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
        ON s.product_id=p.id AND s.branch_id=? WHERE p.active=1 AND COALESCE(p.usage,'sale')<>'use'
        ORDER BY p.name""", (v["branch_id"],)).fetchall()
    vnotes = db.execute("""SELECT n.*, u.full_name AS by_name FROM client_notes n LEFT JOIN users u ON u.id=n.created_by
        WHERE n.client_id=? ORDER BY n.id DESC LIMIT 8""", (v["client_id"],)).fetchall() if has_perm("medical") else []
    mats_list = work_materials(db, v["branch_id"])
    return render_template("visit_view.html", v=v, items=items, total=total, services=services_for(v["branch_id"]),
                           vnotes=vnotes, eco=session_economics(db, v, items), mats_list=mats_list,
                           mats_default=visit_default_mats(db, v, items),
                           skin=skin_card(db, v["client_id"]) if has_perm("medical") else None,
                           prods=prods, can_treat=can_treat, can_edit=can_edit)


# ---------------------------------------------------------------- الدورات التكوينية والشهادات
def course_or_404(cid):
    c = get_db().execute("""SELECT co.*, b.name AS branch FROM courses co JOIN branches b ON b.id=co.branch_id
        WHERE co.id=?""", (cid,)).fetchone() or abort(404)
    u = current_user()
    if u["role"] != "admin" and c["branch_id"] != u["branch_id"]:
        abort(403)
    return c


def trainee_alloc(db, client_id):
    """ملف المتكوّن: كل دفعاته (تسبيقات ودفعات) توزَّع على دوراته بالترتيب، الأقدم أولًا."""
    ens = db.execute("""SELECT t.id, t.price, t.status FROM course_trainees t WHERE t.client_id=?
        ORDER BY t.enrolled_at, t.id""", (client_id,)).fetchall()
    ids = [e["id"] for e in ens]
    if not ids:
        return {}, 0, 0
    q = ",".join("?" * len(ids))
    paid_total = db.execute(f"SELECT COALESCE(SUM(amount),0) FROM payments WHERE cancelled=0 AND enroll_id IN ({q})",
                            ids).fetchone()[0]
    left, out, due = paid_total, {}, 0
    active = [e for e in ens if e["status"] != "withdrawn"]
    for e in active:
        take = min(left, e["price"] or 0)
        out[e["id"]] = take
        left -= take
        due += e["price"] or 0
    if left > 0 and active:  # زيادة (مثلاً بعد تخفيض السعر): تظهر على آخر دورة
        out[active[-1]["id"]] += left
    for e in ens:
        out.setdefault(e["id"], 0)
    return out, due, paid_total


def trainees_of(cid):
    db = get_db()
    rows = [dict(r) for r in db.execute("""SELECT t.*, c.name, c.phone, c.birth_date, c.gender
        FROM course_trainees t JOIN clients c ON c.id=t.client_id WHERE t.course_id=? ORDER BY c.name""", (cid,))]
    for r in rows:
        r["paid"] = trainee_alloc(db, r["client_id"])[0].get(r["id"], 0)
    return rows


def make_course_days(db, tid, n):
    for k in range(1, (n or 1) + 1):
        db.execute("INSERT INTO course_days(trainee_id,day_no,created_at) VALUES(?,?,?)", (tid, k, now_str()))


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
        cid = db.execute("""INSERT INTO courses(branch_id,name,price,start_date,end_date,hours,trainer,notes,created_by,created_at,days)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (u["branch_id"] or int(f.get("branch_id") or work_branch()), name,
                                             fnum(f.get("price")), f.get("start_date") or None, f.get("end_date") or None,
                                             fnum(f.get("hours")) or None, f.get("trainer", "").strip(),
                                             f.get("notes", "").strip(), u["id"], now_str(),
                                             int(fnum(f.get("days")) or 1))).lastrowid
        db.execute("UPDATE courses SET name_en=? WHERE id=?", ((f.get("name_en") or "").strip() or None, cid))
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
    files = []
    fq = """SELECT DISTINCT t.client_id, c.name, c.phone FROM course_trainees t JOIN clients c ON c.id=t.client_id
        JOIN courses co ON co.id=t.course_id WHERE 1=1"""
    if br:
        fq += " AND co.branch_id=?"
    for r in db.execute(fq + " ORDER BY c.name", [br] if br else []):
        _, due, paid = trainee_alloc(db, r["client_id"])
        cs = db.execute("""SELECT co.name, t.status FROM course_trainees t JOIN courses co ON co.id=t.course_id
            WHERE t.client_id=? AND t.status<>'withdrawn' ORDER BY t.enrolled_at""", (r["client_id"],)).fetchall()
        files.append(dict(cid=r["client_id"], name=r["name"], phone=r["phone"], courses=cs, due=due, paid=paid))
    return render_template("courses.html", rows=rows, br=br, files=files)


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
            db.execute("UPDATE courses SET days=? WHERE id=?", (int(fnum(f.get("days")) or 1), cid))
            db.execute("UPDATE courses SET name_en=? WHERE id=?", ((f.get("name_en") or "").strip() or None, cid))
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
                tid = db.execute("""INSERT INTO course_trainees(course_id,client_id,price,enrolled_at,created_by)
                    VALUES(?,?,?,?,?)""", (cid, int(cl), price, now_str(), u["id"])).lastrowid
                make_course_days(db, tid, c["days"])
                flash("تم التسجيل في الدورة", "ok")
        elif act == "pay":
            t = db.execute("SELECT t.*, (SELECT COALESCE(SUM(amount),0) FROM payments p WHERE p.enroll_id=t.id AND p.cancelled=0) AS paid "
                           "FROM course_trainees t WHERE t.id=? AND t.course_id=?", (f.get("tid"), cid)).fetchone()
            amount = fnum(f.get("amount"))
            if not t or amount <= 0:
                flash("أدخل المبلغ المدفوع", "err")
            elif amount > round(trainee_alloc(db, t["client_id"])[1] - trainee_alloc(db, t["client_id"])[2], 2) + 0.001:
                flash("المبلغ أكبر من الباقي على المتكوّن", "err")
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


@app.route("/trainees/<int(signed=True):client_id>", methods=["GET", "POST"])
@perm_required("courses")
def trainee_file(client_id):
    """ملف المتكوّن: كل دوراته (حجامة ثم ليزر...) وأيامها ودفعاته في مكان واحد."""
    db = get_db()
    u = current_user()
    cl = db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone() or abort(404)
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        tid = f.get("tid")
        own = db.execute("SELECT t.*, co.days, co.name AS cname, co.branch_id FROM course_trainees t JOIN courses co ON co.id=t.course_id "
                         "WHERE t.id=? AND t.client_id=?", (tid, client_id)).fetchone() if tid else None
        if act == "enroll":
            co = db.execute("SELECT * FROM courses WHERE id=?", (f.get("course_id"),)).fetchone()
            if not co:
                flash("اختاري الدورة", "err")
                return redirect(url_for("trainee_file", client_id=client_id))
            if db.execute("SELECT 1 FROM course_trainees WHERE course_id=? AND client_id=? AND status<>'withdrawn'",
                          (co["id"], client_id)).fetchone():
                flash("مسجّل في هذه الدورة مسبقًا", "err")
                return redirect(url_for("trainee_file", client_id=client_id))
            price = co["price"] if price_locked(u) or not f.get("price") else fnum(f.get("price"))
            tid = db.execute("""INSERT INTO course_trainees(course_id,client_id,price,enrolled_at,created_by)
                VALUES(?,?,?,?,?)""", (co["id"], client_id, price, now_str(), u["id"])).lastrowid
            make_course_days(db, tid, co["days"])
            adv = fnum(f.get("advance"))
            audit("تسجيل في دورة", f"{cl['name']}: {co['name']} ({price:g})")
            if adv > 0:
                if adv > price + 0.001:
                    db.commit()
                    flash("سُجّل في الدورة، لكن التسبيق أكبر من سعرها فلم يُسجَّل", "err")
                    return redirect(url_for("trainee_file", client_id=client_id))
                pid = make_payment(db, co["branch_id"], client_id, adv, f.get("method", "cash"), "course",
                                   f"تسبيق دورة: {co['name']}", u["id"])
                db.execute("UPDATE payments SET enroll_id=? WHERE id=?", (tid, pid))
                db.commit()
                flash(f"تم التسجيل في «{co['name']}» وتسجيل التسبيق", "ok")
                return redirect(url_for("receipt", pid=pid))
            db.commit()
            flash(f"تم التسجيل في «{co['name']}»", "ok")
        elif act == "pay":
            alloc, due, paid = trainee_alloc(db, client_id)
            amount = fnum(f.get("amount"))
            rest = round(due - paid, 2)
            if amount <= 0:
                flash("اكتبي المبلغ", "err")
            elif amount > rest + 0.001:
                flash(f"المبلغ أكبر من الباقي ({rest:g})", "err")
            else:
                ens = db.execute("""SELECT t.id, t.price, co.name, co.branch_id FROM course_trainees t JOIN courses co ON co.id=t.course_id
                    WHERE t.client_id=? AND t.status<>'withdrawn' ORDER BY t.enrolled_at, t.id""", (client_id,)).fetchall()
                target = next((e for e in ens if alloc.get(e["id"], 0) < (e["price"] or 0) - 0.001), ens[-1])
                label = (f.get("note") or "").strip() or "دفعة"
                pid = make_payment(db, target["branch_id"], client_id, amount, f.get("method", "cash"), "course",
                                   f"دورة: {'، '.join(e['name'] for e in ens)} — {label}", u["id"])
                db.execute("UPDATE payments SET enroll_id=? WHERE id=?", (target["id"], pid))
                db.commit()
                flash("تم تسجيل الدفعة", "ok")
                return redirect(url_for("receipt", pid=pid))
        elif act == "day" and own:
            st = f.get("status") if f.get("status") in ("present", "absent", "") else ""
            db.execute("UPDATE course_days SET day_date=?, status=?, note=? WHERE id=? AND trainee_id=?",
                       (f.get("day_date") or None, st or None, (f.get("note") or "").strip() or None, f.get("did"), own["id"]))
            days = db.execute("SELECT status FROM course_days WHERE trainee_id=?", (own["id"],)).fetchall()
            if days and all(d["status"] == "present" for d in days) and own["status"] == "enrolled":
                db.execute("UPDATE course_trainees SET status='completed', completed_at=? WHERE id=?", (now_str(), own["id"]))
                flash(f"حضر كل أيام «{own['cname']}»: أكمل الدورة", "ok")
        elif act == "add_day" and own:
            n = db.execute("SELECT COALESCE(MAX(day_no),0) FROM course_days WHERE trainee_id=?", (own["id"],)).fetchone()[0]
            db.execute("INSERT INTO course_days(trainee_id,day_no,created_at) VALUES(?,?,?)", (own["id"], n + 1, now_str()))
        elif act == "del_day" and own:
            db.execute("DELETE FROM course_days WHERE id=? AND trainee_id=? AND status IS NULL", (f.get("did"), own["id"]))
        elif act == "status" and own and f.get("status") in TRAINEE_STATUS:
            st = f.get("status")
            db.execute("UPDATE course_trainees SET status=?, completed_at=? WHERE id=?",
                       (st, now_str() if st == "completed" else None, own["id"]))
        elif act == "latin":
            db.execute("UPDATE clients SET name_latin=? WHERE id=?", ((f.get("name_latin") or "").strip() or None, client_id))
            flash("حُفظ الاسم اللاتيني", "ok")
        elif act == "price" and own and not price_locked(u):
            db.execute("UPDATE course_trainees SET price=? WHERE id=?", (fnum(f.get("price")), own["id"]))
            audit("تعديل سعر دورة لمتكوّن", f"{cl['name']}: {own['cname']} → {fnum(f.get('price')):g}")
        db.commit()
        return redirect(url_for("trainee_file", client_id=client_id))
    alloc, due, paid = trainee_alloc(db, client_id)
    ens = []
    for t in db.execute("""SELECT t.*, co.name AS cname, co.days, co.hours, co.trainer, b.name AS branch, co.branch_id
            FROM course_trainees t JOIN courses co ON co.id=t.course_id JOIN branches b ON b.id=co.branch_id
            WHERE t.client_id=? ORDER BY t.enrolled_at, t.id""", (client_id,)):
        t = dict(t)
        t["paid"] = alloc.get(t["id"], 0)
        t["daylist"] = db.execute("SELECT * FROM course_days WHERE trainee_id=? ORDER BY day_no", (t["id"],)).fetchall()
        if not t["daylist"] and t["status"] == "enrolled":  # تسجيل قديم قبل نظام الأيام
            make_course_days(db, t["id"], t["days"])
            db.commit()
            t["daylist"] = db.execute("SELECT * FROM course_days WHERE trainee_id=? ORDER BY day_no", (t["id"],)).fetchall()
        ens.append(t)
    pays = db.execute(f"""SELECT p.*, us.full_name AS by_name FROM payments p LEFT JOIN users us ON us.id=p.received_by
        WHERE p.cancelled=0 AND p.enroll_id IN (SELECT id FROM course_trainees WHERE client_id=?) ORDER BY p.id""",
                      (client_id,)).fetchall()
    open_courses = db.execute("SELECT co.*, b.name AS branch FROM courses co JOIN branches b ON b.id=co.branch_id "
                              "WHERE co.status='open' ORDER BY co.name").fetchall()
    total_days = sum(len(t["daylist"]) for t in ens if t["status"] != "withdrawn")
    return render_template("trainee_file.html", cl=cl, ens=ens, pays=pays, due=due, paid=paid,
                           open_courses=open_courses, total_days=total_days,
                           done=[t for t in ens if t["status"] == "completed"])


@app.route("/trainees/open")
@perm_required("courses")
def trainee_open():
    s = request.args.get("q", "").strip()
    db = get_db()
    r = db.execute("""SELECT id FROM clients WHERE name LIKE ? OR phone LIKE ?
        ORDER BY (id IN (SELECT client_id FROM course_trainees)) DESC, name LIMIT 1""", (f"%{s}%", f"%{s}%")).fetchone()
    if not r:
        flash("لم يُعثر على هذا الشخص. سجّليه أولًا كزبون ثم افتحي ملفه.", "err")
        return redirect(url_for("courses"))
    return redirect(url_for("trainee_file", client_id=r["id"]))


def joined(names):
    names = [n for n in names if n]
    return names[0] if len(names) == 1 else "، ".join(names[:-1]) + " و" + names[-1] if names else ""


MONTHS_EN = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER",
             "NOVEMBER", "DECEMBER"]
BRANCH_EN = {1: "SKIKDA", 2: "EL HARROUCH"}


def dates_en(dates):
    """['2026-10-22','2026-10-23'] ← «22,23 OCTOBER 2026»"""
    ds = sorted({d[:10] for d in dates if d})
    if not ds:
        return ""
    groups = []
    for d in ds:
        y, m, dd = d.split("-")
        if groups and groups[-1][0] == (y, m):
            groups[-1][1].append(str(int(dd)))
        else:
            groups.append(((y, m), [str(int(dd))]))
    parts = []
    for i, ((y, m), days) in enumerate(groups):
        last_y = i == len(groups) - 1 or groups[i + 1][0][0] != y
        parts.append(",".join(days) + " " + MONTHS_EN[int(m) - 1] + (f" {y}" if last_y else ""))
    return " - ".join(parts)


def cert_en_data(db, rows, client):
    """بيانات الشهادة (النموذج الأخضر): من الملف، ويمكن تعديلها وتُحفظ مع الشهادة."""
    last = rows[-1]
    saved = {}
    try:
        saved = json.loads(last["cert_en"] or "{}")
    except (ValueError, TypeError):
        saved = {}
    course_names = []
    dates = []
    for r in rows:
        co = db.execute("SELECT name, name_en FROM courses WHERE id=?", (r["course_id"],)).fetchone()
        nm = (co["name_en"] or co["name"] or "").strip() if co else ""
        if nm and nm.upper() not in [x.upper() for x in course_names]:
            course_names.append(nm)
        ds = [d["day_date"] for d in db.execute("SELECT day_date FROM course_days WHERE trainee_id=? AND day_date IS NOT NULL",
                                              (r["id"],))]
        dates += ds or [x for x in (r["start_date"], r["end_date"]) if x] or [(r["completed_at"] or r["enrolled_at"] or "")[:10]]
    br = db.execute("SELECT id, name_en FROM branches WHERE id=?", (last["branch_id"],)).fetchone()
    place = (br["name_en"] if br and br["name_en"] else BRANCH_EN.get(last["branch_id"], "")) if br else ""
    d = dict(name=client["name_latin"] or client["name"],
             course=" & ".join(course_names).upper(),
             dates=dates_en(dates), place=place.upper(),
             center=setting("cert_en_center") or DEFAULT_SETTINGS["cert_en_center"],
             signer_title=setting("cert_en_signer_title") or DEFAULT_SETTINGS["cert_en_signer_title"],
             signer=setting("cert_en_signer") or DEFAULT_SETTINGS["cert_en_signer"])
    d.update({k: v for k, v in saved.items() if v})
    return d


def cert_en_save(db, rows, client_id, form):
    last = rows[-1]
    keys = ("course", "dates", "place", "center", "signer_title", "signer")
    data = {k: form.get(k, "").strip() for k in keys}
    nl = form.get("name", "").strip()
    if nl:
        db.execute("UPDATE clients SET name_latin=? WHERE id=?", (nl, client_id))
    db.execute("UPDATE course_trainees SET cert_en=? WHERE id=?", (json.dumps(data, ensure_ascii=False), last["id"]))
    for k, sk in (("signer_title", "cert_en_signer_title"), ("signer", "cert_en_signer"), ("center", "cert_en_center")):
        if form.get("as_default") and data[k]:
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (sk, data[k]))


@app.route("/trainees/<int(signed=True):client_id>/certificate", methods=["GET", "POST"])
@perm_required("courses")
def trainee_certificate(client_id):
    """شهادة واحدة لكل الدورات التي أكملها المتكوّن (مثلاً الحجامة والليزر)."""
    db = get_db()
    rows = db.execute("""SELECT t.*, co.name AS cname, co.hours, co.trainer, co.start_date, co.end_date, co.branch_id,
        b.name AS branch, c.name, c.birth_date, c.gender FROM course_trainees t JOIN courses co ON co.id=t.course_id
        JOIN branches b ON b.id=co.branch_id JOIN clients c ON c.id=t.client_id
        WHERE t.client_id=? AND t.status='completed' ORDER BY t.enrolled_at, t.id""", (client_id,)).fetchall()
    if not rows:
        flash("لا توجد دورة مكتملة بعد لهذا المتكوّن", "err")
        return redirect(url_for("trainee_file", client_id=client_id))
    last = rows[-1]
    model = request.values.get("model", "en")
    if request.method == "POST" and request.form.get("action") == "save_en":
        cert_en_save(db, rows, client_id, request.form)
        db.commit()
        flash("حُفظت بيانات الشهادة", "ok")
        return redirect(url_for("trainee_certificate", client_id=client_id))
    if request.method == "POST" and request.form.get("action") == "reset_en":
        db.execute("UPDATE course_trainees SET cert_en=NULL WHERE id=?", (last["id"],))
        db.commit()
        return redirect(url_for("trainee_certificate", client_id=client_id))
    if request.method == "GET" and model == "en":
        client = db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        _, due_, paid_ = trainee_alloc(db, client_id)
        return render_template("certificate_en.html", d=cert_en_data(db, rows, client), client=client,
                               due=due_, paid=paid_, stamp=setting("stamp_img"), signature=setting("signature_img"),
                               cert_no=f"{(last['completed_at'] or now_str())[:4]}/{rid_filter(last['id'])}")
    if request.method == "POST":
        act = request.form.get("action")
        if act == "reset":
            db.execute("UPDATE course_trainees SET cert_title=NULL, cert_body=NULL, cert_footer=NULL WHERE id=?", (last["id"],))
            flash("رجع نص الشهادة إلى النص الافتراضي", "ok")
        elif act == "printed":
            db.execute(f"UPDATE course_trainees SET cert_printed_at=? WHERE id IN ({','.join('?' * len(rows))})",
                       [now_str()] + [r["id"] for r in rows])
            db.commit()
            return {"ok": True}
        else:
            db.execute("UPDATE course_trainees SET cert_title=?, cert_body=?, cert_footer=? WHERE id=?",
                       (request.form.get("title", "").strip(), request.form.get("body", "").strip(),
                        request.form.get("footer", "").strip(), last["id"]))
            flash("تم حفظ تعديلات الشهادة", "ok")
        db.commit()
        return redirect(url_for("trainee_certificate", client_id=client_id, model="ar"))
    dates = []
    for r in rows:
        ds = [d["day_date"] for d in db.execute("SELECT day_date FROM course_days WHERE trainee_id=? AND day_date IS NOT NULL", (r["id"],))]
        dates += ds or [x for x in (r["start_date"], r["end_date"], (r["enrolled_at"] or "")[:10], (r["completed_at"] or "")[:10]) if x]
    dates = sorted(d[:10] for d in dates if d)
    hours = sum(r["hours"] or 0 for r in rows)
    trainers = []
    for r in rows:
        if r["trainer"] and r["trainer"] not in trainers:
            trainers.append(r["trainer"])
    c = dict(id=last["course_id"], name=joined([r["cname"] for r in rows]), start_date=dates[0] if dates else None,
             end_date=dates[-1] if dates else None, hours=hours or None, trainer=" و".join(trainers) or None,
             branch=last["branch"])
    t = dict(last)
    t["completed_at"] = max(r["completed_at"] or "" for r in rows) or None
    _, t["price"], t["paid"] = trainee_alloc(db, client_id)
    txt = cert_texts(c, t)
    return render_template("certificate.html", c=c, t=t, txt=txt,
                           stamp=setting("stamp_img"), signature=setting("signature_img"),
                           signer=setting("cert_signer") or DEFAULT_SETTINGS["cert_signer"],
                           cert_no=f"{(t['completed_at'] or now_str())[:4]}/{rid_filter(t['id'])}")


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
            if e and (admin or (e["created_by"] == u["id"] and e["day"] == center_today().isoformat())):
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
                br, day = int(f.get("branch_id") or work_branch()), f.get("day") or center_today().isoformat()
                from_cash = 1 if f.get("from_cash") else 0
                role = f.get("role") if from_cash and f.get("role") in PLACES else None
            else:  # العامل: مصروف من صندوق اليوم في مكانه فقط
                br, day, from_cash, role = u["branch_id"], center_today().isoformat(), 1, u["role"]
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
            WHERE e.created_by=? AND e.day=? ORDER BY e.id DESC""", (u["id"], center_today().isoformat())).fetchall()
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
    today = center_today().isoformat()
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
    d1 = request.args.get("from") or center_today().replace(day=1).isoformat()
    d2 = request.args.get("to") or center_today().isoformat()
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
    d1 = request.args.get("from") or (center_today() - timedelta(days=7)).isoformat()
    d2 = request.args.get("to") or center_today().isoformat()
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
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (s_["e"]["branch_id"], center_today().isoformat(), "أجور العمال",
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


def service_profit(br, d1, d2):
    """فائدة كل خدمة في الفترة: عدد الحصص، الدخل، المواد المستعملة (بسعر الشراء)، والفائدة الصافية."""
    db = get_db()
    q = "SELECT id FROM visits WHERE status IN ('done','paid') AND substr(created_at,1,10) BETWEEN ? AND ?"
    args = [d1, d2]
    if br:
        q += " AND branch_id=?"
        args.append(br)
    out = {}

    def add(key, name, room, n, inc, cost):
        e = out.setdefault(key, {"name": name, "room": room, "n": 0, "income": 0.0, "cost": 0.0})
        e["n"] += n
        e["income"] += inc
        e["cost"] += cost

    for (vid,) in db.execute(q, args).fetchall():
        v = db.execute("SELECT * FROM visits WHERE id=?", (vid,)).fetchone()
        items = db.execute("SELECT * FROM visit_items WHERE visit_id=?", (vid,)).fetchall()
        e = session_economics(db, v, items)
        room = visit_room(v)
        parts = [(i["service_id"] or ("d:" + (i["description"] or "")), i["description"], i["qty"] * i["unit_price"])
                 for i in items if not i["product_id"]]
        if e["prepaid"] and v["appointment_id"]:
            ap = db.execute("SELECT a.service_id, s.name FROM appointments a LEFT JOIN services s ON s.id=a.service_id WHERE a.id=?",
                            (v["appointment_id"],)).fetchone()
            if ap:
                parts.append((ap["service_id"] or "d:باقة", ap["name"] or "حصة من باقة", e["prepaid"]))
        if not parts:
            if e["mat_cost"]:
                add("d:" + (v["request"] or "بدون خدمة"), v["request"] or "حصة بدون خدمة", room, 1, 0, e["mat_cost"])
            continue
        tot = sum(max(p[2], 0) for p in parts)
        for k, name, amt in parts:
            share = (max(amt, 0) / tot) if tot > 0 else 1 / len(parts)
            add(k, name, room, 1, max(amt, 0), e["mat_cost"] * share)
    # خدمات تخلّصت مباشرة بلا زيارة (موعد تكمّل)
    q2 = """SELECT ch.service_id, s.name, s.dept, p.amount FROM charges ch JOIN payments p ON p.id=ch.payment_id
        LEFT JOIN services s ON s.id=ch.service_id WHERE ch.visit_id IS NULL AND ch.service_id IS NOT NULL AND p.cancelled=0
        AND substr(p.created_at,1,10) BETWEEN ? AND ?"""
    args = [d1, d2]
    if br:
        q2 += " AND p.branch_id=?"
        args.append(br)
    for r in db.execute(q2, args):
        add(r["service_id"], r["name"] or "خدمة", r["dept"] or "", 1, r["amount"] or 0, 0)
    for k, e in out.items():
        if isinstance(k, int):
            s = db.execute("SELECT name FROM services WHERE id=?", (k,)).fetchone()
            if s:
                e["name"] = s["name"]
        e["profit"] = round(e["income"] - e["cost"], 2)
        e["avg"] = round(e["profit"] / e["n"], 2) if e["n"] else 0
        e["margin"] = round(e["profit"] / e["income"] * 100) if e["income"] > 0 else 0
    return sorted(out.values(), key=lambda e: -e["profit"])


@app.route("/reports/day")
@login_required("admin")
def day_report():
    """تقرير اليوم (كالورقة المعمول بها في المركز): حضور الموظفين ثم كل المداخيل بالاسم والجلسة والسعر."""
    db = get_db()
    d = request.args.get("d") or center_today().isoformat()
    br = int(request.args.get("branch")) if (request.args.get("branch") or "").lstrip("-").isdigit() else (scope_branch() or 0)
    att = db.execute("""SELECT e.name, a.check_in, a.check_out, a.status FROM attendance a JOIN employees e ON e.id=a.employee_id
        WHERE a.day=? AND (?=0 OR e.branch_id=?) ORDER BY e.name""", (d, br, br)).fetchall()
    pays = db.execute("""SELECT p.*, c.name AS client FROM payments p LEFT JOIN clients c ON c.id=p.client_id
        WHERE p.cancelled=0 AND substr(p.created_at,1,10)=? AND (?=0 OR p.branch_id=?) ORDER BY p.id""", (d, br, br)).fetchall()
    rows = []
    for p in pays:
        desc = p["description"] or ""
        if ": " in desc:
            desc = desc.split(": ", 1)[1]
        if p["kind"] == "product":
            its = db.execute("""SELECT pr.name, si.qty FROM sale_items si JOIN products pr ON pr.id=si.product_id
                WHERE si.payment_id=?""", (p["id"],)).fetchall()
            if its:
                desc = "، ".join(i["name"] + (f" ×{i['qty']:g}" if i["qty"] != 1 else "") for i in its)
        rows.append(dict(name=p["client"] or "—", what=desc or PAY_KINDS.get(p["kind"], ""), amount=p["amount"]))
    exp = db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE day=? AND (?=0 OR branch_id=?)",
                     (d, br, br)).fetchone()[0]
    half = max(17, (len(rows) + 1) // 2)
    return render_template("day_report.html", d=d, br=br, att=att, rows=rows, half=half,
                           total=sum(r["amount"] for r in rows), exp=exp)


@app.route("/reports/services")
@login_required("admin")
def services_profit():
    br = scope_branch()
    if request.args.get("from"):
        d1 = request.args["from"]
        d2 = request.args.get("to") or d1
        mm = None
    else:
        mm, d1, d2 = month_bounds(request.args.get("month"))
    rows = service_profit(br, d1, d2)
    grand = {k: sum(r[k] for r in rows) for k in ("n", "income", "cost", "profit")}
    return render_template("services_profit.html", rows=rows, grand=grand, br=br, mm=mm, d1=d1, d2=d2)


def month_digest(br, m):
    """ملخص الشهر في ورقة: مقارنة بالشهر الفايت + أحسن خدمة وعاملة ويوم."""
    db = get_db()
    mm, d1, d2 = month_bounds(m)
    pm, p1, p2 = month_bounds((datetime.strptime(d1, "%Y-%m-%d").date() - timedelta(days=1)).strftime("%Y-%m"))
    cur, prev = report_data(br, d1, d2), report_data(br, p1, p2)

    def mats(a, b):
        q = """SELECT COALESCE(SUM(-m.qty*COALESCE(p.cost_price,0)),0) FROM stock_moves m JOIN products p ON p.id=m.product_id
               WHERE m.kind='use' AND COALESCE(m.cancelled,0)=0 AND substr(m.created_at,1,10) BETWEEN ? AND ?"""
        return db.execute(q + (" AND m.branch_id=?" if br else ""), [a, b] + ([br] if br else [])).fetchone()[0]

    def visits_n(a, b):
        q = "SELECT COUNT(*) FROM visits WHERE status IN ('done','paid') AND substr(created_at,1,10) BETWEEN ? AND ?"
        return db.execute(q + (" AND branch_id=?" if br else ""), [a, b] + ([br] if br else [])).fetchone()[0]

    def pct(a, b):
        return None if not b else round((a - b) / abs(b) * 100)

    lines = []
    for key, label, a, b, good_up in (
            ("income", "المداخيل", cur["income"], prev["income"], True),
            ("expense", "المصاريف", cur["expense"], prev["expense"], False),
            ("mats", "مواد العمل المستعملة", mats(d1, d2), mats(p1, p2), False),
            ("profit", "الربح الصافي", cur["profit"], prev["profit"], True),
            ("visits", "الحصص (الزيارات)", visits_n(d1, d2), visits_n(p1, p2), True),
            ("served", "الزبائن الذين دفعوا", cur["served"], prev["served"], True),
            ("new", "زبائن جدد", cur["new_clients"], prev["new_clients"], True)):
        p = pct(a, b)
        lines.append(dict(key=key, label=label, cur=a, prev=b, pct=p, money=key not in ("visits", "served", "new"),
                          good=(p is None or p == 0) or ((p > 0) == good_up)))
    q = """SELECT u.full_name AS name, COUNT(*) AS n, COALESCE(SUM((SELECT SUM(qty*unit_price) FROM visit_items i WHERE i.visit_id=v.id)),0) AS rev
           FROM visits v JOIN users u ON u.id=v.done_by WHERE v.status IN ('done','paid') AND substr(v.created_at,1,10) BETWEEN ? AND ?"""
    workers = db.execute(q + (" AND v.branch_id=?" if br else "") + " GROUP BY u.id ORDER BY n DESC LIMIT 5",
                         [d1, d2] + ([br] if br else [])).fetchall()
    svc = service_profit(br, d1, d2)
    best_day = max(cur["days"], key=lambda x: x[1]) if cur["days"] and cur["max_day"] > 1 else None
    tips = []
    if lines[0]["pct"] is not None:
        tips.append(f"المداخيل {'زادت' if lines[0]['pct'] >= 0 else 'نقصت'} بـ {abs(lines[0]['pct'])}% على الشهر الماضي.")
    if svc:
        tips.append(f"أكثر خدمة جابت فائدة: {svc[0]['name']} ({svc[0]['profit']:,.0f} دج صافي).")
        low = [s for s in svc if s["income"] > 0 and s["margin"] < 30]
        if low:
            tips.append(f"خدمات فائدتها ضعيفة (أقل من 30%): {'، '.join(s['name'] for s in low[:3])} — راجعي سعرها أو موادها.")
    if cur["debts"] > 0:
        tips.append(f"ديون الزبائن الحالية: {cur['debts']:,.0f} دج.")
    return dict(mm=mm, pm=pm, d1=d1, d2=d2, lines=lines, workers=workers, svc=svc[:5], best_day=best_day,
                tips=tips, cur=cur)


@app.route("/reports/month")
@login_required("admin")
def month_report():
    br = scope_branch()
    s = month_digest(br, request.args.get("month"))
    return render_template("month_report.html", s=s, br=br)


def reorder_suggestions(br):
    """المواد اللي لازم تتشرى: اللي وصلت حد التنبيه، ولا اللي ما تكفّيش أسبوع حسب الاستهلاك تاع آخر 30 يوم.
    الكمية المقترحة تكفّي شهر (وما تنقصش على ضعف حد التنبيه)."""
    db = get_db()
    since = (center_today() - timedelta(days=30)).isoformat()
    rows = db.execute("""SELECT p.id, p.name, p.category, p.usage, COALESCE(p.cost_price,0) AS cost, COALESCE(s.qty,0) AS qty,
        COALESCE(s.min_qty,0) AS min_qty,
        (SELECT COALESCE(SUM(-m.qty),0) FROM stock_moves m WHERE m.product_id=p.id AND m.branch_id=? AND m.qty<0
           AND substr(m.created_at,1,10)>=?) AS used30,
        (SELECT pu.supplier_id FROM purchase_items pi JOIN purchases pu ON pu.id=pi.purchase_id
           WHERE pi.product_id=p.id AND pu.supplier_id IS NOT NULL ORDER BY pu.id DESC LIMIT 1) AS last_sup
        FROM products p LEFT JOIN stock s ON s.product_id=p.id AND s.branch_id=? WHERE p.active=1
        ORDER BY p.name""", (br, since, br)).fetchall()
    out = []
    open_q = {r[0]: r[1] for r in db.execute("""SELECT pi.product_id, SUM(pi.qty) FROM purchase_items pi JOIN purchases pu
        ON pu.id=pi.purchase_id WHERE pu.status='ordered' AND pu.branch_id=? GROUP BY pi.product_id""", (br,))}
    for r in rows:
        daily = r["used30"] / 30
        days_left = (r["qty"] / daily) if daily > 0 else None
        low = r["min_qty"] > 0 and r["qty"] <= r["min_qty"]
        fast = daily > 0 and days_left is not None and days_left < 7
        if not (low or fast):
            continue
        target = max(r["min_qty"] * 2, daily * 30)
        sug = math.ceil(max(target - r["qty"] - (open_q.get(r["id"]) or 0), 0))
        d = dict(r)
        d.update(daily=round(daily, 2), days_left=None if days_left is None else int(days_left), suggest=sug,
                 ordered=open_q.get(r["id"]) or 0, low=low)
        out.append(d)
    out.sort(key=lambda d: (d["days_left"] if d["days_left"] is not None else (0 if d["qty"] <= 0 else 99)))
    return out


@app.route("/purchases/auto", methods=["GET", "POST"])
@perm_required("purchases")
def purchase_auto():
    """طلبية أوتوماتيكية: البرنامج يجمع المواد التي قاربت على النفاد، والمديرة (ولا اللي عندو الصلاحية) يوافق بضغطة."""
    db = get_db()
    u = current_user()
    br = (int(request.values.get("branch")) if u["role"] == "admin" and (request.values.get("branch") or "").lstrip("-").isdigit()
          else (scope_branch() or work_branch()) if u["role"] == "admin" else u["branch_id"])
    if request.method == "POST":
        f = request.form
        groups = {}
        for pid_ in f.getlist("pick"):
            q = fnum(f.get(f"q_{pid_}"))
            if q > 0 and pid_.lstrip("-").isdigit():
                groups.setdefault(f.get(f"s_{pid_}") or "", []).append((int(pid_), q))
        made = []
        for sup, lines in groups.items():
            pid = db.execute("""INSERT INTO purchases(supplier_id,branch_id,day,notes,created_by,created_at)
                VALUES(?,?,?,?,?,?)""", (int(sup) if sup.lstrip("-").isdigit() else None, br, center_today().isoformat(),
                                         "طلبية أوتوماتيكية (مواد قاربت على النفاد)", u["id"], now_str())).lastrowid
            for p, q in lines:
                db.execute("INSERT INTO purchase_items(purchase_id,product_id,qty,unit_cost) VALUES(?,?,?,0)", (pid, p, q))
            made.append(pid)
        if made:
            audit("طلبية أوتوماتيكية", f"{len(made)} طلبية — {branch_name(br)}", br)
            db.commit()
            flash(f"تم إنشاء {len(made)} طلبية (وحدة لكل مورد). اطبعها وابعثها للمورد.", "ok")
            return redirect(url_for("purchase_view", pid=made[0]) if len(made) == 1 else url_for("purchases"))
        flash("اختر منتجًا واحدًا على الأقل", "err")
        return redirect(url_for("purchase_auto", branch=br))
    rows = reorder_suggestions(br)
    return render_template("purchase_auto.html", rows=rows, br=br,
                           sups=db.execute("SELECT * FROM suppliers WHERE active=1 ORDER BY name").fetchall(),
                           branches=active_branches() if u["role"] == "admin" else [])


# ---------------------------------------------------------------- إلغاء العمليات
# العملية الملغاة تبقى محفوظة (في «العمليات الملغاة») بصّح ما تدخلش لا في الصندوق ولا في التقارير ولا في المخزون.
OP_KINDS = {"payment": "وصل", "visit": "زيارة", "charge": "مبلغ في الانتظار", "expense": "مصروف", "stock": "حركة مخزون"}


def day_operations(db, br, day):
    """كل عمليات اليوم في الفرع (اللي ممكن تتلغى)."""
    ops = []
    for r in db.execute("""SELECT p.*, c.name AS client, u.full_name AS by_name FROM payments p LEFT JOIN clients c ON c.id=p.client_id
            LEFT JOIN users u ON u.id=p.received_by WHERE p.cancelled=0 AND p.branch_id=? AND substr(p.created_at,1,10)=?""", (br, day)):
        ops.append(dict(kind="payment", id=r["id"], at=r["created_at"], amount=r["amount"], client=r["client"], by=r["by_name"],
                        label=f"وصل {rid_filter(r['id'])} — {r['description'] or ''}"))
    for r in db.execute("""SELECT v.*, c.name AS client, u.full_name AS by_name,
            (SELECT COALESCE(SUM(qty*unit_price),0) FROM visit_items i WHERE i.visit_id=v.id) AS total
            FROM visits v JOIN clients c ON c.id=v.client_id LEFT JOIN users u ON u.id=v.created_by
            WHERE v.status<>'cancelled' AND v.branch_id=? AND substr(v.created_at,1,10)=?""", (br, day)):
        ops.append(dict(kind="visit", id=r["id"], at=r["created_at"], amount=r["total"], client=r["client"], by=r["by_name"],
                        label=f"زيارة — {VISIT_TARGETS.get(r['target'], '')} — {VISIT_STATUS.get(r['status'], '')}"))
    for r in db.execute("""SELECT ch.*, c.name AS client, u.full_name AS by_name FROM charges ch LEFT JOIN clients c ON c.id=ch.client_id
            LEFT JOIN users u ON u.id=ch.created_by WHERE ch.status IN ('pending','debt') AND ch.branch_id=?
            AND substr(ch.created_at,1,10)=?""", (br, day)):
        ops.append(dict(kind="charge", id=r["id"], at=r["created_at"], amount=r["amount"], client=r["client"], by=r["by_name"],
                        label=("دين — " if r["status"] == "debt" else "مبلغ في الانتظار — ") + (r["description"] or "")))
    for r in db.execute("""SELECT e.*, u.full_name AS by_name FROM expenses e LEFT JOIN users u ON u.id=e.created_by
            WHERE e.branch_id=? AND e.day=?""", (br, day)):
        ops.append(dict(kind="expense", id=r["id"], at=r["created_at"] or day, amount=r["amount"], client=None, by=r["by_name"],
                        label=f"مصروف — {r['category'] or ''} {r['description'] or ''}"))
    for r in db.execute("""SELECT m.*, p.name AS product, u.full_name AS by_name FROM stock_moves m JOIN products p ON p.id=m.product_id
            LEFT JOIN users u ON u.id=m.user_id WHERE m.kind='adjust' AND COALESCE(m.cancelled,0)=0 AND m.branch_id=?
            AND substr(m.created_at,1,10)=?""", (br, day)):
        ops.append(dict(kind="stock", id=r["id"], at=r["created_at"], amount=None, client=None, by=r["by_name"],
                        label=f"مخزون — {r['product']}: {r['qty']:+g} ({r['reason'] or ''})"))
    ops.sort(key=lambda o: o["at"] or "")
    return ops


def _archive(db, kind, ref_id, branch_id, day, summary, amount, reason, requested_by, data):
    db.execute("""INSERT INTO cancelled_ops(kind,ref_id,branch_id,day,summary,amount,reason,requested_by,done_by,created_at,data)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (kind, ref_id, branch_id, day, summary[:300], amount or 0, (reason or "")[:300],
                                           requested_by, current_user()["id"] if current_user() else None, now_str(),
                                           json.dumps(data, ensure_ascii=False, default=str)[:20000]))
    audit("إلغاء عملية", f"{OP_KINDS.get(kind, kind)}: {summary}" + (f" — السبب: {reason}" if reason else ""), branch_id)


def cancel_op(db, kind, ref_id, reason="", requested_by=None):
    """يلغي عملية وحدة: تبقى محفوظة في «العمليات الملغاة» وتخرج من كل الحسابات."""
    if kind == "payment":
        p = db.execute("SELECT * FROM payments WHERE id=? AND cancelled=0", (ref_id,)).fetchone()
        if not p:
            return False
        chs = [r["id"] for r in db.execute("SELECT id FROM charges WHERE payment_id=?", (ref_id,))]
        vids = {r[0] for r in db.execute("SELECT visit_id FROM charges WHERE payment_id=? AND visit_id IS NOT NULL", (ref_id,))}
        items = [dict(r) for r in db.execute("SELECT * FROM sale_items WHERE payment_id=?", (ref_id,))]
        cancel_payment_now(db, ref_id)
        if chs:
            db.execute(f"UPDATE charges SET status='cancelled' WHERE id IN ({','.join('?' * len(chs))})", chs)
        for v in vids:
            db.execute("UPDATE visits SET status='cancelled' WHERE id=?", (v,))
        _archive(db, kind, ref_id, p["branch_id"], p["created_at"][:10], f"وصل {rid_filter(ref_id)} — {p['description'] or ''}",
                 p["amount"], reason, requested_by, {"payment": dict(p), "items": items, "charges": chs})
        return True
    if kind == "visit":
        v = db.execute("SELECT * FROM visits WHERE id=? AND status<>'cancelled'", (ref_id,)).fetchone()
        if not v:
            return False
        for (pid,) in db.execute("""SELECT DISTINCT payment_id FROM charges WHERE visit_id=? AND payment_id IS NOT NULL
                AND status='paid'""", (ref_id,)).fetchall():
            cancel_op(db, "payment", pid, reason or "مع إلغاء الزيارة", requested_by)
        db.execute("UPDATE charges SET status='cancelled' WHERE visit_id=? AND status IN ('pending','debt')", (ref_id,))
        for m in db.execute("SELECT * FROM stock_moves WHERE visit_id=? AND COALESCE(cancelled,0)=0 AND kind='use'", (ref_id,)).fetchall():
            move_stock(db, m["product_id"], m["branch_id"], -m["qty"], f"إلغاء الزيارة {rid_filter(ref_id)}", kind="cancel")
            db.execute("UPDATE stock_moves SET cancelled=1 WHERE id=?", (m["id"],))
        db.execute("UPDATE visits SET status='cancelled' WHERE id=?", (ref_id,))
        c = db.execute("SELECT name FROM clients WHERE id=?", (v["client_id"],)).fetchone()
        tot = db.execute("SELECT COALESCE(SUM(qty*unit_price),0) FROM visit_items WHERE visit_id=?", (ref_id,)).fetchone()[0]
        _archive(db, kind, ref_id, v["branch_id"], v["created_at"][:10], f"زيارة {rid_filter(ref_id)} — {c[0] if c else ''}",
                 tot, reason, requested_by, {"visit": dict(v)})
        return True
    if kind == "charge":
        ch = db.execute("SELECT * FROM charges WHERE id=? AND status IN ('pending','debt')", (ref_id,)).fetchone()
        if not ch:
            return False
        db.execute("UPDATE charges SET status='cancelled' WHERE id=?", (ref_id,))
        _archive(db, kind, ref_id, ch["branch_id"], (ch["created_at"] or now_str())[:10], ch["description"] or "مبلغ",
                 ch["amount"], reason, requested_by, {"charge": dict(ch)})
        return True
    if kind == "expense":
        e = db.execute("SELECT * FROM expenses WHERE id=?", (ref_id,)).fetchone()
        if not e:
            return False
        _archive(db, kind, ref_id, e["branch_id"], e["day"], f"مصروف — {e['category'] or ''} {e['description'] or ''}",
                 e["amount"], reason, requested_by, {"expense": dict(e)})
        db.execute("DELETE FROM expenses WHERE id=?", (ref_id,))
        return True
    if kind == "stock":
        m = db.execute("SELECT m.*, p.name FROM stock_moves m JOIN products p ON p.id=m.product_id WHERE m.id=? AND COALESCE(m.cancelled,0)=0",
                       (ref_id,)).fetchone()
        if not m:
            return False
        move_stock(db, m["product_id"], m["branch_id"], -m["qty"], f"إلغاء تصحيح مخزون {m['id']}", kind="cancel")
        db.execute("UPDATE stock_moves SET cancelled=1 WHERE id=?", (ref_id,))
        _archive(db, kind, ref_id, m["branch_id"], m["created_at"][:10], f"مخزون — {m['name']}: {m['qty']:+g}", 0, reason,
                 requested_by, {"move": dict(m)})
        return True
    return False


def cancel_day(db, br, day, reason="", requested_by=None):
    n = 0
    order = {"payment": 0, "visit": 1, "charge": 2, "expense": 3, "stock": 4}
    for o in sorted(day_operations(db, br, day), key=lambda o: order[o["kind"]]):
        if cancel_op(db, o["kind"], o["id"], reason or f"إلغاء كل عمليات {day}", requested_by):
            n += 1
    audit("إلغاء كل عمليات اليوم", f"{branch_name(br)} — {day}: {n} عملية", br)
    return n


@app.route("/operations", methods=["GET", "POST"])
@perm_required("cancel_ops")
def operations():
    """إلغاء العمليات: المديرة تلغي مباشرة، والعامل يبعث طلب للمديرة."""
    db = get_db()
    u = current_user()
    admin = u["role"] == "admin"
    br = (int(request.values.get("branch")) if admin and (request.values.get("branch") or "").lstrip("-").isdigit()
          else (scope_branch() or work_branch()) if admin else u["branch_id"])
    today = center_today().isoformat()
    day = request.values.get("day") or today
    if not admin and day not in (today, (center_today() - timedelta(days=1)).isoformat()):
        day = today  # العامل يلغي غير عمليات اليوم والبارح (للأقدم: المديرة)
    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        kind, oid = request.form.get("kind"), request.form.get("id", "")
        if not reason:
            flash("اكتب سبب الإلغاء", "err")
            return redirect(url_for("operations", day=day, branch=br))
        if kind == "day":
            if admin:
                n = cancel_day(db, br, day, reason, u["id"])
                flash(f"تم إلغاء {n} عملية من يوم {day}. وهي محفوظة في «العمليات الملغاة».", "ok")
            else:
                request_approval(db, "cxl_day", br, br, 0, reason, f"{day} — {branch_name(br)}")
                flash("أُرسل الطلب إلى المديرة", "ok")
        elif kind in OP_KINDS and oid.lstrip("-").isdigit():
            oid = int(oid)
            if admin or (day == today and setting("staff_direct_cancel") != "0"):
                ok = cancel_op(db, kind, oid, reason, u["id"])
                if ok and not admin:
                    audit("إلغاء عملية", f"{OP_KINDS.get(kind)} {rid_filter(oid)} — {reason}", br)
                flash("تم الإلغاء. العملية محفوظة في «العمليات الملغاة» ولا تدخل في الحسابات." if ok
                      else "العملية أُلغيت سابقًا أو تغيّرت", "ok" if ok else "err")
            else:
                op = next((o for o in day_operations(db, br, day) if o["kind"] == kind and o["id"] == oid), None)
                if op:
                    request_approval(db, "cxl_" + kind, oid, br, op["amount"] or 0, reason,
                                     f"{op['label']}" + (f" — {op['client']}" if op["client"] else ""))
                    flash("أُرسل طلب الإلغاء إلى المديرة", "ok")
        db.commit()
        return redirect(url_for("operations", day=day, branch=br))
    ops = day_operations(db, br, day)
    pend = {(r["kind"][4:], r["ref_id"]) for r in db.execute(
        "SELECT kind, ref_id FROM approvals WHERE status='pending' AND kind LIKE 'cxl_%'")}
    done = db.execute("""SELECT o.*, u.full_name AS by_name, r.full_name AS req_name FROM cancelled_ops o
        LEFT JOIN users u ON u.id=o.done_by LEFT JOIN users r ON r.id=o.requested_by WHERE o.branch_id=? AND o.day=? ORDER BY o.id DESC""",
                      (br, day)).fetchall()
    return render_template("operations.html", ops=ops, pend=pend, done=done, day=day, br=br, admin=admin, direct=(day == today and setting("staff_direct_cancel") != "0"),
                           branches=active_branches() if admin else [], today=today)


@app.route("/operations/cancelled")
@login_required("admin")
def cancelled_ops():
    """أرشيف العمليات الملغاة (محفوظة، ما تدخلش في الحسابات)."""
    db = get_db()
    br = scope_branch()
    mm, d1, d2 = month_bounds(request.args.get("month"))
    q = """SELECT o.*, u.full_name AS by_name, r.full_name AS req_name, b.name AS branch FROM cancelled_ops o
        LEFT JOIN users u ON u.id=o.done_by LEFT JOIN users r ON r.id=o.requested_by JOIN branches b ON b.id=o.branch_id
        WHERE o.day BETWEEN ? AND ?"""
    args = [d1, d2]
    if br:
        q += " AND o.branch_id=?"
        args.append(br)
    rows = db.execute(q + " ORDER BY o.id DESC", args).fetchall()
    return render_template("cancelled_ops.html", rows=rows, mm=mm, br=br)


# ---------------------------------------------------------------- إدارة المخزون (الجرد والتصحيح)
STOCK_REASONS = ["خطأ في العدّ", "مواد استُعملت ولم تُسجَّل", "تلف", "انتهاء الصلاحية", "ضياع", "سلعة دخلت ولم تُسجَّل", "أخرى"]


@app.route("/stock/opening", methods=["GET", "POST"])
@perm_required("products_edit")
def stock_opening():
    """إدخال المخزون الموجود في الفرع (قبل البرنامج أو عند الجرد): تكتب الكمية الموجودة لكل منتج وتحفظ مرة واحدة."""
    db = get_db()
    u = current_user()
    admin = u["role"] == "admin"
    br = (int(request.values.get("branch")) if admin and (request.values.get("branch") or "").lstrip("-").isdigit()
          else (scope_branch() or work_branch()) if admin else u["branch_id"])
    can_cost = admin or has_perm("cost_prices")
    can_price = admin or has_perm("sale_prices")
    if request.method == "POST":
        f = request.form
        n = 0
        for k, val in f.items():
            if not k.startswith("q_") or val.strip() == "" or not k[2:].lstrip("-").isdigit():
                continue
            pid = int(k[2:])
            cur = db.execute("SELECT COALESCE(qty,0) FROM stock WHERE product_id=? AND branch_id=?", (pid, br)).fetchone()
            diff = round(fnum(val) - (cur[0] if cur else 0), 3)
            if diff:
                move_stock(db, pid, br, diff, "مخزون موجود (إدخال المخزون)", u["id"], kind="adjust")
                n += 1
            c = f.get(f"c_{pid}", "").strip()
            if can_cost and c and fnum(c) > 0:
                db.execute("UPDATE products SET cost_price=? WHERE id=?", (fnum(c), pid))
            sp = f.get(f"s_{pid}", "").strip()
            if can_price and sp and fnum(sp) > 0:
                old = db.execute("SELECT name, price FROM products WHERE id=?", (pid,)).fetchone()
                if old and fnum(sp) != (old["price"] or 0):
                    db.execute("UPDATE products SET price=? WHERE id=?", (fnum(sp), pid))
                    audit("تغيير سعر البيع", f"{old['name']}: {(old['price'] or 0):g} ← {fnum(sp):g}", br)
                    if not admin:
                        db.execute("UPDATE products SET needs_review=1, review_note=? WHERE id=?",
                                   (f"تغيّر سعر البيع عند إدخال المخزون: {(old['price'] or 0):g} ← {fnum(sp):g}", pid))
        if n:
            audit("إدخال المخزون الموجود", f"{n} منتج — {branch_name(br)}", br)
        db.commit()
        flash(f"تم حفظ المخزون: {n} منتج تغيّرت كميته" if n else "لا يوجد أي تغيير", "ok")
        return redirect(url_for("stock_opening", branch=br))
    rows = db.execute("""SELECT p.id, p.name, COALESCE(p.category,'') AS category, p.usage, COALESCE(p.cost_price,0) AS cost,
        COALESCE(p.price,0) AS price, COALESCE(s.qty,0) AS qty FROM products p
        LEFT JOIN stock s ON s.product_id=p.id AND s.branch_id=? WHERE p.active=1
        ORDER BY CASE WHEN p.usage='use' THEN 1 ELSE 0 END, COALESCE(p.category,'ي'), p.id""", (br,)).fetchall()
    return render_template("stock_opening.html", rows=[dict(r) for r in rows], br=br, can_cost=can_cost, can_price=can_price,
                           branches=active_branches() if admin else [])


@app.route("/stock/manage", methods=["GET", "POST"])
@perm_required("products_edit")
def stock_manage():
    """تكتب الكمية الحقيقية التي وجدتها، والبرنامج يحسب الفرق ويسجّلو بالسبب."""
    db = get_db()
    u = current_user()
    admin = u["role"] == "admin"
    br = (int(request.values.get("branch")) if admin and (request.values.get("branch") or "").lstrip("-").isdigit()
          else (scope_branch() or work_branch()) if admin else u["branch_id"])
    if request.method == "POST":
        f = request.form
        reason = f.get("reason") if f.get("reason") in STOCK_REASONS else None
        note = f.get("note", "").strip()
        if not reason:
            flash("اختر سبب التصحيح", "err")
            return redirect(url_for("stock_manage", branch=br))
        n = 0
        for k, val in f.items():
            if not k.startswith("real_") or val.strip() == "":
                continue
            pid = k[5:]
            if not pid.lstrip("-").isdigit():
                continue
            pid = int(pid)
            cur = db.execute("SELECT COALESCE(qty,0) FROM stock WHERE product_id=? AND branch_id=?", (pid, br)).fetchone()
            cur = cur[0] if cur else 0
            diff = round(fnum(val) - cur, 3)
            if diff:
                move_stock(db, pid, br, diff, f"تصحيح: {reason}" + (f" — {note}" if note else ""), u["id"], kind="adjust")
                n += 1
        if n:
            audit("تصحيح مخزون", f"{n} منتج — {reason} — {branch_name(br)}", br)
            db.commit()
            flash(f"تم تصحيح {n} منتج", "ok")
        else:
            flash("لا يوجد أي فرق: الكميات كما هي", "ok")
        return redirect(url_for("stock_manage", branch=br))
    q = request.args.get("q", "").strip()
    rows = db.execute("""SELECT p.id, p.name, p.category, p.usage, COALESCE(p.cost_price,0) AS cost, COALESCE(s.qty,0) AS qty
        FROM products p LEFT JOIN stock s ON s.product_id=p.id AND s.branch_id=? WHERE p.active=1
        AND (?='' OR p.name LIKE ?) ORDER BY p.usage, p.category, p.name""", (br, q, f"%{q}%")).fetchall()
    since = (center_today() - timedelta(days=60)).isoformat()
    log = db.execute("""SELECT m.*, p.name, COALESCE(p.cost_price,0) AS cost, u.full_name AS by_name FROM stock_moves m
        JOIN products p ON p.id=m.product_id LEFT JOIN users u ON u.id=m.user_id
        WHERE m.kind='adjust' AND m.branch_id=? AND substr(m.created_at,1,10)>=? ORDER BY m.id DESC LIMIT 200""",
                     (br, since)).fetchall()
    loss = sum(-m["qty"] * m["cost"] for m in log if m["qty"] < 0 and not m["cancelled"])
    return render_template("stock_manage.html", rows=rows, log=log, loss=loss, br=br, q=q, reasons=STOCK_REASONS,
                           branches=active_branches() if admin else [], printing=bool(request.args.get("print")),
                           can_cost=admin or has_perm("cost_prices"))


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
        parts = []
        if request.form.getlist("area"):
            parts.append("المنطقة: " + "، ".join(request.form.getlist("area")))
        for k, lbl in (("reaction", "رد فعل البشرة"), ("settings", "الجهاز / الإعدادات"), ("advice", "التوصية")):
            if request.form.get(k, "").strip():
                parts.append(f"{lbl}: {request.form[k].strip()}")
        if parts:
            note = "🧴 " + " · ".join(parts) + (f" — {note}" if note else "")
        if note:
            db.execute("INSERT INTO client_notes(client_id,branch_id,visit_id,note,created_by,created_at) VALUES(?,?,?,?,?,?)",
                       (cid, u["branch_id"] or work_branch(), request.form.get("visit_id") or None, note, u["id"], now_str()))
            flash("تمت إضافة الملاحظة إلى الملف", "ok")
    db.commit()
    return redirect(request.referrer or url_for("client_view", cid=cid))


def skin_card(db, cid):
    return db.execute("SELECT * FROM skin_cards WHERE client_id=? ORDER BY id DESC LIMIT 1", (cid,)).fetchone()


@app.route("/clients/<int(signed=True):cid>/skin", methods=["POST"])
@perm_required("medical")
def client_skin(cid):
    """بطاقة البشرة: نوع البشرة، الفوتوتايب، المشاكل، وموانع العلاج."""
    db = get_db()
    db.execute("SELECT 1 FROM clients WHERE id=?", (cid,)).fetchone() or abort(404)
    f = request.form
    vals = (f.get("skin_type") if f.get("skin_type") in SKIN_TYPES else None,
            f.get("phototype") if f.get("phototype") in PHOTOTYPES else None,
            "، ".join(x for x in f.getlist("concerns") if x in SKIN_CONCERNS),
            "، ".join(x for x in f.getlist("contra") if x in SKIN_CONTRA),
            f.get("sensitivities", "").strip(), f.get("routine", "").strip(), f.get("notes", "").strip(),
            current_user()["id"], now_str())
    old = skin_card(db, cid)
    if old:
        db.execute("""UPDATE skin_cards SET skin_type=?, phototype=?, concerns=?, contra=?, sensitivities=?, routine=?, notes=?,
            updated_by=?, updated_at=? WHERE id=?""", vals + (old["id"],))
    else:
        db.execute("""INSERT INTO skin_cards(skin_type,phototype,concerns,contra,sensitivities,routine,notes,updated_by,updated_at,client_id)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", vals + (cid,))
    db.commit()
    flash("تم حفظ بطاقة البشرة", "ok")
    return redirect(request.referrer or url_for("client_view", cid=cid))


@app.route("/visits/<int(signed=True):vid>/aftercare")
@login_required()
def visit_aftercare(vid):
    """ورقة «نصائح بعد الجلسة» تتطبع وتتعطى للزبونة."""
    db = get_db()
    v, items, total = visit_data(vid)
    u = current_user()
    if u["role"] in ("laser", "beauty") and v["target"] != u["role"]:
        abort(403)
    sids = [i["service_id"] for i in items if i["service_id"]]
    if v["appointment_id"]:
        r = db.execute("SELECT service_id FROM appointments WHERE id=?", (v["appointment_id"],)).fetchone()
        if r and r[0] and r[0] not in sids:
            sids.append(r[0])
    tips = []
    for sid in sids:
        s = db.execute("SELECT * FROM services WHERE id=?", (sid,)).fetchone()
        if s and aftercare_for(s):
            tips.append((s["name"], aftercare_for(s).split("\n")))
    nxt = db.execute("""SELECT start_at FROM appointments WHERE client_id=? AND status='scheduled' AND start_at>? ORDER BY start_at LIMIT 1""",
                     (v["client_id"], now_str()[:16])).fetchone()
    return render_template("aftercare.html", v=v, tips=tips, nxt=nxt)


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
                birth_date=fmt_date(c["birth_date"]), date=fmt_date(center_today().isoformat()))

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
    q = """SELECT p.*, s.name AS supplier, b.name AS branch, uu.full_name AS by_name,
        (SELECT COALESCE(SUM(qty*unit_cost),0) FROM purchase_items i WHERE i.purchase_id=p.id) AS total,
        (SELECT COALESCE(SUM(amount),0) FROM expenses e WHERE e.purchase_id=p.id) AS paid
        FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id JOIN branches b ON b.id=p.branch_id
        LEFT JOIN users uu ON uu.id=p.created_by WHERE 1=1"""
    args = []
    if br:
        q += " AND p.branch_id=?"
        args.append(br)
    if request.args.get("supplier"):
        q += " AND p.supplier_id=?"
        args.append(request.args["supplier"])
    rows = db.execute(q + " ORDER BY p.id DESC LIMIT 300", args).fetchall()
    who = []
    if current_user()["role"] == "admin":  # المديرة تختار من يستطيع إدخال المشتريات
        for b in active_branches():
            for place in ["reception"] + [k for k in branch_depts(b["id"]) if k in ("laser", "beauty")]:
                pp = place_perms(b["id"], place)
                who.append(dict(branch_id=b["id"], branch=b["name"], role=place, place=PLACES[place],
                                purchases=pp.get("purchases"), expenses=pp.get("expenses")))
    return render_template("purchases.html", rows=rows, br=br, who=who)


@app.route("/purchases/new", methods=["GET", "POST"])
@perm_required("purchases")
def purchase_new():
    db = get_db()
    if request.method == "POST":
        f = request.form
        pids, qtys = f.getlist("product_id"), f.getlist("qty")
        lines = [(int(p), fnum(q), 0.0) for p, q in zip(pids, qtys) if p and p.lstrip("-").isdigit() and fnum(q) > 0]
        if not lines:
            flash("أضف منتجًا واحدًا على الأقل بكمية", "err")
            return redirect(url_for("purchase_new"))
        u = current_user()
        can_cost = u["role"] == "admin" or has_perm("cost_prices")
        costs = f.getlist("cost")
        if can_cost and costs:
            lines = [(p_, q_, fnum(costs[i]) if i < len(costs) else 0.0) for i, (p_, q_, _) in enumerate(lines)] \
                if len(costs) == len(pids) else lines
            # إعادة ربط الأسعار بالأسطر الصحيحة (الأسطر الفارغة حُذفت)
            lines = []
            for p_, q_, c_ in zip(pids, qtys, costs):
                if p_ and p_.lstrip("-").isdigit() and fnum(q_) > 0:
                    lines.append((int(p_), fnum(q_), fnum(c_)))
        br_ = u["branch_id"] or int(f.get("branch_id") or work_branch())
        pid = db.execute("""INSERT INTO purchases(supplier_id,branch_id,day,notes,created_by,created_at)
            VALUES(?,?,?,?,?,?)""", (f.get("supplier_id") or None, br_,
                                     f.get("day") or center_today().isoformat(), f.get("notes", "").strip(),
                                     u["id"], now_str())).lastrowid
        for p_, q_, c_ in lines:
            db.execute("INSERT INTO purchase_items(purchase_id,product_id,qty,unit_cost) VALUES(?,?,?,?)", (pid, p_, q_, c_))
        # سعر البيع الجديد (إذا ارتفع سعر الشراء)
        can_price = u["role"] == "admin" or has_perm("sale_prices")
        if can_price:
            changed = []
            for p_, q_, sp_ in zip(pids, qtys, f.getlist("sale")):
                if not (p_ and p_.lstrip("-").isdigit()) or fnum(q_) <= 0 or not sp_.strip() or fnum(sp_) <= 0:
                    continue
                old = db.execute("SELECT name, price FROM products WHERE id=?", (int(p_),)).fetchone()
                if old and fnum(sp_) != (old["price"] or 0):
                    db.execute("UPDATE products SET price=? WHERE id=?", (fnum(sp_), int(p_)))
                    changed.append(f"{old['name']}: {(old['price'] or 0):g} ← {fnum(sp_):g}")
                    if u["role"] != "admin":
                        db.execute("UPDATE products SET needs_review=1, review_note=?, added_by=? WHERE id=?",
                                   (f"تغيّر سعر البيع عند الشراء: {(old['price'] or 0):g} ← {fnum(sp_):g}", u["id"], int(p_)))
            if changed:
                audit("تغيير أسعار البيع عند الشراء", f"{rid_filter(pid)}: " + "، ".join(changed), br_)
        if f.get("received") == "1":  # شراء سريع: السلعة وصلت الآن
            for p_, q_, c_ in lines:
                move_stock(db, p_, br_, q_, f"شراء — {rid_filter(pid)}", u["id"])
                if c_ > 0:
                    db.execute("UPDATE products SET cost_price=? WHERE id=?", (c_, p_))
            db.execute("UPDATE purchases SET status='received', received_at=? WHERE id=?", (now_str(), pid))
            amount = fnum(f.get("paid_now")) if has_perm("expenses") else 0
            if amount > 0:
                worker = u["role"] != "admin"
                sup = db.execute("SELECT name FROM suppliers WHERE id=?", (f.get("supplier_id") or 0,)).fetchone()
                db.execute("""INSERT INTO expenses(branch_id,day,category,description,amount,method,supplier_id,purchase_id,
                    created_by,created_at,from_cash,role) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (br_, center_today().isoformat(), "شراء سلع (منتجات)",
                            f"مشتريات {rid_filter(pid)} — {sup['name'] if sup else ''}", amount,
                            "cash" if worker else f.get("method", "cash"), f.get("supplier_id") or None, pid, u["id"],
                            now_str(), 1 if worker else 0, u["role"] if worker else None))
            audit("مشتريات (استلام فوري)", f"{rid_filter(pid)}: {len(lines)} منتج", br_)
            db.commit()
            flash("تم تسجيل المشتريات: المخزون زاد مباشرة", "ok")
            return redirect(url_for("purchase_view", pid=pid))
        db.commit()
        flash("تم إنشاء طلبية الشراء", "ok")
        return redirect(url_for("purchase_view", pid=pid))
    prods = db.execute("SELECT id,name,cost_price,price,category FROM products WHERE active=1 ORDER BY category,name").fetchall()
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
    items = db.execute("""SELECT i.*, pr.name, pr.cost_price, pr.price FROM purchase_items i JOIN products pr ON pr.id=i.product_id
        WHERE i.purchase_id=? ORDER BY i.id""", (pid,)).fetchall()
    total = round(sum(i["qty"] * i["unit_cost"] for i in items), 2)
    paid = db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE purchase_id=?", (pid,)).fetchone()[0]
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        if act == "receive" and p["status"] == "ordered":
            can_price = u["role"] == "admin" or has_perm("sale_prices")
            can_cost = u["role"] == "admin" or has_perm("cost_prices")
            changed = []
            for i in items:
                q = fnum(f.get(f"rq_{i['id']}"), i["qty"])  # الكمية التي وصلت فعلًا (قد تكون أقل)
                c = fnum(f.get(f"rc_{i['id']}"), i["unit_cost"]) if can_cost else i["unit_cost"]  # سعر الشراء: اختياري
                if not c:
                    c = i["cost_price"] or 0  # ما كتبوش: نخلّيو سعر الشراء القديم
                db.execute("UPDATE purchase_items SET qty=?, unit_cost=? WHERE id=?", (q, c, i["id"]))
                if q > 0:
                    move_stock(db, i["product_id"], p["branch_id"], q, f"شراء — طلبية {rid_filter(pid)}", u["id"])
                    if c > 0 and c != (i["cost_price"] or 0):
                        db.execute("UPDATE products SET cost_price=? WHERE id=?", (c, i["product_id"]))
                        if u["role"] != "admin":
                            changed.append(f"{i['name']} (شراء): {(i['cost_price'] or 0):g} ← {c:g}")
                sp = f.get(f"sp_{i['id']}")
                if can_price and sp not in (None, "") and fnum(sp) > 0 and fnum(sp) != (i["price"] or 0):
                    new = fnum(sp)
                    db.execute("UPDATE products SET price=? WHERE id=?", (new, i["product_id"]))
                    changed.append(f"{i['name']}: {(i['price'] or 0):g} ← {new:g}")
                    if u["role"] != "admin":
                        db.execute("UPDATE products SET needs_review=1, review_note=?, added_by=? WHERE id=?",
                                   (f"تغيّر السعر عند الاستلام: {(i['price'] or 0):g} ← {new:g}", u["id"], i["product_id"]))
            if changed:
                audit("تغيير أسعار عند الاستلام", f"طلبية {rid_filter(pid)}: " + "، ".join(changed), p["branch_id"])
            db.execute("UPDATE purchases SET status='received', received_at=? WHERE id=?", (now_str(), pid))
            amount = fnum(f.get("paid_now")) if has_perm("expenses") else 0
            if amount > 0:
                worker = u["role"] != "admin"
                db.execute("""INSERT INTO expenses(branch_id,day,category,description,amount,method,supplier_id,purchase_id,
                    created_by,created_at,from_cash,role) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (p["branch_id"], center_today().isoformat(), "شراء سلع (منتجات)",
                            f"طلبية {rid_filter(pid)} — {p['supplier'] or ''}", amount, "cash" if worker else f.get("method", "cash"),
                            p["supplier_id"], pid, u["id"], now_str(), 1 if worker else 0, u["role"] if worker else None))
            audit("استلام سلعة", f"طلبية {rid_filter(pid)} — {p['supplier'] or ''}", p["branch_id"])
            flash("تم استلام الطلبية: المخزون زاد، وسعر الشراء تحدّث", "ok")
        elif act == "pay":
            if u["role"] != "admin":
                abort(403)
            amount = fnum(f.get("amount"))
            if amount > 0:
                db.execute("""INSERT INTO expenses(branch_id,day,category,description,amount,method,supplier_id,purchase_id,
                    created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                           (p["branch_id"], center_today().isoformat(), "شراء سلع (منتجات)",
                            f"تسديد طلبية {rid_filter(pid)} — {p['supplier'] or ''}", amount, f.get("method", "cash"),
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
                    db.execute("UPDATE purchase_items SET qty=? WHERE id=?", (q, i["id"]))
            flash("تم حفظ الطلبية", "ok")
        db.commit()
        return redirect(url_for("purchase_view", pid=pid))
    return render_template("purchase_view.html", p=p, items=items, total=total, paid=paid,
                           now=center_now().strftime("%Y-%m-%d %H:%M"))


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
        devs = {}
        lim = (center_now() - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
        for dv in db.execute("SELECT full_name, role, last_seen FROM users WHERE device=1 AND active=1 AND branch_id=?",
                             (br["id"],)):
            devs.setdefault(dv["role"], []).append(dict(full_name=dv["full_name"], last_seen=dv["last_seen"],
                                                         online=bool(dv["last_seen"] and dv["last_seen"] >= lim)))
        data.append(dict(b=br, places=places, staff=staff, devices=devs,
                         perms={p: place_perms(br["id"], p) for p in places}))
    return render_template("permissions.html", data=data, PERMS=PERMS, PLACES=PLACES)


# ---------------------------------------------------------------- النسخ الاحتياطي
def backup_status():
    db = get_db()
    last = setting("backup_last")
    age = None
    if last:
        try:
            age = (center_now() - datetime.strptime(last, "%Y-%m-%d %H:%M:%S")).total_seconds() / 3600
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
                v = request.form.get(k, "").strip()
                if v:
                    try:  # نتأكد أن المكان موجود ويقبل الكتابة
                        os.makedirs(v, exist_ok=True)
                        tf = os.path.join(v, ".bilsan_test")
                        open(tf, "w").close()
                        os.remove(tf)
                    except OSError as e:
                        flash(f"لا يمكن الحفظ في «{v}»: {e}", "err")
                        return redirect(url_for("backup_page"))
                db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, v))
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
    return render_template("backup.html", st=st, files=files, total=total, dbsize=dbsize, central=not sync.NODE,
                           pending=os.path.exists(os.path.join(BASE_DIR, "restore_pending.txt")))



@app.route("/api/hijama-days")
@login_required()
def api_hijama_days():
    """عدد المواعيد في كل يوم من الأيام القادمة (لبطاقة «أيام الحجامة المسنونة القادمة»)."""
    db = get_db()
    u = current_user()
    br = u["branch_id"] or scope_branch()
    d1 = center_today().isoformat()
    d2 = (center_today() + timedelta(days=75)).isoformat()
    q = """SELECT substr(start_at,1,10) d, COUNT(*) n FROM appointments WHERE status IN ('scheduled','done')
        AND substr(start_at,1,10) BETWEEN ? AND ?"""
    args = [d1, d2]
    if br:
        q += " AND branch_id=?"
        args.append(br)
    return {"today": d1, "counts": {r["d"]: r["n"] for r in db.execute(q + " GROUP BY d", args)}}


# ---------------------------------------------------------------- اختيار مكان النسخ الاحتياطي
@app.route("/backup/browse")
@login_required("admin")
def backup_browse():
    """تصفّح مجلدات الحاسوب لاختيار مكان حفظ النسخ الاحتياطية."""
    p = request.args.get("p", "").strip()
    drives = []
    if os.name == "nt":
        import string
        drives = [f"{c}:\\" for c in string.ascii_uppercase if os.path.exists(f"{c}:\\")]
    else:
        drives = ["/"]
    if not p or not os.path.isdir(p):
        return {"path": "", "parent": "", "dirs": [], "drives": drives}
    p = os.path.abspath(p)
    dirs = []
    try:
        for n in sorted(os.listdir(p), key=str.lower):
            fp = os.path.join(p, n)
            if os.path.isdir(fp) and not n.startswith(("$", ".")) and n not in ("System Volume Information", "Windows",
                                                                              "Program Files", "Program Files (x86)", "ProgramData"):
                dirs.append(n)
    except OSError:
        pass
    parent = os.path.dirname(p.rstrip("\\/")) if p.rstrip("\\/") != p[:3].rstrip("\\/") else ""
    if os.name == "nt" and len(p) <= 3:
        parent = ""
    return {"path": p, "parent": parent, "dirs": dirs[:400], "drives": drives}


@app.route("/backup/mkdir", methods=["POST"])
@login_required("admin")
def backup_mkdir():
    base, name = request.form.get("p", ""), re.sub(r'[<>:"/\\|?*]', "", request.form.get("name", "")).strip()
    if not name or not os.path.isdir(base):
        return {"ok": False}
    try:
        os.makedirs(os.path.join(base, name), exist_ok=True)
        return {"ok": True, "path": os.path.join(base, name)}
    except OSError as e:
        return {"ok": False, "err": str(e)}


# ---------------------------------------------------------------- مسح كل البيانات (الرجوع من الصفر)
RESET_ALWAYS = ["visit_items", "visits", "sale_items", "charges", "payments", "appointments", "plans", "client_notes",
                "client_photos", "skin_cards", "clients", "course_days", "course_trainees", "courses", "expenses", "purchase_items",
                "purchases", "stock_moves", "approvals", "cancelled_ops", "cash_days", "sms_log", "audit"]
RESET_STAFF = ["grants", "attendance", "employees"]
RESET_CATALOG = ["service_materials", "stock", "products", "services", "suppliers"]


@app.route("/factory-reset", methods=["POST"])
@login_required("admin")
def factory_reset():
    """يمسح كل العمليات والزبائن ويرجع البرنامج من الصفر. في حاسوب المديرة فقط، بكلمة سرها."""
    if sync.NODE:
        abort(403)
    db = get_db()
    u = current_user()
    f = request.form
    if not check_password_hash(u["pw_hash"], f.get("password", "")):
        flash("كلمة المرور غير صحيحة، لم يُمسح شيء", "err")
        return redirect(url_for("backup_page"))
    if f.get("confirm", "").strip() != "مسح":
        flash("اكتب كلمة «مسح» للتأكيد، لم يُمسح شيء", "err")
        return redirect(url_for("backup_page"))
    ok, msg = backup.run_backup(connect, DB_PATH, "قبل مسح كل البيانات")
    if not ok:
        flash("تعذّرت النسخة الاحتياطية قبل المسح، فلم يُمسح شيء: " + msg, "err")
        return redirect(url_for("backup_page"))
    tables = list(RESET_ALWAYS) + (RESET_STAFF if f.get("staff") else []) + (RESET_CATALOG if f.get("catalog") else [])
    for t in tables:
        db.execute(f"DELETE FROM {t}")
    if not f.get("catalog"):
        db.execute("UPDATE stock SET qty=0")
    db.commit()
    audit("مسح كل البيانات", "رجوع البرنامج من الصفر" + (" مع العمال" if f.get("staff") else "")
          + (" مع المنتجات والخدمات" if f.get("catalog") else "") + f" — نسخة قبل المسح: {msg}")
    db.commit()
    flash("تم مسح كل البيانات، والبرنامج يبدأ من الصفر. حُفظت نسخة احتياطية قبل المسح في صفحة «النسخ الاحتياطي».", "ok")
    return redirect(url_for("dashboard"))


@app.route("/clients/delete-all", methods=["POST"])
@login_required("admin")
def clients_delete_all():
    """حذف جميع الزبائن (من حاسوب المديرة فقط، بكلمة مرورها).
    تُحذف ملفاتهم ومواعيدهم وخططهم وزياراتهم والمبالغ غير المدفوعة،
    وتبقى المداخيل المقبوضة في الصندوق والتقارير لكن بدون اسم زبون."""
    if sync.NODE:
        abort(403)
    db = get_db()
    u = current_user()
    if not check_password_hash(u["pw_hash"], request.form.get("password", "")):
        flash("كلمة المرور غير صحيحة، لم يُحذف شيء", "err")
        return redirect(url_for("clients"))
    if request.form.get("confirm", "").strip() != "حذف":
        flash("اكتبي كلمة «حذف» للتأكيد، لم يُحذف شيء", "err")
        return redirect(url_for("clients"))
    ok, msg = backup.run_backup(connect, DB_PATH, "قبل حذف الزبائن")
    if not ok:
        flash("تعذّرت النسخة الاحتياطية قبل الحذف، فلم يُحذف شيء: " + msg, "err")
        return redirect(url_for("clients"))
    n = db.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    for t in ("client_notes", "client_photos", "skin_cards", "appointments", "plans", "course_trainees"):
        db.execute(f"DELETE FROM {t}")
    db.execute("UPDATE stock_moves SET visit_id=NULL WHERE visit_id IS NOT NULL")
    db.execute("DELETE FROM visit_items")
    db.execute("DELETE FROM visits")
    db.execute("DELETE FROM charges WHERE status IN ('pending','debt','cancelled')")
    db.execute("UPDATE charges SET client_id=NULL, visit_id=NULL WHERE client_id IS NOT NULL OR visit_id IS NOT NULL")
    db.execute("UPDATE payments SET client_id=NULL WHERE client_id IS NOT NULL")
    db.execute("DELETE FROM clients")
    audit("حذف جميع الزبائن", f"{n} زبون — نسخة قبل الحذف: {msg}")
    db.commit()
    flash(f"تم حذف جميع الزبائن ({n}). المداخيل المقبوضة باقية في الصندوق والتقارير. حُفظت نسخة احتياطية قبل الحذف.", "ok")
    return redirect(url_for("clients"))

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
    st["adv"], st["credit"] = plan_credit(db, plan_id)
    st["remaining"] = round(total - st["paid"] - max(st["credit"], 0), 2)
    st["advances"] = db.execute("SELECT * FROM payments WHERE plan_id=? AND cancelled=0 ORDER BY id", (plan_id,)).fetchall()
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
        srv_row = db.execute("SELECT * FROM services WHERE id=?", (f.get("service_id") or 0,)).fetchone()
        # السعر: من الباقة التي حددتها المديرة. العامل ما يبدّلوش: يطلب سعر آخر (موافقة المديرة)
        if srv_row and (srv_row["pkg_total"] or 0) > 0 and n == (srv_row["pkg_sessions"] or 1):
            list_total, list_mode = srv_row["pkg_total"], "total"
        else:
            list_total, list_mode = round((srv_row["price"] if srv_row else 0) * n, 2), "session"
        admin = u["role"] == "admin"
        if admin and f.get("total_price") not in (None, ""):
            total, mode = fnum(f.get("total_price")), "total"
        else:
            total, mode = list_total, list_mode
        each = round(total / n, 2) if n else 0
        prices = [each] * n
        prices[-1] = round(total - each * (n - 1), 2)
        pay_mode = f.get("pay_mode") if (admin and f.get("pay_mode") in ("session", "full")) else \
            ((srv_row["pkg_pay"] if srv_row else None) or "session")
        srv = f.get("service_id") or None
        title = f.get("title", "").strip()
        if not title and srv_row:
            title = srv_row["name"] + (f" — {n} حصص" if n > 1 else "")
        title = title or f"{DEPTS.get(dept)} — {n} حصص"
        post = f.get("post_id") or None
        pid = db.execute("""INSERT INTO plans(client_id,branch_id,dept,service_id,post_id,title,total_price,price_mode,
            notes,created_by,created_at,pay_mode) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (int(f["client_id"]), br, dept, srv, post, title, total, mode,
                          f.get("notes", "").strip(), u["id"], now_str(), pay_mode)).lastrowid
        # التواريخ: من الجدول المعروض (يتعمّر وحدو ويتبدّل باليد)
        ds, ts = f.getlist("sd"), f.getlist("st")
        start = None
        if not ds and f.get("first_date"):
            try:
                start = datetime.strptime(f"{f['first_date']} {f.get('time') or '09:00'}", "%Y-%m-%d %H:%M")
            except ValueError:
                start = None
        step = int(fnum(f.get("interval"), 0))
        for i in range(n):
            at = None
            if i < len(ds) and ds[i]:
                at = f"{ds[i]} {(ts[i] if i < len(ts) and ts[i] else f.get('time') or '09:00')}"
            elif start and (i == 0 or step > 0):
                at = (start + timedelta(days=step * i)).strftime("%Y-%m-%d %H:%M")
            db.execute("""INSERT INTO appointments(client_id,branch_id,dept,service_id,start_at,status,created_by,
                created_at,plan_id,session_no,price,paid,post_id) VALUES(?,?,?,?,?,'scheduled',?,?,?,?,?,0,?)""",
                       (int(f["client_id"]), br, dept, srv, at, u["id"], now_str(), pid, i + 1, prices[i], post))
        if pay_mode == "full" and total > 0:  # الباقة كاملة: المبلغ كله يروح للاستقبال يتخلّص
            db.execute("""INSERT INTO charges(branch_id,client_id,dept,service_id,description,amount,created_by,created_at,plan_id)
                VALUES(?,?,?,?,?,?,?,?,?)""", (br, int(f["client_id"]), dept, srv, f"باقة: {title}", total, u["id"],
                                               now_str(), pid))
        want = f.get("want_price", "").strip()
        if want and not admin and fnum(want) > 0 and fnum(want) != total:
            request_approval(db, "plan_price", pid, br, fnum(want), f.get("want_reason"),
                             f"{title} — السعر الحالي {total:g}")
            flash("أُرسل طلب السعر الجديد للمديرة", "ok")
        db.commit()
        flash(f"تم إنشاء خطة من {n} حصص", "ok")
        return redirect(url_for("plan_view", pid=pid))
    sel_client = None
    if request.args.get("client_id"):
        sel_client = db.execute("SELECT id,name,phone FROM clients WHERE id=?", (request.args["client_id"],)).fetchone()
    off = [int(x) for x in (setting("weekly_off") or "4").split(",") if x.strip().isdigit()]
    return render_template("plan_new.html", br=br, depts=branch_depts(br), services=services_for(br),
                           posts=posts_for(br), sel_client=sel_client, weekly_off=off)


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
                    db.execute("UPDATE appointments SET sms_sent_at=NULL, morning_sent_at=NULL WHERE id=?", (x["id"],))
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
        elif act == "advance":
            if not can_collect(u):
                abort(403)
            amount = fnum(f.get("amount"))
            if amount <= 0:
                flash("اكتب مبلغ التسبيق", "err")
            else:
                pay = make_payment(db, p["branch_id"], p["client_id"], amount, f.get("method", "cash"), "service",
                                   f"تسبيق: {p['title']}", u["id"], dept=p["dept"])
                db.execute("UPDATE payments SET plan_id=? WHERE id=?", (pid, pay))
                db.commit()
                flash("تم تسجيل التسبيق", "ok")
                return redirect(url_for("receipt", pid=pay))
        elif act == "pay_credit":
            ids = [int(i) for i in f.getlist("sel") if i.lstrip("-").isdigit()]
            chosen = [x for x in sessions if x["id"] in ids and not x["paid"]]
            need_ = round(sum(x["price"] or 0 for x in chosen), 2)
            if not chosen:
                flash("حدد الحصص", "err")
            elif need_ > st["credit"] + 0.001:
                flash(f"التسبيق المتبقّي ({st['credit']:g}) لا يكفي لهذه الحصص ({need_:g})", "err")
            else:
                for x in chosen:
                    db.execute("UPDATE appointments SET paid=1, credit_used=1 WHERE id=?", (x["id"],))
                    db.execute("UPDATE charges SET status='cancelled' WHERE appointment_id=? AND status='pending'", (x["id"],))
                flash(f"دُفعت {len(chosen)} حصة من التسبيق", "ok")
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
    today = center_today()
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
            pkg_sid = sid
            flash("تم التعديل", "ok")
        else:
            pkg_sid = db.execute("INSERT INTO services(name,kind,dept,price,branch_id,active,duration) VALUES(?,?,?,?,?,?,?)",
                                 vals).lastrowid
            flash("تمت الإضافة", "ok")
        if vals[0]:
            db.execute("UPDATE services SET category=? WHERE id=?", (request.form.get("category", "").strip() or None, pkg_sid))
            db.execute("UPDATE services SET pkg_sessions=?, pkg_interval=?, pkg_total=?, pkg_pay=? WHERE id=?",
                       (max(1, int(fnum(request.form.get("pkg_sessions"), 1))), int(fnum(request.form.get("pkg_interval"), 0)),
                        fnum(request.form.get("pkg_total")),
                        "full" if request.form.get("pkg_pay") == "full" else "session", pkg_sid))
            if request.form.get("mats_form"):
                save_service_mats(db, pkg_sid, request.form.getlist("sm_id"), request.form.getlist("sm_qty"))
            if "aftercare" in request.form:
                db.execute("UPDATE services SET aftercare=? WHERE id=?", (request.form.get("aftercare", "").strip() or None, pkg_sid))
        db.commit()
        return redirect(url_for("services"))
    rows = db.execute("""SELECT s.*, b.name AS branch FROM services s LEFT JOIN branches b ON b.id=s.branch_id
        ORDER BY s.active DESC, s.dept, COALESCE(s.category,'ي'), s.id""").fetchall()
    edit = db.execute("SELECT * FROM services WHERE id=?", (request.args.get("edit"),)).fetchone() \
        if request.args.get("edit") else None
    smats = {}
    for r in db.execute("""SELECT sm.service_id, sm.product_id, sm.qty, p.name, COALESCE(p.cost_price,0) AS unit
            FROM service_materials sm JOIN products p ON p.id=sm.product_id ORDER BY sm.id"""):
        smats.setdefault(r["service_id"], []).append(r)
    return render_template("services.html", rows=rows, edit=edit, smats=smats, mat_products=work_materials(db),
                           scats=[r[0] for r in db.execute("SELECT DISTINCT category FROM services WHERE COALESCE(category,'')<>'' ORDER BY category")])


def work_materials(db, branch_id=None):
    """مواد العمل (للاستعمال) مع الكمية الموجودة في الفرع."""
    return db.execute("""SELECT p.id, p.name, COALESCE(p.cost_price,0) AS unit, COALESCE(s.qty,0) AS qty FROM products p
        LEFT JOIN stock s ON s.product_id=p.id AND s.branch_id=? WHERE p.active=1 AND p.usage IN ('use','both')
        ORDER BY p.usage='both', p.name""", (branch_id,)).fetchall()


def save_service_mats(db, sid, ids, qtys):
    """المواد المعتادة لخدمة: تُملأ تلقائيًا في كل حصة من هذه الخدمة."""
    want = {}
    for p, q in zip(ids, qtys):
        q = fnum(q)
        if p.lstrip("-").isdigit() and q > 0:
            want[int(p)] = want.get(int(p), 0) + q
    old = {r["product_id"]: r for r in db.execute("SELECT * FROM service_materials WHERE service_id=?", (sid,))}
    for p, r in old.items():
        if p not in want:
            db.execute("DELETE FROM service_materials WHERE id=?", (r["id"],))
        elif r["qty"] != want[p]:
            db.execute("UPDATE service_materials SET qty=? WHERE id=?", (want[p], r["id"]))
    for p, q in want.items():
        if p not in old:
            db.execute("INSERT INTO service_materials(service_id,product_id,qty) VALUES(?,?,?)", (sid, p, q))


def visit_default_mats(db, v, items):
    """المواد المعتادة لخدمات هذه الحصة (من صفحة الخدمات)، ناقص اللي تسجّل من قبل."""
    sids = {i["service_id"] for i in items if i["service_id"]}
    if v["appointment_id"]:
        r = db.execute("SELECT service_id FROM appointments WHERE id=?", (v["appointment_id"],)).fetchone()
        if r and r[0]:
            sids.add(r[0])
    if not sids:
        return []
    out = {}
    for r in db.execute(f"""SELECT sm.product_id, sm.qty, p.name FROM service_materials sm JOIN products p ON p.id=sm.product_id
            WHERE p.active=1 AND sm.service_id IN ({",".join("?" * len(sids))}) ORDER BY sm.id""", tuple(sids)):
        if r["product_id"] in out:
            out[r["product_id"]]["qty"] += r["qty"]
        else:
            out[r["product_id"]] = {"id": r["product_id"], "name": r["name"], "qty": r["qty"]}
    done = {r[0] for r in db.execute("SELECT product_id FROM stock_moves WHERE visit_id=? AND kind='use'", (v["id"],))}
    return [m for m in out.values() if m["id"] not in done]


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
@app.route("/settings/summary-test", methods=["POST"])
@login_required("admin")
def summary_test():
    db = get_db()
    msg = daily_summary_text(db, center_today().isoformat())
    if not setting("manager_phone"):
        flash("اكتب هاتف المديرة أولًا ثم احفظ", "err")
        return redirect(url_for("settings") + "#dir")
    ok, resp = send_sms(db, setting("manager_phone"), msg)
    flash(("تم إرسال الملخص: " if ok else "تعذّر الإرسال: " + resp + " — نص الملخص: ") + msg.replace("\n", " | "),
          "ok" if ok else "err")
    return redirect(url_for("settings") + "#dir")


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
            elif k in ("sms_confirm", "sms_birthday", "daily_summary", "approvals_sms", "sms_morning"):
                v = "1" if request.form.get(k) else "0"
            elif k == "last_birthday_run":
                continue
            elif k in ("backup_dir", "backup_dir2", "backup_every_hours"):
                continue  # من صفحة النسخ الاحتياطي
            elif k in ("staff_can_edit_prices", "staff_direct_cancel"):
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
            elif k in ("sms_depts", "sms_hours_before", "sms_morning_hour", "daily_summary_time") and k not in request.form:
                continue  # لم تعد في الصفحة (الإرسال يدوي)
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
    url = s["sms_url"].strip()
    urls = [url]
    # الإصدارات الجديدة من SMS Gateway تستعمل /messages بدل /message
    if url.rstrip("/").endswith("/message"):
        urls.insert(0, url.rstrip("/") + "s")
    # الشكل الجديد (textMessage) ثم القديم (message) إذا البوابة قديمة
    bodies = [{"textMessage": {"text": message}, "phoneNumbers": [norm_phone(phone)]},
              {"message": message, "phoneNumbers": [norm_phone(phone)]}]
    err = ""
    for u in urls:
        for body in bodies:
            # بدون «User-Agent» واضح يرفض Cloudflare الطلب (HTTP 403 error code: 1010)
            req = urlreq.Request(u, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) BilsanClinic/{APP_VERSION}"})
            if s.get("sms_user"):
                tok = base64.b64encode(f"{s['sms_user'].strip()}:{s.get('sms_pass', '').strip()}".encode()).decode()
                req.add_header("Authorization", "Basic " + tok)
            try:
                with urlreq.urlopen(req, timeout=20) as r:
                    return 200 <= r.status < 300, r.read(500).decode("utf-8", "replace")
            except urlerr.HTTPError as e:
                try:
                    detail = e.read(300).decode("utf-8", "replace")
                except Exception:
                    detail = ""
                err = f"HTTP {e.code} {detail}".strip()
                if e.code == 403 and "1010" in detail:
                    return False, "رفضت البوابة الاتصال (403/1010). حدّث البرنامج إلى آخر نسخة، وإن تكرر فجرّب انترنت أخرى"
                if e.code == 401:
                    return False, "اسم المستخدم أو كلمة المرور خاطئة (انسخهما من تطبيق SMS Gateway)"
                if e.code in (404, 405):
                    break  # الرابط غالط: نجربو الرابط الآخر
                if e.code not in (400, 422):
                    return False, err
            except Exception as e:
                return False, str(e)[:300]
    return False, err


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
    now = center_now()
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


def daily_summary_text(db, day):
    lines = [f"{setting('center_name')} - ملخص {day[8:10]}/{day[5:7]}:"]
    grand = 0
    for b in active_branches():
        t = db.execute("""SELECT COALESCE(SUM(amount),0), COUNT(*) FROM payments WHERE branch_id=? AND cancelled=0
            AND substr(created_at,1,10)=?""", (b["id"], day)).fetchone()
        ex = db.execute("""SELECT COALESCE(SUM(amount),0) FROM expenses WHERE branch_id=?
            AND day=?""", (b["id"], day)).fetchone()[0]
        grand += t[0]
        lines.append(f"{b['name'].replace('فرع ', '').replace(' للطب البديل', '')}: {t[0]:,.0f} ({t[1]} عملية)"
                     + (f"، مصاريف {ex:,.0f}" if ex else ""))
    lines.append(f"المجموع: {grand:,.0f} {setting('currency')}")
    for r in db.execute("""SELECT c.role, b.name AS branch, c.counted-c.expected AS diff FROM cash_days c
            JOIN branches b ON b.id=c.branch_id WHERE c.day=? AND c.counted IS NOT NULL AND ABS(c.counted-c.expected)>=1""", (day,)):
        lines.append(f"فرق الصندوق ({PLACES.get(r['role'], r['role'])} {r['branch'].replace('فرع ', '')}): {r['diff']:+,.0f}")
    n = pending_approvals(db)
    if n:
        lines.append(f"طلبات تنتظر موافقتك: {n}")
    st = stock_alerts(None)
    if st:
        lines.append(f"منتجات قاربت على النفاد: {len(st)}")
    return "\n".join(lines)


def daily_summary_check():
    """كل ليلة في الساعة المحددة: ملخص اليوم في هاتف المديرة."""
    if sync.NODE or setting("daily_summary") != "1" or setting("sms_enabled") != "1" or not setting("manager_phone"):
        return
    today = center_today().isoformat()
    if setting("last_daily_summary") == today or center_now().strftime("%H:%M") < (setting("daily_summary_time") or "21:00"):
        return
    db = get_db()
    db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('last_daily_summary',?)", (today,))
    db.commit()
    msg = daily_summary_text(db, today)
    ok, resp = send_sms(db, setting("manager_phone"), msg)
    db.execute("INSERT INTO sms_log(appointment_id,phone,message,status,response,created_at) VALUES(NULL,?,?,?,?,?)",
               (setting("manager_phone"), msg, "sent" if ok else "failed", resp, now_str()))
    db.commit()


def stock_sms_check():
    """مرة في اليوم (بعد الساعة 9 صباحًا) يرسل للمدير رسالة بالمنتجات التي قاربت على النفاد."""
    if setting("stock_sms_enabled") != "1" or not setting("manager_phone"):
        return
    today = center_today().isoformat()
    if setting("last_stock_sms") == today or center_now().hour < 9:
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
        d0 = center_today()
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


AUTO_SMS = False  # كل الرسائل يدوية بطلب المديرة


def sms_extra_jobs(con):
    s = {r["key"]: r["value"] for r in con.execute("SELECT * FROM settings")}
    if s.get("sms_enabled") != "1":
        return
    now = center_now()
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
    # 1-ب) التذكير الثاني: صباح نهار الموعد
    if s.get("sms_morning") == "1" and now.hour >= int(fnum(s.get("sms_morning_hour"), 8)):
        depts = [d for d in (s.get("sms_depts") or "").split(",") if d]
        if depts:
            rows = con.execute(f"""SELECT a.*, c.name AS client, c.phone, b.name AS branch FROM appointments a
                JOIN clients c ON c.id=a.client_id JOIN branches b ON b.id=a.branch_id
                WHERE a.status='scheduled' AND a.morning_sent_at IS NULL AND c.phone<>''
                AND a.dept IN ({','.join('?' * len(depts))}) AND substr(a.start_at,1,10)=? AND a.start_at > ?
                ORDER BY a.start_at LIMIT 20""", depts + [now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M")]).fetchall()
            for a in rows:
                # تذكير وصلها قبل أقل من 3 ساعات (موعد تسجّل اليوم): ما نعاودوش
                if a["sms_sent_at"] and a["sms_sent_at"] >= (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"):
                    con.execute("UPDATE appointments SET morning_sent_at=? WHERE id=?", (now_str(), a["id"]))
                    con.commit()
                    continue
                dt = datetime.strptime(a["start_at"][:16], "%Y-%m-%d %H:%M")
                msg = sms_fill(s.get("sms_morning_template", ""), name=a["client"], center=s.get("center_name"),
                               branch=a["branch"], date=dt.strftime("%d/%m/%Y"), time=dt.strftime("%H:%M"))
                ok, resp = send_sms(con, a["phone"], msg)
                con.execute("INSERT INTO sms_log(appointment_id,phone,message,status,response,created_at) VALUES(?,?,?,?,?,?)",
                            (a["id"], a["phone"], msg, "sent" if ok else "failed", resp, now_str()))
                fails = con.execute("SELECT COUNT(*) FROM sms_log WHERE appointment_id=? AND status='failed' AND created_at>=?",
                                    (a["id"], now.strftime("%Y-%m-%d"))).fetchone()[0]
                if ok or fails >= 3:
                    con.execute("UPDATE appointments SET morning_sent_at=? WHERE id=?", (now_str(), a["id"]))
                con.commit()
    # 2) تهنئة عيد الميلاد مرة في اليوم بعد العاشرة صباحًا
    today = center_today().isoformat()
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


SMS_FILTERS = {"": "كل الزبائن", "tomorrow": "موعدهم غدًا", "today": "موعدهم اليوم",
               "birthday": "عيد ميلادهم اليوم", "missed": "لم يحضروا موعدهم (آخر 30 يومًا)",
               "debt": "عليهم ديون"}


@app.route("/sms/campaign", methods=["GET", "POST"])
@login_required("admin")
def sms_campaign():
    """إرسال يدوي: المديرة تختار النص وتختار الزبائن واحدًا واحدًا."""
    db = get_db()
    f = request.values
    today = center_today()
    q = """SELECT c.id, c.name, c.phone, b.name AS branch, NULL AS start_at, NULL AS aid
        FROM clients c LEFT JOIN branches b ON b.id=c.branch_id WHERE c.phone IS NOT NULL AND c.phone<>''"""
    args = []
    kind = f.get("kind", "")
    if kind in ("tomorrow", "today"):
        d = (today + timedelta(days=1 if kind == "tomorrow" else 0)).isoformat()
        q = """SELECT c.id, c.name, c.phone, b.name AS branch, a.start_at, a.id AS aid FROM appointments a
            JOIN clients c ON c.id=a.client_id JOIN branches b ON b.id=a.branch_id
            WHERE a.status='scheduled' AND substr(a.start_at,1,10)=? AND c.phone<>''"""
        args.append(d)
        if f.get("branch"):
            q += " AND a.branch_id=?"
            args.append(f["branch"])
        if f.get("dept") in DEPTS:
            q += " AND a.dept=?"
            args.append(f["dept"])
    else:
        if kind == "birthday":
            q += " AND substr(c.birth_date,6,5)=?"
            args.append(today.isoformat()[5:])
        elif kind == "missed":
            q += " AND c.id IN (SELECT client_id FROM appointments WHERE (missed=1 OR status='missed') AND substr(start_at,1,10)>=?)"
            args.append((today - timedelta(days=30)).isoformat())
        elif kind == "debt":
            q += " AND c.id IN (SELECT client_id FROM charges WHERE status='debt')"
        if f.get("branch"):
            q += " AND c.branch_id=?"
            args.append(f["branch"])
        if f.get("dept") in DEPTS:
            q += " AND c.id IN (SELECT client_id FROM payments WHERE cancelled=0 AND dept=?)"
            args.append(f["dept"])
    if f.get("gender") in ("ذكر", "أنثى"):
        q += " AND c.gender=?"
        args.append(f["gender"])
    s = (f.get("q") or "").strip()
    if s:
        q += " AND (c.name LIKE ? OR c.phone LIKE ?)"
        args += [f"%{s}%", f"%{s}%"]
    rows = db.execute(q + (" ORDER BY a.start_at" if kind in ("tomorrow", "today") else " ORDER BY c.name") + " LIMIT 1000", args).fetchall()
    msg = (f.get("message") or "").strip()
    center = setting("center_name")

    def fill(r):
        kw = dict(name=r["name"], center=center, branch=r["branch"] or "", date="", time="")
        if r["start_at"]:
            dt = datetime.strptime(r["start_at"][:16], "%Y-%m-%d %H:%M")
            kw.update(date=dt.strftime("%d/%m/%Y"), time=dt.strftime("%H:%M"))
        return sms_fill(msg, **kw)

    if request.method == "POST" and f.get("action") == "send":
        picked = set(request.form.getlist("pick"))
        extra = [p.strip() for p in re.split(r"[,\s،;]+", f.get("extra", "")) if p.strip()]
        chosen = [r for r in rows if f"{r['id']}:{r['aid'] or ''}" in picked]
        if not msg:
            flash("اكتبي نص الرسالة", "err")
        elif not chosen and not extra:
            flash("لم تختاري أي زبون. أشّري على الزبائن في الجدول أو اكتبي أرقامًا", "err")
        elif setting("sms_enabled") != "1":
            flash("بوابة الإرسال غير مفعّلة. فعّليها من الإعدادات أولًا", "err")
        else:
            now = now_str()
            for r in chosen:
                db.execute("INSERT INTO sms_log(appointment_id,client_id,phone,message,status,created_at) VALUES(?,?,?,?,'queued',?)",
                           (r["aid"], r["id"], r["phone"], fill(r), now))
            for p in extra:
                db.execute("INSERT INTO sms_log(phone,message,status,created_at) VALUES(?,?,'queued',?)",
                           (p, sms_fill(msg, name="", center=center, branch="", date="", time=""), now))
            db.commit()
            n = len(chosen) + len(extra)
            audit("إرسال رسائل SMS", f"{n} رسالة: {msg[:80]}")
            flash(f"وُضعت {n} رسالة في قائمة الإرسال، وتخرج من الهاتف تباعًا (حوالي 15 رسالة في الدقيقة). يمكنك إيقافها من صفحة رسائل SMS.", "ok")
            return redirect(url_for("sms_page"))
    tpls = {"reminder": setting("sms_template"), "morning": setting("sms_morning_template"),
            "confirm": setting("sms_confirm_template"), "birthday": setting("sms_birthday_template")}
    return render_template("sms_campaign.html", rows=rows, f=f, msg=msg, kind=kind, tpls=tpls, SMS_FILTERS=SMS_FILTERS,
                           sample=fill(rows[0]) if msg and rows else "")


def sms_send_queue(con):
    """يرسل الرسائل التي اختارتها المديرة بنفسها (لا شيء يُرسل تلقائيًا): 15 رسالة كل دقيقة."""
    if con.execute("SELECT value FROM settings WHERE key='sms_enabled'").fetchone()["value"] != "1":
        return
    for q in con.execute("SELECT * FROM sms_log WHERE status='queued' ORDER BY id LIMIT 15").fetchall():
        if con.execute("SELECT status FROM sms_log WHERE id=?", (q["id"],)).fetchone()["status"] != "queued":
            continue  # أوقفتها المديرة
        ok, resp = send_sms(con, q["phone"], q["message"])
        con.execute("UPDATE sms_log SET status=?, response=?, created_at=? WHERE id=?",
                    ("sent" if ok else "failed", resp, now_str(), q["id"]))
        if ok and q["appointment_id"]:
            con.execute("UPDATE appointments SET sms_sent_at=? WHERE id=?", (now_str(), q["appointment_id"]))
        con.commit()
        time.sleep(2)


def reminder_loop():
    """الإرسال يدوي بالكامل: هذه الحلقة ترسل فقط الرسائل التي وضعتها المديرة في قائمة الإرسال."""
    while True:
        try:
            con = connect()
            sms_send_queue(con)
            con.close()
        except Exception as e:
            print("sms error:", e)
        time.sleep(30)


@app.route("/sms", methods=["GET", "POST"])
@login_required("admin")
def sms_page():
    db = get_db()
    if request.method == "POST":
        act = request.form.get("action")
        if act == "test":
            ok, resp = send_sms(db, request.form.get("phone"), "رسالة تجريبية من " + setting("center_name"))
            flash(("تم الإرسال: " if ok else "فشل الإرسال: ") + resp[:200], "ok" if ok else "err")
        elif act == "stop":
            n = db.execute("UPDATE sms_log SET status='stopped' WHERE status='queued'").rowcount
            db.commit()
            flash(f"أُوقفت {n} رسالة ولن تُرسل", "ok")
        elif act == "retry":
            db.execute("UPDATE sms_log SET status='queued' WHERE id=? AND status IN ('failed','stopped')", (request.form.get("lid"),))
            db.commit()
            flash("أُعيدت الرسالة إلى قائمة الإرسال", "ok")
        return redirect(url_for("sms_page"))
    log = db.execute("""SELECT l.*, COALESCE(c.name, c2.name) AS client FROM sms_log l
        LEFT JOIN clients c ON c.id=l.client_id
        LEFT JOIN appointments a ON a.id=l.appointment_id LEFT JOIN clients c2 ON c2.id=a.client_id
        ORDER BY l.id DESC LIMIT 200""").fetchall()
    queued = db.execute("SELECT COUNT(*) n FROM sms_log WHERE status='queued'").fetchone()["n"]
    return render_template("sms.html", log=log, enabled=setting("sms_enabled") == "1", queued=queued)


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
    exp = (center_now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute("INSERT INTO pair_codes(code,user_id,expires) VALUES(?,?,?)", (code, uid, exp))
    return code


def phone_urls():
    """عناوين الحاسوب المركزي في الشبكة المحلية (لتطبيق هاتف المديرة)."""
    import socket
    port = (request.host.rsplit(":", 1)[1] if ":" in request.host else "80")
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    ips = sorted(i for i in ips if not i.startswith("127.") and not i.startswith("169.254."))
    return [f"http://{i}:{port}" for i in ips]


@app.route("/app/ping")
def app_ping():
    """يتعرّف به تطبيق الهاتف على الحاسوب المركزي في الشبكة."""
    r = Response(json.dumps({"bilsan": 1, "central": not sync.NODE, "name": setting("center_name"), "version": APP_VERSION},
                            ensure_ascii=False), mimetype="application/json")
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r


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
    return render_template("devices.html", phone_urls=phone_urls(), rows=device_rows(db), codes=codes,
                           branches=db.execute("SELECT * FROM branches WHERE active=1 ORDER BY id").fetchall(),
                           now=center_now(), version=APP_VERSION)


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
        if data.get("version"):
            db.execute("UPDATE users SET last_seen=?, app_version=? WHERE id=?",
                       (now_str(), str(data["version"])[:20], d["id"]))
        else:
            db.execute("UPDATE users SET last_seen=? WHERE id=?", (now_str(), d["id"]))
        db.commit()
    return data, int(b)


@app.route("/sync/wait", methods=["POST"])
def sync_wait():
    """الحاسوب الفرعي ينتظر هنا حتى تتسجل معلومة جديدة (حتى 25 ثانية)."""
    data, _ = sync_auth()
    old = data.get("s", -1)
    if old == -1 or old != sync.STAMP[0]:
        return {"s": sync.STAMP[0]}
    r = sync.wait_change(old, 25, "n:" + str(data.get("device") or data.get("branch_id") or request.remote_addr))
    return {"s": sync.STAMP[0] if r in (None, "x") else r}


@app.route("/sync/hello", methods=["POST"])
def sync_hello():
    sync_auth()
    return {"ok": True, "version": APP_VERSION, "update": bool(update_zip()), "epoch": time.time(), "tz": sync.TZ_HOURS[0]}


def update_zip():
    """ملف التحديث الذي يأتي مع ملف تثبيت الحاسوب المركزي."""
    p = os.path.join(BASE_DIR, "update", f"Bilsan-update-{APP_VERSION}.zip")
    return p if os.path.exists(p) else None


@app.route("/sync/update", methods=["POST"])
def sync_update_file():
    sync_auth()
    p = update_zip()
    if not p:
        abort(404)
    return send_file(p, mimetype="application/zip", as_attachment=True, download_name=os.path.basename(p))


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


@app.route("/node/central", methods=["POST"])
def node_central():
    """من صفحة الدخول في حاسوب الفرع: كتابة عنوان الحاسوب المركزي باليد أو البحث عنه تلقائيًا."""
    if not sync.NODE:
        abort(404)
    port = urlsplit(sync.NODE["central_url"]).port or 80
    ip = (request.form.get("ip") or "").strip().replace("http://", "").split("/")[0]
    if ip:
        if ":" in ip:
            ip, port = ip.split(":", 1)[0], int(ip.split(":", 1)[1] or port)
        if not sync._ping(ip, port, 3):
            flash(f"لم يُعثر على البرنامج في {ip}. تأكدي أن البرنامج مفتوح في حاسوب المديرة وأن العنوان صحيح.", "err")
            return redirect(url_for("login"))
        sync.save_central_ip(ip)
    else:
        ip = sync.discover_central(port, force=True)
        if not ip:
            flash("لم يُعثر على الحاسوب المركزي في الشبكة. تأكدي أنه شغال والبرنامج مفتوح فيه، وأن الحاسوبين على نفس الراوتر، أو اكتبي عنوانه.", "err")
            return redirect(url_for("login"))
    sync._net["conn"] = None
    ok, msg = sync.sync_now(connect)
    flash((f"تم الربط بالحاسوب المركزي ({ip}). ادخلي الآن بكلمة سر الحاسوب." if ok
           else f"وُجد الحاسوب المركزي ({ip}) لكن المزامنة فشلت: {msg}"), "ok" if ok else "err")
    return redirect(url_for("login"))


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


sync.APP_VERSION = APP_VERSION
import icons  # noqa: E402

# صفحة → رمزها (يظهر في عنوان كل صفحة)
PAGE_ICONS = {
    "dashboard": "home", "branch_view": "branch", "visit_queue": "queue", "visit_view": "visits",
    "visit_new": "reception", "visits_list": "visits", "reception": "cash", "receipt": "invoice",
    "charge_new": "send", "pos": "cart", "appointments": "calendar", "calendar": "rooms",
    "plans": "plans", "plan_new": "plans", "plan_view": "plans", "clients": "clients",
    "client_view": "clients", "consent": "sign", "payment_new": "card", "debts": "debt",
    "cash_close": "lock", "cash_daily": "safe", "cashbox": "vault", "reports": "reports",
    "expenses": "expense", "permissions": "key", "audit_page": "audit", "backup_page": "backup",
    "products": "products", "stock_alerts_page": "alert", "purchases": "invoice", "purchase_new": "invoice",
    "suppliers": "truck", "services": "services", "branches": "branch", "branch_edit": "branch",
    "devices": "monitor", "users": "users", "sms_page": "sms", "sms_campaign": "sms",
    "settings": "settings", "change_password": "key", "staff": "staff", "staff_view": "staff",
    "attendance": "staff", "courses": "course", "course_view": "course", "stock_use": "cream", "approvals": "key", "sessions_profit": "reports", "stock_use": "cream",
    "services_profit": "services", "month_report": "reports", "purchase_auto": "truck",
    "appt_reschedule": "calendar", "appts_missed": "calendar",
    "operations": "audit", "cancelled_ops": "audit", "stock_manage": "products", "stock_opening": "products", "day_report": "reports", "payment_fix": "cash", "appt_edit": "calendar", "trainee_file": "course",
}


def page_icon():
    ep = request.endpoint or ""
    name = PAGE_ICONS.get(ep) or next((v for k, v in PAGE_ICONS.items() if ep.startswith(k)), "leaf")
    return icons.ic(name, "pg")


app.jinja_env.globals.update(now_hm=lambda: center_now().strftime("%Y-%m-%d %H:%M"), live_page=lambda: bool(request.endpoint) and request.endpoint not in NOT_LIVE
                             and not request.endpoint.endswith(("_print", "_csv")) and request.method == "GET", ic=icons.ic, item_ic=icons.item, avatar=icons.avatar,
                             icon_sprite=icons.sprite, page_icon=page_icon)
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
    if sync.NODE:  # آخر فرق ساعة معروف مع المركزي (حتى إذا الحاسوب يبدا بلا انترنت)
        try:
            _c = connect()
            sync.CLOCK_SKEW[0] = float(sync.state_get(_c, "clock_skew", "0") or 0)
            _c.close()
        except Exception:
            pass


# ---------------------------------------------------------------- التحديث التلقائي للحواسيب
# الحاسوب المركزي يُحدَّث يدويًا (ملف التثبيت). كل حاسوب آخر يرى أن المركزي بنسخة أحدث
# فيحمّل منه ملف التحديث ويثبّته وحده: عند تشغيل الحاسوب، أو بعد 5 دقائق دون استعمال.
START_TIME = time.time()
LAST_REQ = [time.time()]


def current_lang():
    try:
        u = current_user()
    except Exception:  # noqa: BLE001
        u = None
    lang = (u["lang"] if u and "lang" in u.keys() and u["lang"] else None) or session.get("lang") or "ar"
    return lang if lang in i18n.LANGS else "ar"


@app.route("/lang/<code>")
def set_lang(code):
    """كل عامل يختار لغتو: تتحفظ في حسابو (تتبعو في أي حاسوب)."""
    if code in i18n.LANGS:
        session["lang"] = code
        u = current_user()
        if not u:
            session["lang_pick"] = 1
        if u:
            db = get_db()
            db.execute("UPDATE users SET lang=? WHERE id=?", (code, u["id"]))
            db.commit()
    ref = request.referrer or ""
    return redirect(ref if ref.startswith(request.host_url) else url_for("dashboard"))


@app.after_request
def _translate(resp):
    """الصفحة تتترجم للفرنسية ولا الإنجليزية حسب لغة العامل."""
    try:
        if (resp.status_code == 200 or 300 <= resp.status_code < 600) and resp.mimetype == "text/html" \
                and not resp.direct_passthrough and not resp.is_streamed:
            lang = current_lang()
            if lang != "ar":
                resp.set_data(i18n.translate_html(resp.get_data(as_text=True), lang))
    except Exception:  # noqa: BLE001
        pass
    return resp


@app.after_request
def _after_write(resp):
    """بعد أي عملية حفظ: الصفحات المفتوحة تتحدث، والحاسوب الفرعي يرسل فورًا."""
    if request.method == "POST" and resp.status_code < 400 and not request.path.startswith("/sync/"):
        sync.bump()
        if sync.NODE:
            sync.WAKE.set()
    return resp


# كل الصفحات تتحدث وحدها عند وصول معلومة جديدة، إلا الصفحات التي فيها عمل غير محفوظ أو للطباعة
NOT_LIVE = {"login", "pos", "purchase_new", "plan_new", "payment_new", "charge_new", "visit_new", "consent",
            "receipt", "certificate", "payslip", "payslips_all", "settings", "settings_images",
            "sms_campaign", "backup_page", "update_now", "setup_pair", "devices", "permissions", "purchase_auto", "appt_reschedule", "operations", "stock_manage",
            "services", "month_report", "stock_opening", "trainee_file"}


@app.route("/api/stamp")
def api_stamp():
    """s: أي معلومة جديدة (تتحدث الصفحات الحية). p: تغيّرت المهام/الصلاحيات (تتحدث كل الصفحات).
    مع wait=1: ينتظر حتى 20 ثانية إلى أن يتغيّر شيء (أخف وأسرع من السؤال كل ثانيتين)."""
    if request.args.get("wait") and request.args.get("s", "").lstrip("-").isdigit():
        old = int(request.args["s"])
        if old == sync.STAMP[0]:
            key = "b:" + (request.args.get("t") or "")[:24] if request.args.get("t") else None
            r = sync.wait_change(old, 20, key)
            if r is None:
                return {"s": sync.STAMP[0], "p": "", "busy": 1}
            if r == "x":
                return {"s": sync.STAMP[0], "p": "", "x": 1}
    p = ""
    if current_user():
        try:
            r = get_db().execute("SELECT COALESCE(MAX(_upd),'') || ':' || COUNT(*) || ':' || COALESCE(SUM(enabled),0) FROM perms").fetchone()
        except sqlite3.OperationalError:
            r = get_db().execute("SELECT COUNT(*) || ':' || COALESCE(SUM(enabled),0) FROM perms").fetchone()
        u = current_user()
        p = f"{r[0]}:{u['active']}"
    return {"s": sync.STAMP[0], "p": p, "d": center_today().isoformat()}


@app.before_request
def _mark_activity():
    if request.endpoint not in ("static", None, "api_stamp"):
        LAST_REQ[0] = time.time()


UPDATE_BAT = r"""@echo off
cd /d "{data}"
ping -n 4 127.0.0.1 >nul
taskkill /f /im Bilsan.exe >nul 2>&1
ping -n 3 127.0.0.1 >nul
set "A={app}"
if exist "%A%_old" rmdir /s /q "%A%_old"
move "%A%" "%A%_old" >nul || goto fail
move "{new}" "%A%" >nul || (move "%A%_old" "%A%" >nul & goto fail)
echo ok> "{data}\update_result.txt"
start "" /D "{data}" "%A%\Bilsan.exe" --background
exit /b 0
:fail
echo fail> "{data}\update_result.txt"
start "" /D "{data}" "%A%\Bilsan.exe" --background
"""


def apply_update():
    """يحمّل ملف التحديث من الحاسوب المركزي ويستبدل البرنامج ثم يعيد تشغيله."""
    import zipfile
    import shutil
    import subprocess
    con = connect()
    try:
        cv = sync.state_get(con, "central_version", "")
        tried = sync.state_get(con, "update_tried", "")
        if tried.startswith(cv + "|") and time.time() - float(tried.split("|")[1]) < 6 * 3600:
            return False  # جربنا هذه النسخة منذ قليل ولم تنجح: لا نعيد كل دقيقة
        sync.state_set(con, "update_tried", f"{cv}|{time.time()}")
        con.commit()
    finally:
        con.close()
    zpath = os.path.join(BASE_DIR, "update_download.zip")
    newdir = os.path.join(BASE_DIR, "app_new")
    req = urlreq.Request(sync.NODE["central_url"] + "/sync/update", method="POST",
                         data=json.dumps({"branch_id": sync.NODE["branch_id"], "device": sync.NODE.get("device")}).encode(),
                         headers={"Content-Type": "application/json", "X-Sync-Key": sync.NODE.get("key", "")})
    with urlreq.urlopen(req, timeout=600) as r, open(zpath, "wb") as f:
        shutil.copyfileobj(r, f)
    shutil.rmtree(newdir, ignore_errors=True)
    with zipfile.ZipFile(zpath) as z:
        if z.testzip() is not None:
            raise RuntimeError("ملف التحديث تالف")
        z.extractall(newdir)
    os.remove(zpath)
    if not os.path.exists(os.path.join(newdir, "Bilsan.exe")):
        raise RuntimeError("ملف التحديث ناقص")
    if not getattr(sys, "frozen", False):  # تشغيل من الكود (اختبار): لا نستبدل شيئًا
        open(os.path.join(BASE_DIR, "update_ready.txt"), "w").write(cv)
        return True
    appdir = os.path.dirname(os.path.abspath(sys.executable))
    bat = os.path.join(BASE_DIR, "update.bat")
    with open(bat, "w", encoding="ascii", errors="replace") as f:
        f.write(UPDATE_BAT.replace("{app}", appdir).replace("{new}", newdir).replace("{data}", BASE_DIR)
                .replace("\n", "\r\n"))
    print(f"تحديث البرنامج إلى {cv}")
    flags = 0x08000000 | 0x00000008 if os.name == "nt" else 0  # بدون نافذة، منفصل
    # مهم: نشغّله من مجلد البيانات، وإلا يبقى مجلد البرنامج «مستعملًا» فلا يمكن استبداله
    subprocess.Popen(["cmd", "/c", bat] if os.name == "nt" else ["sh", bat], creationflags=flags, close_fds=True,
                     cwd=BASE_DIR)
    time.sleep(0.5)
    os._exit(0)


@app.route("/update-now")
@login_required()
def update_now():
    """زر «حدّث الآن» في الحاسوب الفرعي."""
    if not sync.NODE:
        abort(404)
    con = connect()
    try:
        sync.state_set(con, "update_tried", "")
        con.commit()
    finally:
        con.close()

    def go():
        time.sleep(1)
        try:
            apply_update()
        except Exception as e:  # noqa: BLE001
            print("update error:", e)
    threading.Thread(target=go, daemon=True).start()
    return ("<!doctype html><meta charset=utf-8><meta http-equiv=refresh content='45;url=/'>"
            "<body style='font-family:Tahoma;background:#0f4c45;color:#f3d6a8;display:flex;align-items:center;"
            "justify-content:center;height:100vh;margin:0;text-align:center'><div><h2>جاري تحديث البرنامج...</h2>"
            "<p>انتظر دقيقة، ستعود الصفحة تلقائيًا.</p></div>")


def update_loop():
    while True:
        time.sleep(float(os.environ.get("BILSAN_UPDATE_EVERY", "60")))
        try:
            con = connect()
            try:
                newer = sync.central_is_newer(con)
            finally:
                con.close()
            idle = time.time() - LAST_REQ[0]
            if newer and (time.time() - START_TIME < 600 or idle > 300) and \
                    not os.path.exists(os.path.join(BASE_DIR, "update_ready.txt")):
                apply_update()
        except Exception as e:  # noqa: BLE001
            print("update error:", e)


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
            if getattr(sys, "frozen", False) or os.environ.get("BILSAN_UPDATE_TEST"):
                threading.Thread(target=update_loop, daemon=True).start()
        else:
            threading.Thread(target=reminder_loop, daemon=True).start()
    # الحاسوب المركزي يستقبل الحواسيب الأخرى، أما الحاسوب الفرعي فلا يفتح إلا لنفسه
    host = "127.0.0.1" if (sync.NODE or PAIR_MODE) else "0.0.0.0"
    print(f"\n  {DEFAULT_SETTINGS['center_name']}\n  البرنامج يعمل على: http://localhost:{port}\n")
    try:
        from waitress import serve
        serve(app, host=host, port=port, threads=48, channel_timeout=60)
    except ImportError:
        app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    run_server()
