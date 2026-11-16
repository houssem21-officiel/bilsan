# -*- coding: utf-8 -*-
"""قائمة خدمات ومنتجات مركز بيلسان وأسعارها (دج). تُضاف تلقائيًا عند أول تشغيل،
ثم تعدّلها المديرة من البرنامج (الخدمات والأسعار / المنتجات والمخزون)."""

# (الاسم، النوع، القسم، السعر، الفرع: None = الفرعان، 1 = سكيكدة فقط)
SERVICES = [
    # القسم العلاجي
    ("حجامة بأنواعها", "hijama", "reception", 1000, None),
    ("سم النحل", "other", "reception", 500, None),
    ("إبر صينية", "other", "reception", 1000, None),
    ("حجامة نارية + إبر صينية", "hijama", "reception", 1500, None),
    ("البلازما (علاجي)", "other", "reception", 5000, None),
    ("إبر ASP لغلق الشهية", "other", "reception", 1000, None),
    ("إبر ASP لفتح الشهية", "other", "reception", 500, None),
    # قسم التجميل
    ("تنظيف البشرة العميق بالهيدرافاسيال", "beauty", "beauty", 4500, None),
    ("التنظيف الكلاسيكي", "beauty", "beauty", 2000, None),
    ("التقشير الذكي للوجه", "beauty", "beauty", 8000, None),
    ("إبر النضارة", "beauty", "beauty", 9000, None),
    ("البلازما للبشرة", "beauty", "beauty", 5000, None),
    ("الميزوثيرابي", "beauty", "beauty", 3500, None),
    ("الأوكسيجينو", "beauty", "beauty", 5900, None),
    ("البلازما لتساقط الشعر", "beauty", "beauty", 5000, None),
    ("الفيلر (الحقنة)", "beauty", "beauty", 20000, None),
    ("التخسيس الموضعي", "beauty", "beauty", 5000, None),
    ("التقشير الكربوني + إزالة الرؤوس السوداء", "beauty", "beauty", 3000, None),
    ("تبييض الإبطين", "beauty", "beauty", 5000, None),
    ("تبييض المنطقة الحساسة", "beauty", "beauty", 7000, None),
    # سعرها حسب المنطقة: تحدد المديرة المناطق وأسعارها
    ("إزالة الشعر بالليزر (حسب المنطقة)", "laser", "laser", 0, 1),
    ("إزالة الشعر الأبيض بالتحليل الكهربائي - إليكتروليز (حسب المساحة)", "beauty", "beauty", 0, None),
]

F1, F2 = "تركيبات بيلسان", "منتجات النحل والطبيعة"
PRODUCTS = [
    ("زيت بيلسان لتطويل وتكثيف الشعر", F1, 1000),
    ("بخاخ بيلسان لتكثيف الشعر", F1, 1000),
    ("زيت الأوزون", F1, 1000),
    ("تركيبة الإنجاب والضعف الجنسي", F1, 4000),
    ("الماكا", F1, 2000),
    ("تركيبة المناعة", F1, 1500),
    ("تركيبة الغدة الدرقية", F1, 1500),
    ("تركيبة سلس البول والتبول اللاإرادي", F1, 1500),
    ("ماء القدّيسين", F1, 700),
    ("مُسمنة بيلسان", F1, 1300),
    ("مسمنة بيلسان العجيبة", F1, 1300),
    ("مُنحفة بيلسان", F1, 500),
    ("تركيبة القولون والقولون العصبي", F1, 500),
    ("تركيبة الهلع", F1, 500),
    ("تركيبة البواسير + دهن البواسير", F1, 800),
    ("كريم سم النحل للأمراض الجلدية", F1, 1500),
    ("كريم سم النحل لآلام المفاصل", F1, 1500),
    ("تركيبة الفيبروم", F1, 500),
    ("تركيبة تكيس المبايض والخلل الهرموني", F1, 500),
    ("تركيبة السكري", F1, 500),
    ("تركيبة الذاكرة والتركيز", F1, 500),
    ("تركيبة الكوليسترول", F1, 500),
    ("تركيبة جرثومة المعدة", F1, 500),
    ("تركيبة الحصى والمسالك البولية", F1, 500),
    ("العكبر", F2, 600),
    ("حبوب اللقاح (حبوب الطلع)", F2, 500),
    ("طلع النخيل", F2, 400),
    ("الجنسنغ الأحمر", F2, 500),
    ("عسل السدر", F2, 1500),
    ("عسل الأزهار", F2, 1000),
    ("عسل الجرجير", F2, 1250),
    ("العسل المر", F2, 1500),
    ("الدارما رولر", F2, 1300),
]

PLACEHOLDER_SERVICES = ("حجامة", "جلسة ليزر", "خدمة تجميل", "دورة تكوينية")


def apply_catalog(con):
    """يضيف الخدمات والمنتجات غير الموجودة (بالاسم). لا يغيّر الأسعار التي عدّلتها المديرة."""
    for name, kind, dept, price, br in SERVICES:
        if not con.execute("SELECT 1 FROM services WHERE name=?", (name,)).fetchone():
            con.execute("INSERT INTO services(name,kind,dept,price,branch_id) VALUES(?,?,?,?,?)",
                        (name, kind, dept, price, br))
    # الخدمات المؤقتة الأولى بسعر 0 تُوقف (لا تُحذف)
    for name in PLACEHOLDER_SERVICES:
        con.execute("UPDATE services SET active=0 WHERE name=? AND price=0", (name,))
    for name, cat, price in PRODUCTS:
        if not con.execute("SELECT 1 FROM products WHERE name=?", (name,)).fetchone():
            con.execute("INSERT INTO products(name,category,price) VALUES(?,?,?)", (name, cat, price))


def restore_catalog(con):
    """يعيد إدخال كل الخدمات والمنتجات الأصلية بنفس ترتيب القائمة: يضيف الناقص بسعره الأصلي،
    ويعيد تفعيل الموقوف منها. لا يغيّر الأسعار التي عدّلتها المديرة ولا يكرّر الموجود.
    يرجع (عدد الخدمات المضافة، عدد المنتجات المضافة، عدد ما أعيد تفعيله)."""
    added_s = added_p = react = 0
    for name, kind, dept, price, br in SERVICES:
        row = con.execute("SELECT id, active FROM services WHERE name=?", (name,)).fetchone()
        if not row:
            con.execute("INSERT INTO services(name,kind,dept,price,branch_id) VALUES(?,?,?,?,?)",
                        (name, kind, dept, price, br))
            added_s += 1
        elif not row[1]:
            con.execute("UPDATE services SET active=1 WHERE id=?", (row[0],))
            react += 1
    for name, cat, price in PRODUCTS:
        row = con.execute("SELECT id, active FROM products WHERE name=?", (name,)).fetchone()
        if not row:
            con.execute("INSERT INTO products(name,category,price) VALUES(?,?,?)", (name, cat, price))
            added_p += 1
        elif not row[1]:
            con.execute("UPDATE products SET active=1 WHERE id=?", (row[0],))
            react += 1
    return added_s, added_p, react
