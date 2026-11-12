# -*- coding: utf-8 -*-
# قوالب الواجهة (عربية، من اليمين لليسار، خلفية خضراء)
TEMPLATES = {}

TEMPLATES["base.html"] = r"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ center }}</title>
<style>
:root{--g9:#173f36;--g8:#1f4d43;--g7:#2a6153;--g5:#3f7c6c;--g2:#d9c7ad;--g1:#f3eadc;
--gold:#e4ab74;--goldl:#f0c9a0;--cream:#fbf7f0;--txt:#1f2a26;--mut:#6b6f66;--red:#b3261e;--amber:#9a6200;--line:#e2d3bd}
*{box-sizing:border-box}
html{min-height:100%;background:#12322b}
body{margin:0;font-family:Tahoma,"Segoe UI",Arial,sans-serif;color:var(--txt);font-size:15px;min-height:100vh;display:flow-root;
background:url({{ url_for('static', filename='pattern.png') }}) repeat,
radial-gradient(ellipse at 50% 45%,#33655a 0%,#28554b 40%,#1b4038 75%,#12322b 100%) fixed}
header{background:rgba(12,38,32,.82);color:var(--gold);padding:8px 18px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;border-bottom:1px solid rgba(228,171,116,.45)}
header .logo{font-size:20px;font-weight:bold;display:flex;align-items:center;gap:10px;color:var(--gold)}
header .logo img{height:52px}
header .who{margin-inline-start:auto;font-size:13px;color:var(--goldl)}
header .who a{color:var(--goldl)}
nav{background:rgba(12,38,32,.55);display:flex;flex-wrap:wrap;padding:0 10px;border-bottom:1px solid rgba(228,171,116,.25)}
nav a{color:var(--goldl);text-decoration:none;padding:10px 13px;font-size:14px}
nav a:hover{background:rgba(228,171,116,.15);color:#fff}
nav a.on{background:var(--gold);color:var(--g9)}
main{max-width:1200px;margin:18px auto;padding:0 14px}
main>h1{color:var(--gold)}
.card{background:var(--cream);border:1px solid rgba(228,171,116,.55);border-radius:12px;padding:16px;margin-bottom:16px}
h1{font-size:21px;color:var(--g9);margin:0 0 14px}
h2{font-size:17px;color:var(--g8);margin:0 0 12px}
a{color:var(--g7)}
table{width:100%;border-collapse:collapse;font-size:14px}
th{background:#efe2cf;color:var(--g9);text-align:right;padding:8px;border-bottom:1px solid var(--line)}
td{padding:7px 8px;border-bottom:1px solid #ece2d3;vertical-align:middle}
tr.cx td{color:#999;text-decoration:line-through}
input,select,textarea{font:inherit;padding:7px 9px;border:1px solid var(--line);border-radius:8px;background:#fff;min-width:0}
textarea{width:100%}
input:focus,select:focus,textarea:focus{outline:2px solid var(--gold);border-color:var(--gold)}
.btn{display:inline-block;background:var(--g7);color:#fff;border:0;border-radius:8px;padding:8px 14px;
cursor:pointer;text-decoration:none;font:inherit;font-size:14px}
.btn:hover{background:var(--g9)}
.btn.sm{padding:4px 9px;font-size:13px}
.btn.light{background:var(--g1);color:var(--g9);border:1px solid var(--line)}
.btn.gold{background:var(--gold);color:var(--g9)}
.btn.red{background:var(--red)}
main>.row .btn{background:var(--gold);color:var(--g9)}
main>.row .btn.light{background:rgba(251,247,240,.9)}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}
.row label{display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--mut)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.stat{background:var(--cream);border:1px solid rgba(228,171,116,.55);border-top:4px solid var(--gold);border-radius:12px;padding:14px}
.stat .n{font-size:24px;font-weight:bold;color:var(--g8)}
.stat .l{color:var(--mut);font-size:13px}
.flash{padding:10px 14px;border-radius:8px;margin-bottom:12px}
.flash.ok{background:#e6f2ea;color:var(--g9);border:1px solid #b9d8c3}
.flash.err{background:#fdecea;color:var(--red);border:1px solid #f3c1bc}
.flash a{color:inherit}
.tag{display:inline-block;padding:2px 9px;border-radius:20px;font-size:12px;background:#e3efe8;color:var(--g9)}
.tag.amber{background:#fbeedd;color:var(--amber)}.tag.red{background:#fdecea;color:var(--red)}
.tag.gray{background:#eee;color:#555}
.mut{color:var(--mut);font-size:13px}
.right{text-align:left}
.picker{position:relative}.picker .list{position:absolute;z-index:5;background:#fff;border:1px solid var(--line);
border-radius:8px;width:100%;max-height:240px;overflow:auto;display:none}
.picker .list div{padding:7px 10px;cursor:pointer}.picker .list div:hover{background:var(--g1)}
.brandlogo{display:block;margin:0 auto}
.dd{position:relative}.dd summary{list-style:none;cursor:pointer;color:var(--goldl);padding:10px 13px;font-size:14px}
.dd summary::-webkit-details-marker{display:none}.dd[open] summary{background:rgba(228,171,116,.15)}
.ddm{position:absolute;z-index:20;background:#173f36;border:1px solid rgba(228,171,116,.5);border-radius:8px;min-width:220px;padding:6px 0;box-shadow:0 8px 20px rgba(0,0,0,.3)}
.ddm a{display:block;padding:8px 14px}
.ic{width:1.15em;height:1.15em;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;vertical-align:-.22em;flex:none}
nav a .ic,.dd summary .ic,.ddm a .ic{color:var(--gold);margin-inline-end:6px}
nav a.on .ic{color:inherit}
.ddm a{display:flex!important;align-items:center;direction:rtl;justify-content:flex-start}
h1 .ic.pg{box-sizing:border-box;width:1.7em;height:1.7em;padding:.3em;margin-inline-end:.45em;border-radius:14px;vertical-align:middle;
 color:#0f4c45;background:linear-gradient(135deg,#f7e2bd,#e4ab74);box-shadow:0 3px 10px rgba(228,171,116,.45),inset 0 1px 0 rgba(255,255,255,.6);stroke-width:1.9}
h2 .ic{color:var(--gold);margin-inline-end:6px}
.itm{display:inline-flex;width:30px;height:30px;border-radius:9px;align-items:center;justify-content:center;margin-inline-end:8px;vertical-align:middle;
 color:#0f4c45;background:linear-gradient(135deg,#eef6f3,#cfe6df);box-shadow:inset 0 0 0 1px rgba(15,76,69,.12)}
.itm .ic{box-sizing:content-box;width:18px;height:18px;vertical-align:0}
.av{display:inline-flex;width:32px;height:32px;border-radius:50%;align-items:center;justify-content:center;margin-inline-end:8px;vertical-align:middle;
 font-weight:bold;font-size:15px;background:hsl(var(--h) 45% 88%);color:hsl(var(--h) 55% 26%);box-shadow:inset 0 0 0 2px hsl(var(--h) 45% 78%)}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin-bottom:16px}
.tile{display:flex;flex-direction:column;align-items:center;gap:8px;padding:16px 8px;border-radius:14px;text-decoration:none;
 background:var(--card,#fbf6ec);color:#0f4c45;font-weight:bold;box-shadow:0 4px 14px rgba(0,0,0,.12);transition:transform .15s,box-shadow .15s}
.tile:hover{transform:translateY(-3px);box-shadow:0 8px 22px rgba(0,0,0,.2)}
.tile .ic{box-sizing:border-box;width:56px;height:56px;padding:13px;border-radius:50%;color:#0f4c45;background:linear-gradient(135deg,#f7e2bd,#e4ab74);stroke-width:1.6}
.badge{display:inline-block;min-width:20px;padding:0 6px;border-radius:10px;background:#c0392b;color:#fff;font-size:12px;text-align:center}
.viewing{background:var(--gold);color:var(--g9);padding:6px 14px;border-radius:8px;margin-bottom:12px;display:flex;gap:10px;align-items:center}
@media print{header,nav,.noprint{display:none!important}body,html{background:#fff!important}.card{border:0}}
</style></head><body>
{{ icon_sprite() }}
{% if cu %}
<header><div class="logo"><img src="{{ url_for('static', filename='logo.png') }}" alt="">{{ center }}</div>
{% if cu.role=='admin' %}<form action="{{ url_for('view_branch') }}" style="margin:0"><select name="b" onchange="this.form.submit()" style="background:rgba(255,255,255,.08);color:var(--goldl);border-color:rgba(228,171,116,.5)">
<option value="" style="color:#000">الحاسوب المركزي — كل الفروع</option>{% for b in all_branches %}<option value="{{ b.id }}" style="color:#000" {{ 'selected' if view_branch==b.id }}>عرض: {{ b.name }}</option>{% endfor %}</select></form>{% endif %}
<div class="who">{{ cu.full_name or cu.username }} — {{ ROLES[cu.role] }}{% if cu.branch_id %} — {{ branch_name(cu.branch_id) }}{% endif %}
 | <a href="{{ url_for('change_password') }}">{{ ic('key') }} كلمة المرور</a> | <a href="{{ url_for('logout') }}">{{ ic('logout') }} خروج</a></div></header>
<nav>
{% set ep = request.endpoint %}
<a href="{{ url_for('dashboard') }}" class="{{ 'on' if ep in ('dashboard','branch_view') }}">{{ ic('home') }}الرئيسية</a>
{% if cu.role in ('admin','laser','beauty') %}<a href="{{ url_for('visit_queue') }}" class="{{ 'on' if ep in ('visit_queue','visit_view') }}">{{ ic('queue') }}{{ 'زبائن المديرة' if cu.role=='admin' else 'قائمة الانتظار' }}{% if queue_count %} <span class="badge">{{ queue_count }}</span>{% endif %}</a>{% endif %}
{% if perm('reception_visits') %}<a href="{{ url_for('visit_new') }}" class="{{ 'on' if ep in ('visit_new','visits_list') }}">{{ ic('reception') }}استقبال زبون</a>{% endif %}
{% if perm('collect') %}<a href="{{ url_for('reception') }}" class="{{ 'on' if ep in ('reception','receipt') }}">{{ ic('cash') }}{{ 'الاستقبال والتحصيل' if cu.role in ('admin','reception') else 'التحصيل' }}</a>
{% elif cu.role in ('laser','beauty') %}<a href="{{ url_for('charge_new') }}" class="{{ 'on' if ep=='charge_new' }}">{{ ic('send') }}إرسال مبلغ للاستقبال</a>{% endif %}
{% if perm('pos') %}<a href="{{ url_for('pos') }}" class="{{ 'on' if ep=='pos' }}">{{ ic('cart') }}بيع المنتجات</a>{% endif %}
<a href="{{ url_for('appointments') }}" class="{{ 'on' if ep in ('appointments','calendar') }}">{{ ic('calendar') }}المواعيد</a>
<a href="{{ url_for('plans') }}" class="{{ 'on' if ep in ('plans','plan_new','plan_view') }}">{{ ic('plans') }}خطط الحصص</a>
<a href="{{ url_for('clients') }}" class="{{ 'on' if ep in ('clients','client_view','consent') }}">{{ ic('clients') }}الزبائن</a>
<details class="dd"><summary>{{ ic('more') }}المزيد ▾{% if alerts_count and perm('stock_alerts') %} <span class="badge">{{ alerts_count }}</span>{% endif %}</summary><div class="ddm">
{% if perm('calendar') %}<a href="{{ url_for('calendar') }}">{{ ic('rooms') }}جدول الغرف</a>{% endif %}
{% if perm('reception_visits') %}<a href="{{ url_for('visits_list') }}">{{ ic('visits') }}الزيارات</a>{% endif %}
{% if perm('direct_payment') %}<a href="{{ url_for('payment_new') }}">{{ ic('card') }}دفعة مباشرة</a>{% endif %}
{% if perm('debts') %}<a href="{{ url_for('debts') }}">{{ ic('debt') }}الديون</a>{% endif %}
{% if perm('cash_close') and cu.role!='admin' %}<a href="{{ url_for('cash_close') }}">{{ ic('lock') }}إغلاق صندوق اليوم</a>{% endif %}
{% if perm('expenses') and cu.role!='admin' %}<a href="{{ url_for('expenses') }}">{{ ic('expense') }}إخراج مبلغ (مصروف)</a>{% endif %}
{% if perm('purchases') and cu.role!='admin' %}<a href="{{ url_for('purchases') }}">{{ ic('invoice') }}فواتير الشراء</a>{% endif %}
{% if perm('courses') %}<a href="{{ url_for('courses') }}">{{ ic('course') }}الدورات والشهادات</a>{% endif %}
{% if perm('attendance') %}<a href="{{ url_for('staff') }}">{{ ic('staff') }}العمال والحضور</a>{% endif %}
{% if perm('stock_alerts') %}<a href="{{ url_for('stock_alerts_page') }}">{{ ic('alert') }}تنبيهات المخزون{% if alerts_count %} <span class="badge">{{ alerts_count }}</span>{% endif %}</a>{% endif %}
</div></details>
{% if cu.role=='admin' %}<details class="dd"><summary>{{ ic('shield') }}الإدارة ▾</summary><div class="ddm">
<a href="{{ url_for('cash_daily') }}">{{ ic('safe') }}الصندوق اليومي</a>
<a href="{{ url_for('cashbox') }}">{{ ic('vault') }}{{ 'كل العمليات (الصندوق المركزي)' if not view_branch else 'عمليات الفرع' }}</a>
<a href="{{ url_for('reports') }}">{{ ic('reports') }}التقارير والأرباح</a>
<a href="{{ url_for('expenses') }}">{{ ic('expense') }}المصاريف</a>
<a href="{{ url_for('permissions') }}">{{ ic('key') }}صلاحيات العمال</a>
<a href="{{ url_for('audit_page') }}">{{ ic('audit') }}سجل العمليات</a>
<a href="{{ url_for('backup_page') }}">{{ ic('backup') }}النسخ الاحتياطي</a>
<a href="{{ url_for('products') }}">{{ ic('products') }}المنتجات والمخزون</a>
<a href="{{ url_for('purchases') }}">{{ ic('truck') }}المشتريات والموردون</a>
<a href="{{ url_for('services') }}">{{ ic('services') }}الخدمات والأسعار</a>
<a href="{{ url_for('branches') }}">{{ ic('branch') }}الفروع والغرف</a>
{% if not NODE %}<a href="{{ url_for('devices') }}">{{ ic('monitor') }}الحواسيب وكلمات السر</a>{% endif %}
<a href="{{ url_for('users') }}">{{ ic('users') }}المستخدمون</a>
<a href="{{ url_for('sms_page') }}">{{ ic('sms') }}رسائل SMS</a>
<a href="{{ url_for('settings') }}">{{ ic('settings') }}الإعدادات</a>
</div></details>{% endif %}
</nav>
{% endif %}
<main>
{% if NODE and node_status %}{% if node_status.update %}<div class="flash noprint" style="background:#fff4df;border:1px solid #e4ab74;color:#6b4a12">{{ ic('sync') }}
<b>نسخة جديدة من البرنامج جاهزة في حاسوب المديرة.</b> هذا الحاسوب يتحدّث وحده عند تشغيله أو بعد 5 دقائق بلا استعمال.
العمليات المسجّلة هنا تُرسل عاديًا. <a href="{{ url_for('update_now') }}" onclick="return confirm('تحديث البرنامج الآن؟ يتوقف دقيقة ثم يرجع وحده.')"><b>حدّث الآن</b></a></div>
{% elif node_status.err %}<div class="flash err noprint">غير متصل بالحاسوب المركزي — البرنامج يعمل عاديًا والعمليات محفوظة هنا ({{ node_status.pending }} عملية تنتظر الإرسال)، وستُرسل تلقائيًا عند رجوع الإنترنت.
<a href="{{ url_for('sync_now_route') }}">إعادة المحاولة الآن</a></div>
{% elif node_status.ok %}<div class="mut noprint" style="color:var(--goldl);margin-bottom:8px">متصل بالحاسوب المركزي — آخر مزامنة {{ node_status.ok[11:16] }}{% if node_status.pending %} · {{ node_status.pending }} عملية تنتظر الإرسال{% endif %} · <a style="color:var(--goldl)" href="{{ url_for('sync_now_route') }}">مزامنة الآن</a></div>{% endif %}{% endif %}
{% if bk and bk.warn %}<div class="flash err noprint">تنبيه: لم تُصنع نسخة احتياطية منذ أكثر من يومين{% if bk.err %} ({{ bk.err }}){% endif %}. <a href="{{ url_for('backup_page') }}">النسخ الاحتياطي</a></div>{% endif %}
{% if cu and cu.role=='admin' and view_branch %}<div class="viewing noprint">أنت تعرض: <b>{{ branch_name(view_branch) }}</b> وحده — كل الصفحات مصفّاة على هذا الفرع.
<a class="btn sm" href="{{ url_for('view_branch', b='') }}" style="margin-inline-start:auto">عرض كل الفروع</a></div>{% endif %}
{% if cu and alerts_count and request.endpoint in ('dashboard','branch_view','reception','pos') %}<div class="flash err noprint">تنبيه: {{ alerts_count }} منتج قارب على النفاد أو اقتربت صلاحيته. <a href="{{ url_for('stock_alerts_page') }}">عرض القائمة</a></div>{% endif %}
{% for cat, m in get_flashed_messages(with_categories=true) %}<div class="flash {{ cat }}">{{ m }}</div>{% endfor %}
{% block body %}{% endblock %}
</main>
<script>
document.addEventListener('click',function(e){document.querySelectorAll('details.dd[open]').forEach(function(d){if(!d.contains(e.target))d.removeAttribute('open')})});
document.querySelectorAll('.picker').forEach(function(pk){
  var inp=pk.querySelector('input[type=text]'), hid=pk.querySelector('input[type=hidden]'), list=pk.querySelector('.list'), t;
  inp.addEventListener('input',function(){hid.value='';clearTimeout(t);var q=inp.value.trim();
    if(q.length<1){list.style.display='none';return}
    t=setTimeout(function(){fetch('{{ url_for("api_clients") }}?q='+encodeURIComponent(q)).then(r=>r.json()).then(function(d){
      list.innerHTML='';d.items.forEach(function(c){var el=document.createElement('div');
        el.textContent=c.name+(c.phone?' — '+c.phone:'');el.onclick=function(){inp.value=c.name;hid.value=c.id;list.style.display='none'};
        list.appendChild(el)});
      if(!d.items.length){list.innerHTML='<div class="mut">لا يوجد — أضفه من زر «زبون جديد»</div>'}
      list.style.display='block'})},250)});
  document.addEventListener('click',function(e){if(!pk.contains(e.target))list.style.display='none'});
});
</script>
{% if cu %}<script>
/* تحديث تلقائي:
   - صفحات المتابعة (الرئيسية، التحصيل، المواعيد...) تتحدث وحدها كي توصل معلومة جديدة.
   - كل الصفحات تتحدث كي تشغّل المديرة أو توقف مهمة، باش تبان أو تختفي فورًا.
   ما تتحدثش إذا كان العامل يكتب في خانة. */
(function(){var s=null,p=null,dirty=false,live={{ 'true' if live_page() else 'false' }};
document.addEventListener('input',function(){dirty=true});
function busy(){return dirty||document.querySelector('details[open].dd')}
function reload(){try{sessionStorage.setItem('bil_y',window.scrollY)}catch(e){}location.reload()}
setInterval(function(){fetch('/api/stamp',{cache:'no-store'}).then(function(r){return r.json()}).then(function(d){
 if(p!==null&&d.p!==p&&!busy()){reload();return}
 if(live&&s!==null&&d.s!==s&&!busy()){reload();return}
 s=d.s;p=d.p}).catch(function(){})},2500);
try{var y=sessionStorage.getItem('bil_y');if(y){window.scrollTo(0,+y);sessionStorage.removeItem('bil_y')}}catch(e){}
})();</script>{% endif %}
</body></html>"""

TEMPLATES["macros.html"] = r"""
{% macro client_picker(sel=None, required=False) %}
<label>الزبون
<div class="picker"><input type="text" placeholder="ابحث بالاسم أو الهاتف" autocomplete="off" value="{{ sel.name if sel else '' }}" style="width:230px">
<input type="hidden" name="client_id" value="{{ sel.id if sel else '' }}" {{ 'required' if required }}>
<div class="list"></div></div></label>
<a class="btn light sm" href="#" onclick="document.getElementById('newc').style.display='block';return false">+ زبون جديد</a>
{% endmacro %}
{% macro new_client_box(back) %}
<div id="newc" class="card" style="display:none;background:#f6fbf6">
<h2>زبون جديد</h2>
<form method="post" action="{{ url_for('clients') }}" class="row">
<input type="hidden" name="back" value="{{ back }}">
<label>الاسم واللقب<input name="name" required></label>
<label>الهاتف<input name="phone" placeholder="05xxxxxxxx"></label>
<label>تاريخ الميلاد<input type="date" name="birth_date"></label>
<label>الجنس<select name="gender"><option value="">—</option><option>ذكر</option><option>أنثى</option></select></label>
<label>العنوان<input name="address"></label>
<label>أمراض مزمنة<input name="chronic" placeholder="سكري، ضغط..."></label>
<label>حساسية<input name="allergies"></label>
<label>أدوية يتناولها<input name="medications"></label>
{% if cu.role=='admin' %}<label>الفرع<select name="branch_id">{% for b in all_branches %}<option value="{{ b.id }}">{{ b.name }}</option>{% endfor %}</select></label>{% endif %}
<label>ملاحظات<input name="notes"></label>
<button class="btn">حفظ واختيار</button></form></div>
{% endmacro %}
{% macro branch_filter(br, extra='') %}
{% if cu.role=='admin' %}<label>الفرع<select name="branch"><option value="">كل الفروع</option>
{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>{% endif %}
{% endmacro %}
"""

TEMPLATES["login.html"] = r"""{% extends "base.html" %}{% block body %}
<div style="max-width:380px;margin:30px auto;text-align:center">
<img class="brandlogo" src="{{ url_for('static', filename='logo.png') }}" alt="{{ center }}" style="width:230px">
<div class="card" style="margin-top:18px">
{% if NODE and node_status and node_status.first %}<div class="flash err">هذا حاسوب الفرع. في انتظار أول اتصال بالحاسوب المركزي لجلب المستخدمين والقوائم... {% if node_status.err %}({{ node_status.err }}){% endif %} <a href="{{ url_for('sync_now_route') }}">حاول الآن</a></div>{% endif %}
<form method="post" style="display:flex;flex-direction:column;gap:10px">
{% if dev or (NODE and NODE.device) %}<div style="font-size:20px;font-weight:bold">{{ dev.full_name if dev else 'هذا الحاسوب' }}</div>
<input name="password" type="password" placeholder="كلمة سر الحاسوب" required autofocus style="text-align:center;font-size:20px">
{% else %}<input name="username" placeholder="اسم المستخدم" required autofocus>
<input name="password" type="password" placeholder="كلمة المرور" required>{% endif %}
<button class="btn">دخول</button></form></div></div>
{% endblock %}"""

TEMPLATES["password.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="card" style="max-width:420px"><h1>{{ page_icon() }}تغيير كلمة المرور</h1>
<form method="post" style="display:flex;flex-direction:column;gap:10px">
<input type="password" name="old" placeholder="كلمة المرور الحالية" required>
<input type="password" name="new" placeholder="كلمة المرور الجديدة" required>
<button class="btn">حفظ</button></form></div>{% endblock %}"""

TEMPLATES["msg.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="card"><h1>{{ page_icon() }}{{ msg }}</h1><a class="btn" href="{{ url_for('dashboard') }}">الرجوع للرئيسية</a></div>{% endblock %}"""

TEMPLATES["dash_admin.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}الحاسوب المركزي — مداخيل اليوم</h1>
{% include "tiles.html" %}
<div class="grid" style="margin-bottom:16px">
<div class="stat"><div class="l">مجموع المداخيل اليوم (كل الفروع)</div><div class="n">{{ grand|money }} {{ cur }}</div></div>
{% for b in per_branch %}
<div class="stat"><div class="l"><a href="{{ url_for('branch_view', bid=b.id) }}">{{ b.name }}</a></div><div class="n">{{ b.total|money }} {{ cur }}</div>
<div class="mut">{{ b.cnt }} عملية · {{ b.pending }} مبلغ ينتظر التحصيل · {{ b.appts }} موعد اليوم</div></div>
{% endfor %}</div>
<div class="card"><h2>آخر الدفعات من كل الفروع</h2>
<table><tr><th>الوصل</th><th>الوقت</th><th>الفرع</th><th>الزبون</th><th>النوع</th><th>البيان</th><th>المبلغ</th><th>استلمه</th></tr>
{% for p in recent %}<tr class="{{ 'cx' if p.cancelled }}"><td><a href="{{ url_for('receipt', pid=p.id) }}">{{ p.id|rid }}</a></td>
<td>{{ p.created_at[:16] }}</td><td>{{ p.branch }}</td><td>{{ p.client or '-' }}</td><td>{{ PAY_KINDS[p.kind] }}</td>
<td>{{ p.description }}</td><td>{{ p.amount|money }}</td><td>{{ p.by_name or '' }}</td></tr>
{% else %}<tr><td colspan="8" class="mut">لا توجد دفعات بعد</td></tr>{% endfor %}</table>
<p><a class="btn light" href="{{ url_for('cashbox') }}">فتح الصندوق المركزي</a></p></div>
{% if due %}<div class="card"><h2>أجور مستحقة ({{ due|length }})</h2><table><tr><th>العامل</th><th>الفرع</th><th>الفترة</th><th>يوم الأجرة</th><th></th></tr>
{% for d in due %}<tr><td>{{ d.e.name }}</td><td>{{ branch_name(d.e.branch_id) }}</td><td>{{ d.d1 }} ← {{ d.d2 }}</td><td><span class="tag {{ 'red' if d.late else 'amber' }}">{{ d.due }}</span></td>
<td><a class="btn gold sm" href="{{ url_for('payslip', eid=d.e.id, month=d.mm) }}">الكشف والدفع</a></td></tr>{% endfor %}</table></div>{% endif %}
{% if low %}<div class="card"><h2>منتجات قاربت على النفاد</h2><table><tr><th>المنتج</th><th>الفرع</th><th>الكمية</th><th>حد التنبيه</th><th>الصلاحية</th></tr>
{% for l in low %}<tr><td>{{ l.name }}</td><td>{{ l.branch }}</td><td><span class="tag {{ 'red' if l.low else '' }}">{{ '%g'|format(l.qty) }}</span></td><td>{{ '%g'|format(l.min_qty) }}</td><td>{% if l.expiring %}<span class="tag amber">{{ l.expiry }}</span>{% endif %}</td></tr>{% endfor %}</table>
<p><a class="btn light" href="{{ url_for('stock_alerts_page') }}">صفحة التنبيهات والطباعة</a></p></div>{% endif %}
{% endblock %}"""

TEMPLATES["dash_staff.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}مرحبًا {{ cu.full_name or cu.username }}</h1>
{% include "tiles.html" %}
<div class="grid" style="margin-bottom:16px">
<div class="stat"><div class="l">مواعيد اليوم</div><div class="n">{{ appts|length }}</div></div>
{% if can_collect %}
<div class="stat"><div class="l">مبالغ تنتظر التحصيل</div><div class="n">{{ pending }}</div><a href="{{ url_for('reception') }}">فتح</a></div>

{% endif %}</div>
<div class="card"><h2>مواعيد اليوم</h2>
{% include "appt_table.html" %}
</div>
{% if perm('stock_alerts') and cu.role!='admin' and low %}<div class="card"><h2>منتجات قاربت على النفاد في فرعك</h2><table><tr><th>المنتج</th><th>الكمية</th><th>حد التنبيه</th></tr>
{% for l in low %}<tr><td>{{ l.name }}</td><td><span class="tag red">{{ '%g'|format(l.qty) }}</span></td><td>{{ '%g'|format(l.min_qty) }}</td></tr>{% endfor %}</table>
<p><a class="btn light" href="{{ url_for('stock_alerts_page') }}">عرض وطباعة القائمة</a></p></div>{% endif %}{% endblock %}"""

TEMPLATES["appt_table.html"] = r"""<table><tr><th>الساعة</th>{% if cu.role=='admin' %}<th>الفرع</th>{% endif %}<th>القسم</th><th>الزبون</th><th>الهاتف</th><th>الخدمة / الحصة</th><th>الغرفة</th><th>الحالة</th><th>الدفع</th><th>SMS</th><th></th></tr>
{% for a in (rows if rows is defined else appts) %}<tr>
<td>{{ a.start_at[11:16] }}</td>{% if cu.role=='admin' %}<td>{{ a.branch }}</td>{% endif %}
<td>{{ DEPTS[a.dept] }}</td><td><a href="{{ url_for('client_view', cid=a.client_id) }}">{{ avatar(a.client) }}{{ a.client }}</a></td><td>{{ a.phone }}</td>
<td>{% if a.plan_id %}<a href="{{ url_for('plan_view', pid=a.plan_id) }}">{{ a.plan_title }}</a><div><span class="tag">حصة {{ a.session_no }} من {{ a.plan_n }}</span></div>{% else %}{{ a.service or '-' }}{% endif %}{% if a.notes %}<div class="mut">{{ a.notes }}</div>{% endif %}</td>
<td>{{ a.room or '' }}</td>
<td><span class="tag {{ {'scheduled':'amber','cancelled':'red','noshow':'gray'}.get(a.status,'') }}">{{ APPT_STATUS[a.status] }}</span></td>
<td>{% if a.paid %}<span class="tag">مدفوعة</span>{% elif a.plan_id %}<span class="tag amber">غير مدفوعة{% if a.price %} ({{ '%g'|format(a.price) }}){% endif %}</span>{% else %}<span class="mut">-</span>{% endif %}</td>
<td>{% if a.sms_sent_at %}<span class="tag">أُرسل</span>{% else %}<span class="mut">-</span>{% endif %}</td>
<td>{% if a.status=='scheduled' %}
<form method="post" action="{{ url_for('appt_done', aid=a.id) }}" style="display:inline-flex;gap:4px">
{% if a.paid %}<input type="hidden" name="amount" value="0">{% else %}<input name="amount" {% if locked %}readonly title="السعر تحدده المديرة"{% endif %} placeholder="المبلغ" style="width:90px" value="{{ ('%g'|format(a.price) if a.price else '') if a.plan_id else ('%g'|format(a.sprice) if a.sprice else '') }}">{% endif %}
<button class="btn sm" title="إنهاء وإرسال المبلغ للاستقبال">تم ✓</button>
{% if can_collect and not a.paid %}<button class="btn gold sm" name="collect" value="1" title="إنهاء وتحصيل المبلغ هنا">تم + تحصيل</button>{% endif %}</form>
<form method="post" action="{{ url_for('appt_status', aid=a.id) }}" style="display:inline">
<select name="status" onchange="this.form.submit()" style="padding:3px"><option value="">…</option>
<option value="noshow">لم يحضر</option><option value="cancelled">إلغاء</option></select></form>
{% elif a.status in ('cancelled','noshow') %}
<form method="post" action="{{ url_for('appt_status', aid=a.id) }}" style="display:inline"><input type="hidden" name="status" value="scheduled"><button class="btn light sm">إرجاع</button></form>
{% endif %}</td></tr>
{% else %}<tr><td colspan="11" class="mut">لا توجد مواعيد</td></tr>{% endfor %}</table>"""

TEMPLATES["clients.html"] = r"""{% extends "base.html" %}{% from "macros.html" import new_client_box with context %}{% block body %}
<h1>{{ page_icon() }}الزبائن</h1>
<div class="card"><form class="row"><label>بحث<input name="q" value="{{ s }}" placeholder="الاسم أو الهاتف"></label><button class="btn">بحث</button>
<a class="btn light" href="#" onclick="document.getElementById('newc').style.display='block';return false">+ زبون جديد</a></form></div>
{{ new_client_box('') }}
<div class="card"><table><tr><th>#</th><th>الاسم</th><th>الهاتف</th><th>الفرع</th><th>تاريخ التسجيل</th></tr>
{% for c in rows %}<tr><td>{{ c.id }}</td><td><a href="{{ url_for('client_view', cid=c.id) }}">{{ avatar(c.name) }}{{ c.name }}</a></td><td>{{ c.phone }}</td><td>{{ c.branch or '' }}</td><td>{{ (c.created_at or '')[:10] }}</td></tr>
{% else %}<tr><td colspan="5" class="mut">لا يوجد زبائن</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["client_view.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}{{ c.name }}</h1>
<div class="card"><form method="post" class="row">
<label>الاسم<input name="name" value="{{ c.name }}"></label><label>الهاتف<input name="phone" value="{{ c.phone or '' }}"></label>
<label>تاريخ الميلاد{% if c.birth_date %} ({{ c.birth_date|age }} سنة){% endif %}<input type="date" name="birth_date" value="{{ c.birth_date or '' }}"></label>
<label>الجنس<select name="gender"><option value="">—</option>{% for g in ('ذكر','أنثى') %}<option {{ 'selected' if c.gender==g }}>{{ g }}</option>{% endfor %}</select></label>
<label>العنوان<input name="address" value="{{ c.address or '' }}"></label>
<label>أمراض مزمنة<input name="chronic" value="{{ c.chronic or '' }}"></label>
<label>حساسية<input name="allergies" value="{{ c.allergies or '' }}"></label>
<label>أدوية يتناولها<input name="medications" value="{{ c.medications or '' }}"></label>
<label style="flex:1">ملاحظات<input name="notes" value="{{ c.notes or '' }}"></label><button class="btn">حفظ</button></form>
<p class="row">{% if perm('reception_visits') %}<a class="btn gold sm" href="{{ url_for('visit_new', client_id=c.id) }}">إرسال الزبون للعلاج (زيارة)</a>{% endif %}
<a class="btn light sm" href="{{ url_for('appointments', client_id=c.id) }}">+ موعد</a>
<a class="btn light sm" href="{{ url_for('plan_new', client_id=c.id) }}">+ خطة حصص</a>
{% if perm('pos') %}<a class="btn light sm" href="{{ url_for('pos', client_id=c.id) }}">بيع منتجات</a>{% endif %}
{% if perm('direct_payment') %}<a class="btn light sm" href="{{ url_for('payment_new', client_id=c.id) }}">دفعة مباشرة</a>{% endif %}</p></div>
{% if perm('medical') or perm('consent') %}<div class="card"><h2>الملف الطبي</h2>
<div class="row" style="margin-bottom:10px">
{% if perm('consent') %}<form class="row" action="{{ url_for('consent', cid=c.id) }}"><label>وثيقة الموافقة على<input name="procedure" list="procs2" style="width:240px" placeholder="اختر الإجراء"></label>
<datalist id="procs2">{% for s in services %}<option value="{{ s.name }}">{% endfor %}</datalist><button class="btn light sm">طباعة وثيقة الموافقة</button></form>{% endif %}</div>
{% if perm('medical') %}<form method="post" action="{{ url_for('client_note', cid=c.id) }}" class="row"><label style="flex:1">ملاحظة جديدة (جلسة، تطور الحالة، توصيات...)<textarea name="note" rows="2"></textarea></label><button class="btn">إضافة</button></form>
<table style="margin-top:10px">{% for n in notes %}<tr><td style="width:130px" class="mut">{{ n.created_at[:16] }}<br>{{ n.by_name or '' }}</td><td>{{ n.note }}</td>
{% if cu.role=='admin' %}<td><form method="post" action="{{ url_for('client_note', cid=c.id) }}"><input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{{ n.id }}"><button class="btn red sm">حذف</button></form></td>{% endif %}</tr>
{% else %}<tr><td class="mut">لا توجد ملاحظات</td></tr>{% endfor %}</table>{% endif %}
{% if can_photos %}<h2 style="margin-top:16px">صور قبل / بعد</h2>
<form method="post" action="{{ url_for('client_photo', cid=c.id) }}" enctype="multipart/form-data" class="row">
<label>الصور<input type="file" name="photo" accept="image/*" multiple capture="environment"></label>
<label>النوع<select name="kind"><option value="before">قبل</option><option value="after">بعد</option><option value="other">أخرى</option></select></label>
<label>ملاحظة<input name="note" placeholder="مثلاً: الجلسة 3 — الوجه"></label><button class="btn">رفع</button></form>
<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:10px">{% for p in photos %}
<div style="width:170px;text-align:center"><a href="{{ url_for('photo', phid=p.id) }}" target="_blank"><img src="{{ url_for('photo', phid=p.id) }}" style="width:170px;height:130px;object-fit:cover;border-radius:8px;border:1px solid #e2d3bd"></a>
<div><span class="tag {{ '' if p.kind=='after' else 'amber' }}">{{ {'before':'قبل','after':'بعد','other':'أخرى'}[p.kind] }}</span> <span class="mut">{{ p.created_at[:10] }}</span></div><div class="mut">{{ p.note or '' }}</div>
{% if cu.role=='admin' %}<form method="post" action="{{ url_for('client_photo', cid=c.id) }}"><input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{{ p.id }}"><button class="btn red sm">حذف</button></form>{% endif %}</div>
{% else %}<span class="mut">لا توجد صور</span>{% endfor %}</div>{% endif %}</div>{% endif %}
{% if cdebts %}<div class="card" style="border-color:#c0392b"><h2>ديون على الزبون: {{ cdebts|sum(attribute='amount')|money }} {{ cur }}</h2>
<table>{% for d in cdebts %}<tr><td>{{ d.created_at[:10] }}</td><td>{{ d.description }}</td><td><b>{{ d.amount|money }}</b></td></tr>{% endfor %}</table>
{% if can_collect %}<p><a class="btn gold sm" href="{{ url_for('debts', client_id=c.id) }}">تسديد</a></p>{% endif %}</div>{% endif %}
<div class="card"><h2>الزيارات</h2><table><tr><th>#</th><th>التاريخ</th><th>الفرع</th><th>الطلب</th><th>المجموع</th><th>الحالة</th></tr>
{% for v in cvisits %}<tr><td><a href="{{ url_for('visit_view', vid=v.id) }}">{{ v.id|rid }}</a></td><td>{{ v.created_at[:16] }}</td><td>{{ v.branch }}</td><td>{{ v.request or '' }}</td><td>{{ v.total|money }}</td><td>{{ VISIT_STATUS[v.status] }}</td></tr>
{% else %}<tr><td colspan="6" class="mut">لا شيء</td></tr>{% endfor %}</table></div>
<div class="card"><h2>خطط الحصص</h2><table><tr><th>الخطة</th><th>الحصص المنجزة</th><th>الحصص المدفوعة</th><th>الحالة</th></tr>
{% for p in cplans %}<tr><td><a href="{{ url_for('plan_view', pid=p.id) }}">{{ p.title }}</a></td><td>{{ p.done }} / {{ p.n }}</td><td>{{ p.paid_n }} / {{ p.n }}</td><td>{{ PLAN_STATUS[p.status] }}</td></tr>
{% else %}<tr><td colspan="4" class="mut">لا شيء</td></tr>{% endfor %}</table></div>
<div class="card"><h2>المواعيد</h2><table><tr><th>التاريخ</th><th>الفرع</th><th>القسم</th><th>الخدمة</th><th>الحالة</th></tr>
{% for a in appts %}<tr><td>{{ a.start_at or 'لم يُحدد' }}{% if a.session_no %} <span class="tag">حصة {{ a.session_no }}</span>{% endif %}</td><td>{{ a.branch }}</td><td>{{ DEPTS[a.dept] }}</td><td>{{ a.service or '-' }}</td><td>{{ APPT_STATUS[a.status] }}</td></tr>
{% else %}<tr><td colspan="5" class="mut">لا شيء</td></tr>{% endfor %}</table></div>
<div class="card"><h2>المدفوعات</h2><table><tr><th>الوصل</th><th>التاريخ</th><th>الفرع</th><th>البيان</th><th>المبلغ</th></tr>
{% for p in pays %}<tr class="{{ 'cx' if p.cancelled }}"><td><a href="{{ url_for('receipt', pid=p.id) }}">{{ p.id|rid }}</a></td><td>{{ p.created_at[:16] }}</td><td>{{ p.branch }}</td><td>{{ p.description }}</td><td>{{ p.amount|money }}</td></tr>
{% else %}<tr><td colspan="5" class="mut">لا شيء</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["appointments.html"] = r"""{% extends "base.html" %}{% from "macros.html" import client_picker, new_client_box, branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}المواعيد</h1>
<div class="row" style="margin-bottom:14px"><a class="btn" href="{{ url_for('plan_new') }}">+ موعد بعدة حصص (خطة جلسات)</a>
<a class="btn light" href="{{ url_for('plans') }}">كل خطط الحصص</a></div>
{% if perm('appointments') %}<div class="card"><h2>موعد واحد</h2>
<form method="post" class="row">
{{ client_picker(sel_client, True) }}
{% if cu.role=='admin' %}<label>الفرع<select name="branch_id" onchange="location='?branch='+this.value+'&date={{ d }}'">{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if form_branch==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>{% endif %}
{% if cu.role in ('admin','reception') %}<label>القسم<select name="dept" id="dept">{% for k in depts %}<option value="{{ k }}">{{ DEPTS[k] }}</option>{% endfor %}</select></label>{% endif %}
<label>الخدمة<select name="service_id"><option value="">—</option>{% for s in services %}{% if cu.role not in ('laser','beauty') or s.dept==cu.role %}<option value="{{ s.id }}" data-dept="{{ s.dept }}">{{ s.name }} ({{ DEPTS[s.dept] }})</option>{% endif %}{% endfor %}</select></label>
<label>الغرفة<select name="post_id"><option value="">—</option>{% for p in posts %}<option value="{{ p.id }}">{{ p.name }}</option>{% endfor %}</select></label>
<label>التاريخ<input type="date" name="date" value="{{ d }}" required></label>
<label>الساعة<input type="time" name="time" required></label>
<label>ملاحظة<input name="notes"></label>
<label style="flex-direction:row;align-items:center;gap:4px"><input type="checkbox" name="force" value="1"> حجز رغم التعارض</label>
<button class="btn">تسجيل الموعد</button></form>
<p class="mut">مواعيد التجميل تصل الزبون تذكيرًا برسالة SMS قبل الموعد تلقائيًا (حسب الإعدادات).</p></div>{% endif %}
{{ new_client_box(request.path ~ '?date=' ~ d) }}
<div class="card"><form class="row" style="margin-bottom:12px">
<label>اليوم<input type="date" name="date" value="{{ d }}"></label>
{{ branch_filter(br) }}
{% if cu.role in ('admin','reception') %}<label>القسم<select name="dept"><option value="">الكل</option>{% for k,v in DEPTS.items() %}<option value="{{ k }}" {{ 'selected' if dept==k }}>{{ v }}</option>{% endfor %}</select></label>{% endif %}
<button class="btn light">عرض</button></form>
{% include "appt_table.html" %}</div>{% endblock %}"""

TEMPLATES["charge_new.html"] = r"""{% extends "base.html" %}{% from "macros.html" import client_picker, new_client_box with context %}{% block body %}
<h1>{{ page_icon() }}إرسال مبلغ إلى الاستقبال</h1>
<div class="card"><p class="mut">بعد تقديم الخدمة، حدّد المبلغ هنا فيظهر عند الاستقبال ليحصّله من الزبون.</p>
<form method="post" class="row">
{{ client_picker(sel_client) }}
{% if cu.role in ('admin','reception') %}<label>القسم<select name="dept">{% for k in depts %}<option value="{{ k }}">{{ DEPTS[k] }}</option>{% endfor %}</select></label>{% endif %}
<label>الخدمة<select name="service_id" onchange="var o=this.selectedOptions[0];if(o.dataset.p&&o.dataset.p!='0')document.getElementById('amt').value=o.dataset.p">
<option value="">—</option>{% for s in services %}<option value="{{ s.id }}" data-p="{{ '%g'|format(s.price) }}">{{ s.name }}</option>{% endfor %}</select></label>
<label>البيان<input name="description"></label>
<label>المبلغ ({{ cur }})<input name="amount" id="amt" {% if locked %}readonly title="السعر تحدده المديرة"{% endif %} required style="width:120px"></label>
<button class="btn">إرسال للاستقبال</button></form></div>
{{ new_client_box(request.path) }}{% endblock %}"""

TEMPLATES["reception.html"] = r"""{% extends "base.html" %}{% from "macros.html" import branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}{{ 'الاستقبال والتحصيل' if cu.role in ('admin','reception') else 'التحصيل — ' ~ DEPTS[cu.role] }}</h1>
{% if cu.role=='admin' %}<div class="card"><form class="row">{{ branch_filter(br) }}<button class="btn light">عرض</button></form></div>{% endif %}
<div class="row" style="margin-bottom:14px">
{% if perm('reception_visits') %}<a class="btn gold" href="{{ url_for('visit_new') }}">استقبال زبون وإرساله للعلاج</a>{% endif %}
{% if perm('pos') %}<a class="btn" href="{{ url_for('pos', branch=br) }}">بيع منتجات</a>{% endif %}
{% if perm('direct_payment') %}<a class="btn" href="{{ url_for('payment_new', branch=br) }}">دفعة مباشرة</a>{% endif %}
{% if perm('appointments') %}<a class="btn light" href="{{ url_for('appointments') }}">موعد جديد</a>{% endif %}
{% if perm('cash_close') and cu.role!='admin' %}<a class="btn light" href="{{ url_for('cash_close') }}">إغلاق صندوق اليوم</a>{% endif %}</div>
{% if open_visits %}<div class="card"><h2>زبائن داخل العلاج الآن ({{ open_visits|length }})</h2><table><tr><th>#</th><th>الوصول</th><th>الزبون</th><th>عند</th><th>الحالة</th></tr>
{% for v in open_visits %}<tr><td><a href="{{ url_for('visit_view', vid=v.id) }}">{{ v.id|rid }}</a></td><td>{{ v.created_at[11:16] }}</td><td>{{ v.client }}</td><td>{{ VISIT_TARGETS.get(v.target,'') }}</td><td><span class="tag amber">{{ VISIT_STATUS[v.status] }}</span></td></tr>{% endfor %}</table></div>{% endif %}
<div class="card"><h2>مبالغ من الأقسام تنتظر التحصيل ({{ pending|length }})</h2>
<table><tr><th>#</th><th>الوقت</th>{% if cu.role=='admin' %}<th>الفرع</th>{% endif %}<th>القسم</th><th>الزبون</th><th>البيان</th><th>أرسله</th><th>المبلغ</th><th>التحصيل</th></tr>
{% for c in pending %}<tr><td>{{ c.id|rid }}</td><td>{{ c.created_at[11:16] }}</td>{% if cu.role=='admin' %}<td>{{ c.branch }}</td>{% endif %}
<td>{{ DEPTS[c.dept] }}</td><td>{{ c.client or '-' }}</td><td>{{ c.description }}</td><td>{{ c.by_name or '' }}</td><td><b>{{ c.amount|money }}</b></td>
<td><form method="post" action="{{ url_for('charge_pay', chid=c.id) }}" style="display:inline-flex;gap:4px;flex-wrap:wrap">
{% if not locked %}<input name="discount" placeholder="تخفيض" style="width:70px" title="تخفيض (بإذن المديرة)">{% endif %}
<input name="paid" value="{{ '%g'|format(c.amount) }}" style="width:85px" title="المبلغ المدفوع الآن — إذا كان أقل يبقى الباقي دينًا على الزبون">
<select name="method">{% for k,v in METHODS.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select>
<button class="btn sm">استلام المبلغ</button></form>
<form method="post" action="{{ url_for('charge_cancel', chid=c.id) }}" style="display:inline" onsubmit="return confirm('إلغاء هذا المبلغ؟')"><button class="btn red sm">إلغاء</button></form></td></tr>
{% else %}<tr><td colspan="9" class="mut">لا توجد مبالغ معلقة</td></tr>{% endfor %}</table></div>
<div class="card"><h2>{% if cu.role=='admin' %}عمليات اليوم — المجموع: {{ total|money }} {{ cur }}{% else %}الوصولات التي سلّمتها اليوم (لإعادة الطباعة){% endif %}</h2>
<table><tr><th>الوصل</th><th>الوقت</th><th>الزبون</th><th>النوع</th><th>البيان</th><th>الدفع</th><th>المبلغ</th></tr>
{% for p in todays %}<tr class="{{ 'cx' if p.cancelled }}"><td><a href="{{ url_for('receipt', pid=p.id) }}">{{ p.id|rid }}</a></td><td>{{ p.created_at[11:16] }}</td><td>{{ p.client or '-' }}</td>
<td>{{ PAY_KINDS[p.kind] }}</td><td>{{ p.description }}</td><td>{{ METHODS.get(p.method, p.method) }}</td><td>{{ p.amount|money }}</td></tr>
{% else %}<tr><td colspan="7" class="mut">لا شيء اليوم</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["payment_new.html"] = r"""{% extends "base.html" %}{% from "macros.html" import client_picker, new_client_box with context %}{% block body %}
<h1>{{ page_icon() }}دفعة مباشرة في الاستقبال</h1>
<div class="card"><form method="post" class="row">
{% if cu.role=='admin' %}<label>الفرع<select name="branch">{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>{% endif %}
{{ client_picker(sel_client) }}
<label>الخدمة<select name="service_id" onchange="var o=this.selectedOptions[0];if(o.dataset.p&&o.dataset.p!='0')document.getElementById('amt').value=o.dataset.p">
<option value="">— أخرى —</option>{% for s in services %}<option value="{{ s.id }}" data-p="{{ '%g'|format(s.price) }}">{{ s.name }} ({{ SERVICE_KINDS[s.kind] }})</option>{% endfor %}</select></label>
<label>البيان<input name="description" placeholder="اختياري"></label>
{% if locked %}<label>العدد<input name="qty" value="1" style="width:60px"></label>{% endif %}
<label>المبلغ ({{ cur }})<input name="amount" id="amt" {% if locked %}readonly title="السعر تحدده المديرة"{% endif %} required style="width:120px"></label>
<label>الدفع<select name="method">{% for k,v in METHODS.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></label>
<button class="btn">تسجيل وطباعة الوصل</button></form></div>
{{ new_client_box(request.path) }}{% endblock %}"""

TEMPLATES["pos.html"] = r"""{% extends "base.html" %}{% from "macros.html" import client_picker, new_client_box with context %}{% block body %}
<h1>{{ page_icon() }}بيع المنتجات</h1>
{% if cu.role=='admin' %}<div class="card"><form class="row"><label>البيع باسم فرع<select name="branch" onchange="this.form.submit()">{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select></label></form></div>{% endif %}
<div style="display:grid;grid-template-columns:minmax(0,3fr) minmax(280px,2fr);gap:16px">
<div class="card"><div style="display:flex;gap:8px;margin-bottom:10px"><input id="search" placeholder="ابحث عن منتج أو امسح الباركود" style="flex:1" autofocus>
<button type="button" class="btn gold" onclick="qpShow(true,document.getElementById('search').value.trim())">{{ ic('products') }} منتج جديد غير مسجّل</button></div>
<div id="nores" class="mut" style="display:none;margin-bottom:8px">ما لقيناش هذا المنتج. <a href="#" onclick="qpShow(true,document.getElementById('search').value.trim());return false">أضفه كمنتج جديد</a></div>
<table id="plist"><tr><th>المنتج</th><th>الفئة</th><th>السعر</th><th>المخزون</th><th></th></tr></table>
{% if not prods %}<p class="mut">لا توجد منتجات بعد. اضغط «منتج جديد غير مسجّل» لإضافة واحد.</p>{% endif %}</div>
<div class="card"><h2>السلة</h2>
<table id="cart"><tr><th>المنتج</th><th>الكمية</th><th>السعر</th><th>المجموع</th><th></th></tr></table>
<p style="font-size:20px">المجموع: <b id="total">0.00</b> {{ cur }}</p>
<form method="post" onsubmit="document.getElementById('cartf').value=JSON.stringify(cart);if(!cart.length){alert('السلة فارغة');return false}">
<input type="hidden" name="branch" value="{{ br }}"><input type="hidden" name="cart" id="cartf">
<div class="row">{{ client_picker(None) }}</div>
<div class="row" style="margin-top:10px"><label>الدفع<select name="method">{% for k,v in METHODS.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></label>
<button class="btn">تأكيد البيع</button></div></form></div></div>
{{ new_client_box(request.path) }}
{% include "quick_product.html" %}
<script>
var P={{ prods|tojson }}, cart=[], QP_NEED_PRICE=true;
function qpDone(p,existed){if(!P.find(x=>x.id==p.id))P.unshift(p);add(p);var s=document.getElementById('search');s.value='';renderP('');
 if(existed)alert('هذا المنتج مسجّل من قبل، أضفناه للسلة')}
function fm(n){return (Math.round(n*100)/100).toFixed(2)}
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML}
function renderP(q){var t=document.getElementById('plist');t.querySelectorAll('tr.p').forEach(r=>r.remove());
 var L=P.filter(p=>!q||p.name.indexOf(q)>-1||(p.barcode||'')==q||(p.category||'').indexOf(q)>-1);
 document.getElementById('nores').style.display=(q&&!L.length)?'':'none';
 L.slice(0,80).forEach(function(p){
  var r=t.insertRow();r.className='p';r.innerHTML='<td><span class="itm"><svg class="ic"><use href="#i-'+p.ic+'"/></svg></span>'+esc(p.name)+'</td><td class="mut">'+esc(p.category)+'</td><td>'+fm(p.price)+'</td><td>'+
  '<span class="tag '+(p.qty<=0?'red':p.qty<=3?'amber':'')+'">'+p.qty+'</span></td><td><button class="btn sm" type="button">+</button></td>';
  r.querySelector('button').onclick=function(){add(p)}})}
function add(p){var c=cart.find(x=>x.id==p.id);if(c)c.qty++;else cart.push({id:p.id,name:p.name,qty:1,price:p.price});renderC()}
function renderC(){var t=document.getElementById('cart'),tot=0;t.querySelectorAll('tr.c').forEach(r=>r.remove());
 cart.forEach(function(c,i){tot+=c.qty*c.price;var r=t.insertRow();r.className='c';
  r.innerHTML='<td>'+esc(c.name)+'</td><td><input type="number" min="0" step="any" value="'+c.qty+'" style="width:65px"></td><td>'+
  '<input type="number" min="0" step="any" value="'+c.price+'" style="width:85px" {{ "readonly" if locked }}></td><td>'+fm(c.qty*c.price)+'</td><td><button type="button" class="btn red sm">×</button></td>';
  var ins=r.querySelectorAll('input');ins[0].onchange=function(){c.qty=parseFloat(this.value)||0;renderC()};
  ins[1].onchange=function(){c.price=parseFloat(this.value)||0;renderC()};
  r.querySelector('button').onclick=function(){cart.splice(i,1);renderC()}});
 document.getElementById('total').textContent=fm(tot)}
var s=document.getElementById('search');s.oninput=function(){renderP(s.value.trim())};
s.onkeydown=function(e){if(e.key=='Enter'){e.preventDefault();var v=s.value.trim(),p=P.find(x=>x.barcode&&x.barcode==v);
 if(p){add(p);s.value='';renderP('')}else if(v){qpShow(true,v)}}};
renderP('');
</script>{% endblock %}"""

TEMPLATES["quick_product.html"] = r"""<div id="qp" class="card" style="display:none;border:2px dashed var(--gold,#e4ab74)">
<h2>{{ ic('products') }}منتج جديد غير مسجّل</h2>
<p class="mut" style="margin-top:-6px">يُضاف إلى قائمة المنتجات مباشرة{% if cu.role!='admin' %}، والمديرة تراجعه وتقدر تعدّل سعره{% endif %}.</p>
<div class="row"><label>الاسم<input id="qp_name" style="min-width:220px"></label>
<label>سعر البيع<input id="qp_price" type="number" min="0" step="any" style="width:110px"></label>
<label>سعر الشراء<input id="qp_cost" type="number" min="0" step="any" style="width:110px"></label>
<label>الفئة<input id="qp_cat" style="width:130px" placeholder="عسل، زيوت..."></label>
<label>الباركود<input id="qp_bar" style="width:130px" placeholder="اختياري"></label>
<button type="button" class="btn gold" onclick="qpSave()">إضافة</button><button type="button" class="btn light" onclick="qpShow(false)">إلغاء</button></div>
<div id="qp_err" class="flash err" style="display:none;margin-top:8px"></div></div>
<script>
function qpShow(on,pre){var b=document.getElementById('qp');b.style.display=on?'':'none';if(on){
 document.getElementById('qp_name').value='';document.getElementById('qp_bar').value='';document.getElementById('qp_price').value='';document.getElementById('qp_cost').value='';
 if(pre){if(/^\d{6,}$/.test(pre))document.getElementById('qp_bar').value=pre;else document.getElementById('qp_name').value=pre}
 document.getElementById('qp_err').style.display='none';b.scrollIntoView({behavior:'smooth',block:'center'});document.getElementById('qp_name').focus()}}
function qpSave(){var e=document.getElementById('qp_err');var d={name:document.getElementById('qp_name').value.trim(),
 price:document.getElementById('qp_price').value,cost:document.getElementById('qp_cost').value,
 category:document.getElementById('qp_cat').value.trim(),barcode:document.getElementById('qp_bar').value.trim(),branch:'{{ br or "" }}'};
 if(!d.name){e.textContent='اكتب اسم المنتج';e.style.display='';return}
 if(QP_NEED_PRICE&&!(parseFloat(d.price)>0)){e.textContent='اكتب سعر البيع';e.style.display='';return}
 fetch('{{ url_for("product_quick") }}',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})
 .then(function(r){return r.json()}).then(function(r){if(!r.ok){e.textContent=r.error||'خطأ';e.style.display='';return}
  qpShow(false);qpDone(r.product,r.existed)}).catch(function(){e.textContent='تعذّر الحفظ';e.style.display=''})}
</script>"""

TEMPLATES["receipt.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="card" style="max-width:420px;margin:auto" id="rc">
<div style="text-align:center"><img src="{{ url_for('static', filename='logo_full.jpg') }}" alt="" style="width:110px;border-radius:10px"><h1 style="margin:6px 0 4px">{{ center }}</h1><div class="mut">{{ p.branch }}</div>
<h2 style="margin:12px 0">وصل دفع رقم {{ p.id|rid }}</h2>{% if p.cancelled %}<span class="tag red">ملغى</span>{% endif %}</div>
<table><tr><td>التاريخ</td><td>{{ p.created_at[:16] }}</td></tr>
<tr><td>الزبون</td><td>{{ p.client or '-' }}</td></tr><tr><td>النوع</td><td>{{ PAY_KINDS[p.kind] }}</td></tr>
{% if not items and not vitems %}<tr><td>البيان</td><td>{{ p.description }}</td></tr>{% endif %}</table>
{% if vitems %}<table style="margin-top:8px"><tr><th>البند</th><th>الكمية</th><th>السعر</th><th>المجموع</th></tr>
{% for i in vitems %}<tr><td>{{ i.description }}</td><td>{{ '%g'|format(i.qty) }}</td><td>{{ i.unit_price|money }}</td><td>{{ (i.qty*i.unit_price)|money }}</td></tr>{% endfor %}</table>{% endif %}
{% if items %}<table style="margin-top:8px"><tr><th>المنتج</th><th>الكمية</th><th>السعر</th><th>المجموع</th></tr>
{% for i in items %}<tr><td>{{ i.name }}</td><td>{{ '%g'|format(i.qty) }}</td><td>{{ i.unit_price|money }}</td><td>{{ (i.qty*i.unit_price)|money }}</td></tr>{% endfor %}</table>{% endif %}
<p style="font-size:20px;text-align:center;margin:14px 0">المبلغ: <b>{{ p.amount|money }} {{ cur }}</b></p>
{% if rest %}<p style="text-align:center;color:#b3261e">بقي على الزبون (دين): <b>{{ rest|money }} {{ cur }}</b></p>{% endif %}
<div class="mut" style="text-align:center">طريقة الدفع: {{ METHODS.get(p.method, p.method) }} — استلمه: {{ p.by_name or '' }}</div>
<div class="row noprint" style="justify-content:center;margin-top:14px"><button class="btn" onclick="window.print()">طباعة</button>
<a class="btn light" href="{{ url_for('reception') if can_collect else url_for('dashboard') }}">رجوع</a>
{% if cu.role=='admin' and not p.cancelled %}<form method="post" action="{{ url_for('payment_cancel', pid=p.id) }}" onsubmit="return confirm('إلغاء هذه الدفعة؟ سيُرجع المخزون إن كانت بيعًا')"><button class="btn red">إلغاء الدفعة</button></form>{% endif %}</div>
</div>{% endblock %}"""

TEMPLATES["cashbox.html"] = r"""{% extends "base.html" %}{% from "macros.html" import branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}{{ 'الصندوق المركزي — كل مدفوعات الفروع' if cu.role=='admin' else 'صندوق الفرع' }}</h1>
<div class="card"><form class="row">
<label>من<input type="date" name="from" value="{{ d1 }}"></label><label>إلى<input type="date" name="to" value="{{ d2 }}"></label>
{{ branch_filter(br) }}
<label>النوع<select name="kind"><option value="">الكل</option>{% for k,v in PAY_KINDS.items() %}<option value="{{ k }}" {{ 'selected' if kind==k }}>{{ v }}</option>{% endfor %}</select></label>
<button class="btn">عرض</button>
{% if cu.role=='admin' %}<a class="btn light" href="{{ url_for('cashbox_csv', **request.args) }}">تصدير Excel (CSV)</a>{% endif %}</form></div>
<div class="grid" style="margin-bottom:16px">
<div class="stat"><div class="l">المجموع</div><div class="n">{{ total|money }} {{ cur }}</div><div class="mut">{{ rows|rejectattr('cancelled')|list|length }} عملية</div></div>
{% if cu.role=='admin' %}<div class="stat"><div class="l">حسب الفرع</div>{% for k,v in by_branch.items() %}<div>{{ k }}: <b>{{ v|money }}</b></div>{% endfor %}</div>{% endif %}
<div class="stat"><div class="l">حسب النوع</div>{% for k,v in by_kind.items() %}<div>{{ k }}: <b>{{ v|money }}</b></div>{% endfor %}</div>
<div class="stat"><div class="l">حسب طريقة الدفع</div>{% for k,v in by_method.items() %}<div>{{ k }}: <b>{{ v|money }}</b></div>{% endfor %}</div></div>
<div class="card"><table><tr><th>الوصل</th><th>التاريخ</th>{% if cu.role=='admin' %}<th>الفرع</th>{% endif %}<th>الزبون</th><th>النوع</th><th>البيان</th><th>الدفع</th><th>استلمه</th><th>المبلغ</th></tr>
{% for p in rows %}<tr class="{{ 'cx' if p.cancelled }}"><td><a href="{{ url_for('receipt', pid=p.id) }}">{{ p.id|rid }}</a></td><td>{{ p.created_at[:16] }}</td>
{% if cu.role=='admin' %}<td>{{ p.branch }}</td>{% endif %}<td>{{ p.client or '-' }}</td><td>{{ PAY_KINDS[p.kind] }}</td><td>{{ p.description }}</td>
<td>{{ METHODS.get(p.method, p.method) }}</td><td>{{ p.by_name or '' }}</td><td><b>{{ p.amount|money }}</b></td></tr>
{% else %}<tr><td colspan="9" class="mut">لا توجد عمليات في هذه الفترة</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["products.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}المنتجات والمخزون{% if br %} — {{ branch_name(br) }}{% endif %}</h1>
{% if review %}<div class="card" style="border:2px solid var(--gold,#e4ab74)"><h2>{{ ic('alert') }}منتجات جديدة أضافها العمال ({{ review|length }})</h2>
<p class="mut">أُضيفت من شاشة البيع أو الشراء. راجع الاسم والسعر، ثم اضغط «تمت المراجعة».</p>
<table><tr><th>المنتج</th><th>سعر البيع</th><th>سعر الشراء</th><th>أضافه</th><th></th></tr>
{% for p in review %}<tr><td>{{ item_ic(p.name, 'product') }}{{ p.name }}</td><td>{{ p.price|money }}</td><td>{{ (p.cost_price or 0)|money }}</td>
<td>{{ p.by_name or '' }}<div class="mut">{{ p.by_branch or '' }}</div></td>
<td style="white-space:nowrap"><a class="btn light sm" href="{{ url_for('products', edit=p.id) }}">تعديل</a>
<form method="post" action="{{ url_for('product_reviewed', pid=p.id) }}" style="display:inline"><button class="btn sm">تمت المراجعة ✓</button></form></td></tr>{% endfor %}</table></div>{% endif %}
<div class="card"><h2>{{ 'تعديل منتج' if edit else 'منتج جديد' }}</h2>
<form method="post">{% if edit %}<input type="hidden" name="id" value="{{ edit.id }}">{% endif %}
<div class="row">
<label>الاسم<input name="name" value="{{ edit.name if edit else '' }}" required></label>
<label>الفئة<input name="category" value="{{ edit.category or '' if edit else '' }}" placeholder="أعشاب، زيوت، عسل، تجميل..." list="cats"></label>
<datalist id="cats">{% for c in rows|map(attribute='category')|unique %}{% if c %}<option value="{{ c }}">{% endif %}{% endfor %}</datalist>
<label>سعر البيع ({{ cur }})<input name="price" value="{{ '%g'|format(edit.price) if edit else '' }}" style="width:110px"></label>
<label>سعر الشراء ({{ cur }})<input name="cost_price" value="{{ '%g'|format(edit.cost_price or 0) if edit else '' }}" style="width:110px"></label>
<label>الباركود<input name="barcode" value="{{ edit.barcode or '' if edit else '' }}"></label>
<label>تاريخ انتهاء الصلاحية<input type="date" name="expiry" value="{{ edit.expiry or '' if edit else '' }}"></label>
{% if edit %}<label>الحالة<select name="active"><option value="1">نشط</option><option value="0" {{ 'selected' if not edit.active }}>موقوف</option></select></label>{% endif %}
</div>
<table style="margin-top:12px;max-width:720px"><tr><th>الفرع</th>{% if not edit %}<th>الكمية الأولية</th>{% endif %}<th>حد التنبيه (ينبّه البرنامج عندما تصل الكمية إليه)</th></tr>
{% for b in branches %}{% set st = stock.get((edit.id, b.id)) if edit else None %}<tr><td>{{ b.name }}</td>
{% if not edit %}<td><input name="qty_{{ b.id }}" style="width:90px" placeholder="0"></td>{% endif %}
<td><input name="min_{{ b.id }}" style="width:90px" value="{{ '%g'|format(st.min_qty or 0) if st else default_min }}"></td></tr>{% endfor %}</table>
<p class="row"><button class="btn">حفظ</button>{% if edit %}<a class="btn light" href="{{ url_for('products') }}">إلغاء</a>{% endif %}</p></form></div>
<div class="card"><h2>استيراد قائمة منتجات من Excel</h2>
<form method="post" action="{{ url_for('products_import') }}" enctype="multipart/form-data" class="row">
<input type="file" name="file" accept=".csv" required><button class="btn light">استيراد</button>
<a class="btn light" href="{{ url_for('products_template') }}">تحميل قائمة المنتجات (Excel)</a></form>
<p class="mut">حمّل القائمة: فيها كل المنتجات بأسعارها. اكتب أمام كل منتج الكمية الموجودة في كل فرع وحد التنبيه،
احفظها بصيغة CSV UTF-8 ثم استوردها. المنتجات الموجودة تُحدَّث (والكمية تُضاف للمخزون)، والجديدة تُضاف.</p></div>
<div class="card"><form class="row" style="margin-bottom:10px"><label>بحث<input name="q" value="{{ q }}"></label>
<label>الفرع<select name="branch"><option value="">كل الفروع</option>{% for b in branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>
<button class="btn light">عرض</button></form>
<table><tr><th>المنتج</th><th>الفئة</th><th>السعر</th><th>الشراء</th><th>الصلاحية</th>{% for b in show %}<th>{{ b.name }}<div class="mut">الكمية / الحد</div></th>{% endfor %}<th>تعديل الكمية أو الحد</th><th></th></tr>
{% for p in rows %}<tr class="{{ 'cx' if not p.active }}"><td>{{ item_ic(p.name, 'product') }}{{ p.name }}</td><td>{{ p.category or '' }}</td><td>{{ p.price|money }}</td>
<td class="mut">{{ (p.cost_price or 0)|money }}</td>
<td>{% if p.expiry %}<span class="tag {{ 'red' if p.expiry<today else 'amber' if p.expiry<=soon else '' }}">{{ p.expiry }}</span>{% endif %}</td>
{% for b in show %}{% set st = stock.get((p.id,b.id)) %}{% set q = st.qty if st else 0 %}{% set m = st.min_qty or 0 if st else 0 %}
<td><span class="tag {{ 'red' if q<=0 else 'amber' if m and q<=m }}">{{ '%g'|format(q) }}</span> <span class="mut">/ {{ '%g'|format(m) }}</span></td>{% endfor %}
<td><form method="post" action="{{ url_for('product_stock', pid=p.id) }}" style="display:inline-flex;gap:4px">
<input type="hidden" name="next" value="{{ request.full_path }}">
<select name="branch_id">{% for b in show %}<option value="{{ b.id }}">{{ b.name }}</option>{% endfor %}</select>
<input name="qty" placeholder="+10 / -2" style="width:75px" title="كمية تُضاف أو تُنقص">
<input name="min_qty" placeholder="الحد" style="width:60px" title="حد التنبيه الجديد">
<button class="btn sm">تطبيق</button></form></td>
<td><a class="btn light sm" href="?edit={{ p.id }}">تعديل</a></td></tr>
{% else %}<tr><td colspan="9" class="mut">لا توجد منتجات بعد</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["stock_alerts.html"] = r"""{% extends "base.html" %}{% block body %}
<style>@media print{.chk,.ctl{display:none!important}tr.skip{display:none}.printhead{display:block!important}main>h1{color:#000}}</style>
<h1 class="noprint">تنبيهات المخزون{% if br %} — {{ branch_name(br) }}{% endif %}</h1>
<div class="card noprint"><form class="row">
{% if cu.role=='admin' %}<label>الفرع<select name="branch"><option value="">كل الفروع</option>{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>{% endif %}
<label>النوع<select name="kind"><option value="">الكل</option><option value="low" {{ 'selected' if kind=='low' }}>كمية قاربت على النفاد</option><option value="expiry" {{ 'selected' if kind=='expiry' }}>صلاحية قريبة أو منتهية</option></select></label>
<button class="btn light">عرض</button>
<button type="button" class="btn gold" onclick="window.print()">طباعة القائمة</button>
{% if cu.role=='admin' %}<button type="button" class="btn" onclick="mkpo()">طلبية شراء من المحدد</button>{% endif %}</form>
<script>function mkpo(){var it=[],br='';document.querySelectorAll('.rowchk:checked').forEach(function(c){var tr=c.closest('tr');
var q=tr.querySelector('td input:not([type=checkbox]):not([type=hidden])');it.push(tr.dataset.pid+':'+((q&&q.value)||1));br=br||tr.dataset.br});
if(!it.length){alert('حدد منتجات');return}location='{{ url_for("purchase_new") }}?branch='+br+'&items='+it.join(',')}</script>
<p class="mut">ألغِ تحديد أي سطر لا تريده في الورقة المطبوعة، وعدّل «الكمية المطلوبة» قبل الطباعة.</p></div>
<div class="card">
<div class="printhead" style="display:none;text-align:center;margin-bottom:10px">
<img src="{{ url_for('static', filename='logo_full.jpg') }}" style="width:90px;border-radius:8px"><h2 style="margin:6px 0">{{ center }}</h2>
<div>قائمة المنتجات التي قاربت على النفاد — {{ branch_name(br) }}</div><div class="mut">{{ now }}</div></div>
<table><tr><th class="chk"><input type="checkbox" checked onclick="document.querySelectorAll('.rowchk').forEach(c=>{c.checked=this.checked;c.onchange()})"></th>
<th>المنتج</th><th>الفئة</th>{% if not br %}<th>الفرع</th>{% endif %}<th>الكمية الحالية</th><th>حد التنبيه</th><th>الصلاحية</th><th>الحالة</th><th>الكمية المطلوبة</th>{% if cu.role=='admin' %}<th class="ctl">تحكم</th>{% endif %}</tr>
{% for r in rows %}<tr data-pid="{{ r.product_id }}" data-br="{{ r.branch_id }}"><td class="chk"><input type="checkbox" class="rowchk" checked onchange="this.closest('tr').classList.toggle('skip',!this.checked)"></td>
<td>{{ item_ic(r.name, 'product') }}{{ r.name }}</td><td>{{ r.category or '' }}</td>{% if not br %}<td>{{ r.branch }}</td>{% endif %}
<td><b>{{ '%g'|format(r.qty) }}</b></td><td>{{ '%g'|format(r.min_qty) }}</td><td>{{ r.expiry or '' }}</td>
<td>{% if r.out %}<span class="tag red">نفد</span>{% elif r.low %}<span class="tag amber">قارب على النفاد</span>{% endif %}
{% if r.expired %}<span class="tag red">انتهت الصلاحية</span>{% elif r.expiring %}<span class="tag amber">صلاحية قريبة</span>{% endif %}</td>
<td><input value="{{ '%g'|format(r.suggest) if r.suggest else '' }}" style="width:70px" oninput="this.nextElementSibling.textContent=this.value"><span style="display:none"></span></td>
{% if cu.role=='admin' %}<td class="ctl"><form method="post" action="{{ url_for('product_stock', pid=r.product_id) }}" style="display:inline-flex;gap:4px">
<input type="hidden" name="branch_id" value="{{ r.branch_id }}"><input type="hidden" name="next" value="{{ request.full_path }}">
<input name="qty" placeholder="+ وصلت" style="width:70px" title="الكمية التي وصلت"><input name="min_qty" placeholder="الحد" style="width:55px" title="تغيير حد التنبيه">
<button class="btn sm">تطبيق</button></form></td>{% endif %}</tr>
{% else %}<tr><td colspan="10" class="mut">لا توجد تنبيهات. كل المخزون فوق حد التنبيه.</td></tr>{% endfor %}</table></div>
<style>@media print{td input{border:0;padding:0;width:auto!important;background:none}}</style>
{% endblock %}"""

TEMPLATES["branches.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}الفروع</h1>
<div class="card"><h2>{{ 'تعديل فرع' if edit else 'إضافة فرع جديد' }}</h2>
<form method="post">{% if edit %}<input type="hidden" name="id" value="{{ edit.id }}">{% endif %}
<div class="row">
<label>اسم الفرع<input name="name" value="{{ edit.name if edit else '' }}" placeholder="فرع ... للطب البديل" required style="width:260px"></label>
<label>العنوان<input name="address" value="{{ edit.address or '' if edit else '' }}"></label>
<label>الهاتف<input name="phone" value="{{ edit.phone or '' if edit else '' }}"></label>
{% if edit %}<label>الحالة<select name="active"><option value="1">نشط</option><option value="0" {{ 'selected' if not edit.active }}>موقوف</option></select></label>{% endif %}
</div>
<p><b>أقسام الفرع:</b>
{% for k,v in DEPTS.items() %}<label style="margin-inline-end:14px"><input type="checkbox" name="depts" value="{{ k }}" {{ 'checked' if k in edit_depts }} {{ 'checked disabled' if k=='reception' }}> {{ v }}</label>{% endfor %}
<span class="mut">(الاستقبال موجود في كل فرع)</span></p>
<p><b>أقسام تحصّل المال بنفسها (في غرفتها):</b>
{% for k in ('laser','beauty') %}<label style="margin-inline-end:14px"><input type="checkbox" name="collect" value="{{ k }}" {{ 'checked' if k in edit_collect }}> {{ DEPTS[k] }}</label>{% endfor %}
<span class="mut">— القسم يستلم المال ويسجله، ويدخل الصندوق، لكنه لا يرى الصندوق.</span></p>
<button class="btn">حفظ</button>{% if edit %} <a class="btn light" href="{{ url_for('branches') }}">إلغاء</a>{% endif %}</form></div>
<div class="grid">{% for b in rows %}
<div class="stat" style="{{ 'opacity:.6' if not b.active }}"><div class="n" style="font-size:18px">{{ b.name }}</div>
<div class="mut">{{ b.address or '' }} {{ b.phone or '' }}</div>
{% if last_sync.get(b.id|string) %}<div class="mut">آخر مزامنة من حاسوب الفرع: {{ last_sync[b.id|string] }}</div>{% endif %}
<p>{% for k in depts.get(b.id, []) %}<span class="tag">{{ DEPTS[k] }}{% if k in collect.get(b.id, []) %} · يحصّل{% endif %}</span> {% endfor %}{% if not b.active %}<span class="tag gray">موقوف</span>{% endif %}</p>
<div class="row"><a class="btn sm" href="{{ url_for('branch_view', bid=b.id) }}">لوحة الفرع والصندوق</a>
<a class="btn light sm" href="?edit={{ b.id }}">تعديل</a></div></div>{% endfor %}</div>{% endblock %}"""

TEMPLATES["branch_view.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}{{ b.name }}</h1>
<div class="row" style="margin-bottom:14px">
<a class="btn" href="{{ url_for('view_branch', b=b.id) }}">العمل على هذا الفرع فقط</a>
<a class="btn light" href="{{ url_for('cashbox', branch=b.id) }}">صندوق الفرع (كل الفترات)</a>
<a class="btn light" href="{{ url_for('products', branch=b.id) }}">منتجات الفرع</a>
<a class="btn light" href="{{ url_for('stock_alerts_page', branch=b.id) }}">تنبيهات مخزون الفرع</a>
<a class="btn light" href="{{ url_for('appointments', branch=b.id) }}">مواعيد الفرع</a></div>
<div class="grid" style="margin-bottom:16px">
<div class="stat"><div class="l">صندوق اليوم</div><div class="n">{{ day.s|money }} {{ cur }}</div><div class="mut">{{ day.n }} عملية</div></div>
<div class="stat"><div class="l">صندوق هذا الشهر</div><div class="n">{{ month.s|money }} {{ cur }}</div>
<div class="mut">{% for k in by_kind %}{{ PAY_KINDS[k.kind] }}: {{ k.s|money }} · {% endfor %}</div></div>
<div class="stat"><div class="l">قيمة المخزون (بسعر البيع)</div><div class="n">{{ stock_value|money }} {{ cur }}</div><div class="mut">{{ stock|length }} منتج · {{ alerts|length }} تنبيه</div></div>
<div class="stat"><div class="l">الأقسام والموظفون</div><div>{% for k in depts %}<span class="tag">{{ DEPTS[k] }}</span> {% endfor %}</div>
<div class="mut">{% for u in staff %}{{ u.full_name or u.username }} ({{ ROLES[u.role] }}){{ '، ' if not loop.last }}{% else %}لا يوجد موظفون بعد{% endfor %}</div></div></div>
<div class="card"><h2>مبالغ تنتظر التحصيل ({{ pending|length }})</h2><table><tr><th>#</th><th>القسم</th><th>الزبون</th><th>البيان</th><th>المبلغ</th></tr>
{% for c in pending %}<tr><td>{{ c.id }}</td><td>{{ DEPTS[c.dept] }}</td><td>{{ c.client or '-' }}</td><td>{{ c.description }}</td><td>{{ c.amount|money }}</td></tr>
{% else %}<tr><td colspan="5" class="mut">لا شيء</td></tr>{% endfor %}</table></div>
<div class="card"><h2>عمليات الصندوق اليوم</h2><table><tr><th>الوصل</th><th>الوقت</th><th>الزبون</th><th>النوع</th><th>البيان</th><th>استلمه</th><th>المبلغ</th></tr>
{% for p in pays %}<tr class="{{ 'cx' if p.cancelled }}"><td><a href="{{ url_for('receipt', pid=p.id) }}">{{ p.id|rid }}</a></td><td>{{ p.created_at[11:16] }}</td><td>{{ p.client or '-' }}</td><td>{{ PAY_KINDS[p.kind] }}</td><td>{{ p.description }}</td><td>{{ p.by_name or '' }}</td><td>{{ p.amount|money }}</td></tr>
{% else %}<tr><td colspan="7" class="mut">لا شيء اليوم</td></tr>{% endfor %}</table></div>
<div class="card"><h2>مواعيد اليوم</h2>{% set rows = appts %}{% include "appt_table.html" %}</div>
<div class="card" id="posts"><h2>الوظائف والغرف في هذا الفرع</h2>
<p class="mut">مثال: غرفة الليزر، غرفة التجميل، الاستقبال، غرفة الحجامة... تُربط بها العمال والمواعيد.</p>
<table>
{% for p in posts %}<tr><td colspan="5" style="padding:4px 0"><form method="post" action="{{ url_for('branch_posts', bid=b.id) }}" class="row" style="align-items:center">
<input type="hidden" name="id" value="{{ p.id }}"><input name="name" value="{{ p.name }}" style="width:200px">
<select name="dept"><option value="">—</option>{% for k in depts %}<option value="{{ k }}" {{ 'selected' if p.dept==k }}>{{ DEPTS[k] }}</option>{% endfor %}</select>
<span class="tag">{{ post_counts.get(p.id, 0) }} عامل</span>
<select name="active"><option value="1">مفعّلة</option><option value="0" {{ 'selected' if not p.active }}>موقوفة</option></select>
<button class="btn sm" name="action" value="save">حفظ</button>
<button class="btn red sm" name="action" value="delete" onclick="return confirm('حذف؟')">حذف</button></form></td></tr>{% endfor %}
<tr><td colspan="5" style="padding-top:10px"><form method="post" action="{{ url_for('branch_posts', bid=b.id) }}" class="row" style="align-items:center">
<input name="name" placeholder="وظيفة أو غرفة جديدة" style="width:200px" required>
<select name="dept"><option value="">— القسم —</option>{% for k in depts %}<option value="{{ k }}">{{ DEPTS[k] }}</option>{% endfor %}</select>
<button class="btn gold sm">+ إضافة</button></form></td></tr></table></div>
<div class="card"><h2>عمال الفرع اليوم</h2>
<div class="row" style="margin-bottom:10px"><a class="btn sm" href="{{ url_for('attendance', branch=b.id) }}">تسجيل حضور اليوم</a>
<a class="btn light sm" href="{{ url_for('staff', branch=b.id) }}">قائمة العمال</a>
<a class="btn light sm" href="{{ url_for('staff_report', branch=b.id) }}">التقرير الشهري (حضور، غيابات، منح)</a></div>
<table><tr><th>العامل</th><th>الهاتف</th><th>اليوم</th><th>الدخول</th><th>أيام الشهر المحسوبة</th><th>غيابات الشهر</th><th>منح الشهر</th></tr>
{% for w in workers %}{% set ms = (msum|selectattr('e.id','equalto',w.id)|list)[0] %}<tr><td><a href="{{ url_for('employee_view', eid=w.id) }}">{{ w.name }}</a>{% if w.post %}<div class="mut">{{ w.post }}</div>{% endif %}</td><td>{{ w.phone or '' }}</td>
<td>{% if w.today_status %}<span class="tag {{ 'red' if w.today_status=='absent' else 'amber' if w.today_status in ('late','justified','sick','leave') else '' }}">{{ ATT_STATUS[w.today_status] }}</span>{% else %}<span class="mut">لم يُسجَّل</span>{% endif %}</td>
<td>{{ w.check_in or '' }}</td><td>{{ '%g'|format(ms.days) }}</td><td>{{ ms.cnt.absent }}{% if ms.cnt.justified %} <span class="mut">(+{{ ms.cnt.justified }} مبرر)</span>{% endif %}</td><td>{{ ms.plus|money }}</td></tr>
{% else %}<tr><td colspan="7" class="mut">لا يوجد عمال في هذا الفرع بعد. أضفهم من صفحة «العمال والحضور».</td></tr>{% endfor %}</table></div>
<div class="card"><h2>مخزون الفرع</h2><table><tr><th>المنتج</th><th>الفئة</th><th>السعر</th><th>الكمية</th><th>حد التنبيه</th><th>الصلاحية</th></tr>
{% for p in stock %}<tr><td>{{ item_ic(p.name, 'product') }}{{ p.name }}</td><td>{{ p.category or '' }}</td><td>{{ p.price|money }}</td>
<td><span class="tag {{ 'red' if p.qty<=0 else 'amber' if p.min_qty and p.qty<=p.min_qty }}">{{ '%g'|format(p.qty) }}</span></td><td>{{ '%g'|format(p.min_qty) }}</td><td>{{ p.expiry or '' }}</td></tr>
{% else %}<tr><td colspan="6" class="mut">لا توجد منتجات</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["services.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}الخدمات والأسعار</h1>
<div class="card"><h2>{{ 'تعديل خدمة' if edit else 'خدمة جديدة' }}</h2>
<form method="post" class="row">{% if edit %}<input type="hidden" name="id" value="{{ edit.id }}">{% endif %}
<label>الاسم<input name="name" value="{{ edit.name if edit else '' }}" required></label>
<label>النوع<select name="kind">{% for k,v in SERVICE_KINDS.items() %}<option value="{{ k }}" {{ 'selected' if edit and edit.kind==k }}>{{ v }}</option>{% endfor %}</select></label>
<label>القسم<select name="dept">{% for k,v in DEPTS.items() %}<option value="{{ k }}" {{ 'selected' if edit and edit.dept==k }}>{{ v }}</option>{% endfor %}</select></label>
<label>السعر ({{ cur }})<input name="price" value="{{ '%g'|format(edit.price) if edit else '' }}" style="width:110px"></label>
<label>المدة (دقيقة)<input name="duration" value="{{ edit.duration or 30 if edit else 30 }}" style="width:70px"></label>
<label>الفرع<select name="branch_id"><option value="">كل الفروع</option>{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if edit and edit.branch_id==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>
{% if edit %}<label>الحالة<select name="active"><option value="1">نشطة</option><option value="0" {{ 'selected' if not edit.active }}>موقوفة</option></select></label>{% endif %}
<button class="btn">حفظ</button></form></div>
<div class="card"><table><tr><th>الخدمة</th><th>النوع</th><th>القسم</th><th>الفرع</th><th>المدة</th><th>السعر</th><th></th></tr>
{% for s in rows %}<tr class="{{ 'cx' if not s.active }}"><td>{{ item_ic(s.name) }}{{ s.name }}</td><td>{{ SERVICE_KINDS[s.kind] }}</td><td>{{ DEPTS[s.dept] }}</td><td>{{ s.branch or 'كل الفروع' }}</td><td class="mut">{{ s.duration or 30 }} د</td>
<td>{{ s.price|money }}{% if not s.price %} <span class="tag amber">حدد السعر</span>{% endif %}</td><td><a class="btn light sm" href="?edit={{ s.id }}">تعديل</a></td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["users.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}المستخدمون</h1>
<div class="card"><h2>{{ 'تعديل مستخدم' if edit else 'مستخدم جديد' }}</h2>
<form method="post" class="row">{% if edit %}<input type="hidden" name="id" value="{{ edit.id }}">{% endif %}
<label>اسم الدخول<input name="username" value="{{ edit.username if edit else '' }}" {{ 'disabled' if edit else 'required' }}></label>
<label>الاسم الكامل<input name="full_name" value="{{ edit.full_name or '' if edit else '' }}"></label>
<label>الدور<select name="role">{% for k,v in ROLES.items() %}<option value="{{ k }}" {{ 'selected' if edit and edit.role==k }}>{{ v }}</option>{% endfor %}</select></label>
<label>الفرع<select name="branch_id"><option value="">—</option>{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if edit and edit.branch_id==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>
<label>كلمة المرور<input name="password" type="password" placeholder="{{ 'اتركها فارغة لعدم التغيير' if edit }}"></label>
{% if edit %}<label>الحالة<select name="active"><option value="1">نشط</option><option value="0" {{ 'selected' if not edit.active }}>موقوف</option></select></label>{% endif %}
<button class="btn">حفظ</button></form>
<p class="mut">كل مستخدم مرتبط بفرع، ولا يرى إلا عمليات فرعه. أقسام كل فرع تُحدَّد من صفحة الفروع. المدير يعمل على الحاسوب المركزي ويرى كل الفروع.</p></div>
<div class="card"><table><tr><th>اسم الدخول</th><th>الاسم</th><th>الدور</th><th>الفرع</th><th>الحالة</th><th></th></tr>
{% for u in rows %}<tr class="{{ 'cx' if not u.active }}"><td>{{ u.username }}</td><td>{{ u.full_name or '' }}</td><td>{{ ROLES[u.role] }}</td><td>{{ u.branch or 'المركزي' }}</td>
<td>{{ 'نشط' if u.active else 'موقوف' }}</td><td><a class="btn light sm" href="?edit={{ u.id }}">تعديل</a></td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["settings.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}الإعدادات</h1>
<form method="post">
<div class="card"><h2>عام</h2><div class="row">
<label>اسم المركز<input name="center_name" value="{{ s.center_name }}" style="width:300px"></label>
<label>العملة<input name="currency" value="{{ s.currency }}" style="width:80px"></label></div></div>
<div class="card"><h2>تذكير المواعيد برسائل SMS</h2>
<p><label><input type="checkbox" name="sms_enabled" value="1" {{ 'checked' if s.sms_enabled=='1' }}> تفعيل الإرسال التلقائي</label></p>
<div class="row">
<label>إرسال التذكير قبل الموعد بـ (ساعة)<input name="sms_hours_before" value="{{ s.sms_hours_before }}" style="width:80px"></label>
<label>الأقسام المعنية<span>{% for k,v in DEPTS.items() %}<label style="display:inline;color:inherit"><input type="checkbox" name="sms_depts" value="{{ k }}" {{ 'checked' if k in s.sms_depts.split(',') }}> {{ v }}</label> &nbsp;{% endfor %}</span></label></div>
<p><label>نص الرسالة<textarea name="sms_template" rows="3">{{ s.sms_template }}</textarea></label></p>
<p class="mut">المتغيرات المتاحة: {name} اسم الزبون، {center} اسم المركز، {branch} الفرع، {date} التاريخ، {time} الساعة.</p>
<h2>رسائل أخرى</h2>
<p><label><input type="checkbox" name="sms_confirm" value="1" {{ 'checked' if s.sms_confirm=='1' }}> رسالة تأكيد للزبون عند تسجيل موعده</label></p>
<p><label>نص التأكيد<textarea name="sms_confirm_template" rows="2">{{ s.sms_confirm_template }}</textarea></label></p>
<p><label><input type="checkbox" name="sms_birthday" value="1" {{ 'checked' if s.sms_birthday=='1' }}> تهنئة الزبائن بعيد ميلادهم (صباحًا)</label></p>
<p><label>نص التهنئة<textarea name="sms_birthday_template" rows="2">{{ s.sms_birthday_template }}</textarea></label></p>
<h2>بوابة الإرسال</h2>
<p class="mut">الطريقة الأسهل: هاتف أندرويد فيه شريحة (موبيليس / جازي / أوريدو) مع تطبيق «SMS Gateway for Android». ضع هنا الرابط واسم المستخدم وكلمة المرور التي يعطيك إياها التطبيق.</p>
<div class="row">
<label>رابط البوابة<input name="sms_url" value="{{ s.sms_url }}" style="width:380px" dir="ltr"></label>
<label>اسم المستخدم<input name="sms_user" value="{{ s.sms_user }}" dir="ltr"></label>
<label>كلمة المرور<input name="sms_pass" type="password" placeholder="{{ '••••• (محفوظة)' if s.sms_pass else '' }}" dir="ltr"></label></div></div>
<div class="card"><h2>تنبيهات المخزون</h2><div class="row">
<label>حد التنبيه الافتراضي للمنتجات الجديدة<input name="default_min_qty" value="{{ s.default_min_qty }}" style="width:80px"></label>
<label>التنبيه قبل انتهاء الصلاحية بـ (يوم)<input name="expiry_days" value="{{ s.expiry_days }}" style="width:80px"></label>
<label>هاتف المدير (لرسالة التنبيه)<input name="manager_phone" value="{{ s.manager_phone }}" placeholder="05xxxxxxxx"></label></div>
<p><label><input type="checkbox" name="stock_sms_enabled" value="1" {{ 'checked' if s.stock_sms_enabled=='1' }}> إرسال رسالة SMS للمدير كل صباح بالمنتجات التي قاربت على النفاد</label></p></div>
{% if not NODE %}<div class="card"><h2>ربط حاسوب فرع (العمل بدون إنترنت)</h2>
<p>مفتاح المزامنة: <code dir="ltr" style="background:#efe2cf;padding:3px 8px;border-radius:6px">{{ s.sync_key }}</code></p>
<p class="mut">ضع هذا المفتاح في ملف node.json على حاسوب استقبال الفرع (التفاصيل في اقرأني.txt).</p></div>{% endif %}
<div class="card" id="cert"><h2>نص الشهادة الافتراضي</h2>
<div class="row"><label>العنوان<input name="cert_title" value="{{ s.cert_title }}"></label><label>صفة الموقّع(ة)<input name="cert_signer" value="{{ s.cert_signer }}"></label></div>
<p><label>النص<textarea name="cert_body" rows="3">{{ s.cert_body }}</textarea></label></p>
<p><label>السطر الأخير<input name="cert_footer" value="{{ s.cert_footer }}" style="width:100%"></label></p>
<p class="mut">المتغيرات: {name} الاسم، {birth_date} تاريخ الميلاد، {course} الدورة، {start} {end} التواريخ، {hours} الساعات، {trainer} المكوّن، {center} المركز، {sayed} السيد/السيدة، {mawlud} المولود/المولودة، {tabaa} تابع/تابعت.</p></div>
<div class="card"><h2>وثيقة الموافقة</h2>
<p><label>العنوان<input name="consent_title" value="{{ s.consent_title }}" style="width:100%"></label></p>
<p><label>النص (كل سطر بند)<textarea name="consent_body" rows="9">{{ s.consent_body }}</textarea></label></p>
<p class="mut">المتغيرات: {name} الاسم، {procedure} الإجراء، {center} المركز، {birth_date}، {phone}، {date}.</p></div>
<div class="card"><h2>الأسعار</h2>
<p><label><input type="checkbox" name="staff_can_edit_prices" value="1" {{ 'checked' if s.staff_can_edit_prices=='1' }}> السماح للعمال (الاستقبال والأقسام) بتغيير السعر عند التحصيل</label></p>
<p class="mut">إذا لم يُفعَّل: الأسعار تُعدَّل من المديرة فقط في «الخدمات والأسعار» و«المنتجات»، والعمال يستعملونها كما هي.</p></div>
<div class="card"><h2>المديرة</h2><div class="row"><label>فرع المديرة (تصلها زيارات هذا الفرع في «زبائن المديرة»)<select name="director_branch"><option value="">—</option>{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if s.director_branch==b.id|string }}>{{ b.name }}</option>{% endfor %}</select></label></div></div>
<div class="card"><h2>العمال والرواتب</h2>
<p><b>طريقة الحضور:</b>
<label style="margin-inline-end:14px"><input type="radio" name="attendance_mode" value="absences" {{ 'checked' if (s.attendance_mode or 'absences')=='absences' }}> العامل حاضر تلقائيًا، نسجّل الغياب فقط (مستحسن)</label>
<label><input type="radio" name="attendance_mode" value="presence" {{ 'checked' if s.attendance_mode=='presence' }}> نسجّل الحضور كل يوم</label></p>
<p><b>أيام الراحة الأسبوعية:</b> {% set dn = ['الإثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت','الأحد'] %}
{% for i in range(7) %}<label style="margin-inline-end:10px"><input type="checkbox" name="weekly_off" value="{{ i }}" {{ 'checked' if i|string in (s.weekly_off or '').split(',') }}> {{ dn[i] }}</label>{% endfor %}</p>
<div class="row">
<label>عدد أيام العمل في الشهر (لأصحاب الراتب الشهري)<input name="work_days" value="{{ s.work_days }}" style="width:80px"></label></div>
<p><b>أيام تُدفع رغم عدم الحضور:</b> {% for k in ('justified','sick','leave','off') %}<label style="margin-inline-end:12px"><input type="checkbox" name="paid_statuses" value="{{ k }}" {{ 'checked' if k in (s.paid_statuses or '').split(',') }}> {{ ATT_STATUS[k] }}</label>{% endfor %}</p>
<p class="mut">أصحاب الأجرة اليومية: الأجرة الشهرية = (أيام الحضور + نصف الأيام × 0.5 + الأيام المدفوعة أعلاه) × أجرة اليوم.</p>
<p><label><input type="checkbox" name="deduct_absence" value="1" {{ 'checked' if s.deduct_absence=='1' }}> أصحاب الراتب الشهري: خصم الغياب غير المبرر ونصف الأيام (الراتب ÷ أيام العمل × أيام الغياب)</label></p></div>
<button class="btn gold">حفظ الإعدادات</button></form>
<div class="card" style="margin-top:16px"><h2>الختم وإمضاء المديرة (للشهادات)</h2>
<form method="post" action="{{ url_for('settings_images') }}" enctype="multipart/form-data">
<div class="grid">
<div><b>الختم</b><div style="height:110px;margin:8px 0">{% if s.stamp_img %}<img src="{{ s.stamp_img }}" style="max-height:110px">{% else %}<span class="mut">لا يوجد</span>{% endif %}</div>
<input type="file" name="stamp_img" accept="image/png,image/jpeg">{% if s.stamp_img %}<label><input type="checkbox" name="del_stamp_img" value="1"> حذف</label>{% endif %}</div>
<div><b>الإمضاء</b><div style="height:110px;margin:8px 0">{% if s.signature_img %}<img src="{{ s.signature_img }}" style="max-height:110px">{% else %}<span class="mut">لا يوجد</span>{% endif %}</div>
<input type="file" name="signature_img" accept="image/png,image/jpeg">{% if s.signature_img %}<label><input type="checkbox" name="del_signature_img" value="1"> حذف</label>{% endif %}</div></div>
<p class="mut">الأفضل صورة PNG بخلفية شفافة. تصل تلقائيًا إلى حاسوب سكيكدة.</p>
<button class="btn">حفظ الصور</button></form></div>{% endblock %}"""

TEMPLATES["sms.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}رسائل SMS</h1>
<div class="row" style="margin-bottom:12px"><a class="btn gold" href="{{ url_for('sms_campaign') }}">رسالة جماعية للزبائن</a>{% if queued %}<span class="tag amber">{{ queued }} رسالة في انتظار الإرسال</span>{% endif %}</div>
{% if not enabled %}<div class="flash err">الإرسال التلقائي غير مفعل. فعّله من <a href="{{ url_for('settings') }}">الإعدادات</a>.</div>{% endif %}
<div class="card"><h2>رسالة تجريبية</h2><form method="post" class="row"><input type="hidden" name="action" value="test">
<label>رقم الهاتف<input name="phone" placeholder="05xxxxxxxx" required></label><button class="btn">إرسال</button></form></div>
<div class="card"><h2>تذكيرات مستحقة الآن ({{ upcoming|length }})</h2>
<table><tr><th>الموعد</th><th>الفرع</th><th>القسم</th><th>الزبون</th><th>الهاتف</th><th></th></tr>
{% for a in upcoming %}<tr><td>{{ a.start_at }}</td><td>{{ a.branch }}</td><td>{{ DEPTS[a.dept] }}</td><td>{{ a.client }}</td><td>{{ a.phone }}</td>
<td><form method="post"><input type="hidden" name="action" value="send"><input type="hidden" name="aid" value="{{ a.id }}"><button class="btn sm">إرسال الآن</button></form></td></tr>
{% else %}<tr><td colspan="6" class="mut">لا توجد تذكيرات مستحقة</td></tr>{% endfor %}</table></div>
<div class="card"><h2>سجل الرسائل</h2><table><tr><th>الوقت</th><th>الزبون</th><th>الهاتف</th><th>الرسالة</th><th>الحالة</th></tr>
{% for l in log %}<tr><td>{{ l.created_at[:16] }}</td><td>{{ l.client or '' }}</td><td>{{ l.phone }}</td><td>{{ l.message }}</td>
<td>{% if l.status=='sent' %}<span class="tag">أُرسلت</span>{% elif l.status=='queued' %}<span class="tag amber">في الانتظار</span>{% else %}<span class="tag red" title="{{ l.response }}">فشل</span>{% endif %}</td></tr>
{% else %}<tr><td colspan="5" class="mut">لا شيء بعد</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["staff.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}العمال{% if br %} — {{ branch_name(br) }}{% endif %}</h1>
<div class="row" style="margin-bottom:14px">
<a class="btn" href="{{ url_for('attendance', branch=br) }}">ورقة الحضور اليومية</a>
<a class="btn light" href="{{ url_for('staff_report', branch=br) }}">التقرير الشهري والأجور</a></div>
{% if due %}<div class="card" style="border-color:#c99a5b"><h2>أجور مستحقة ({{ due|length }})</h2><table><tr><th>العامل</th><th>الفترة</th><th>يوم الأجرة</th><th></th></tr>
{% for d in due %}<tr><td>{{ d.e.name }}</td><td>{{ d.d1 }} ← {{ d.d2 }}</td><td>{% if d.late %}<span class="tag red">{{ d.due }} — حان</span>{% else %}<span class="tag amber">{{ d.due }}</span>{% endif %}</td>
<td><a class="btn gold sm" href="{{ url_for('payslip', eid=d.e.id, month=d.mm) }}">الكشف والدفع</a></td></tr>{% endfor %}</table></div>{% endif %}
{% if cu.role=='admin' %}<div class="card"><h2>{{ 'تعديل بيانات عامل' if edit else 'إضافة عامل' }}</h2>
<form method="post" class="row">{% if edit %}<input type="hidden" name="id" value="{{ edit.id }}">{% endif %}
<h2 style="width:100%;margin:4px 0 0;font-size:15px">المعلومات الشخصية</h2>
<label>الاسم واللقب<input name="name" value="{{ edit.name if edit else '' }}" required></label>
<label>رقم الهاتف<input name="phone" value="{{ edit.phone or '' if edit else '' }}" placeholder="05xxxxxxxx"></label>
<label>تاريخ الميلاد<input type="date" name="birth_date" value="{{ edit.birth_date or '' if edit else '' }}"></label>
<label>مكان الميلاد<input name="birth_place" value="{{ edit.birth_place or '' if edit else '' }}"></label>
<label>العنوان<input name="address" value="{{ edit.address or '' if edit else '' }}" style="width:240px"></label>
<label>رقم بطاقة التعريف<input name="id_card" value="{{ edit.id_card or '' if edit else '' }}"></label>
<label>الحالة العائلية<select name="marital_status">{% for v in ('','أعزب / عزباء','متزوج(ة)','مطلق(ة)','أرمل(ة)') %}<option value="{{ v }}" {{ 'selected' if edit and edit.marital_status==v }}>{{ v or '—' }}</option>{% endfor %}</select></label>
<label>عدد الأولاد<input name="children" value="{{ edit.children or '' if edit else '' }}" style="width:70px"></label>
<label>زمرة الدم<input name="blood_type" value="{{ edit.blood_type or '' if edit else '' }}" style="width:70px"></label>
<label>شخص يُتصل به عند الطوارئ<input name="emergency_contact" value="{{ edit.emergency_contact or '' if edit else '' }}" placeholder="الاسم والهاتف"></label>
<h2 style="width:100%;margin:10px 0 0;font-size:15px">الضمان الاجتماعي</h2>
<label>مؤمَّن في الضمان الاجتماعي؟<select name="social_security" onchange="document.getElementById('ssn').style.display=this.value=='1'?'':'none'">
<option value="0">لا</option><option value="1" {{ 'selected' if edit and edit.social_security }}>نعم</option></select></label>
<label id="ssn" style="{{ '' if edit and edit.social_security else 'display:none' }}">رقم الضمان الاجتماعي<input name="ss_number" value="{{ edit.ss_number or '' if edit else '' }}"></label>
<h2 style="width:100%;margin:10px 0 0;font-size:15px">العمل والأجر</h2>
<label>الفرع<select name="branch_id">{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if (edit.branch_id if edit else form_branch)==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>
<label>الوظيفة / الغرفة<select name="post_id" id="postsel"><option value="" data-b="">—</option>
{% for p in posts %}<option value="{{ p.id }}" data-b="{{ p.branch_id }}" {{ 'selected' if edit and edit.post_id==p.id }}>{{ p.name }}</option>{% endfor %}</select></label>
<script>(function(){var b=document.querySelector('select[name=branch_id]'),p=document.getElementById('postsel');
function f(){[].forEach.call(p.options,function(o){o.hidden=o.dataset.b&&o.dataset.b!=b.value;if(o.hidden&&o.selected)p.value=''})}
b.addEventListener('change',f);f()})()</script>
<label>تاريخ بداية العمل<input type="date" name="hire_date" value="{{ edit.hire_date or '' if edit else '' }}"></label>
<label>يوم استلام الأجرة (1-28)<input name="pay_day" value="{{ edit.pay_day or '' if edit else '' }}" placeholder="يوم بداية العمل" style="width:80px"></label>
<label>طريقة الأجر<select name="pay_type" onchange="document.getElementById('dw').style.display=this.value=='daily'?'':'none';document.getElementById('ms').style.display=this.value=='monthly'?'':'none'">
{% for k,v in PAY_TYPES.items() %}<option value="{{ k }}" {{ 'selected' if edit and (edit.pay_type or 'daily')==k }}>{{ v }}</option>{% endfor %}</select></label>
<label id="dw" style="{{ 'display:none' if edit and edit.pay_type=='monthly' }}">أجرة اليوم ({{ cur }})<input name="daily_wage" value="{{ '%g'|format(edit.daily_wage or 0) if edit else '' }}" style="width:100px"></label>
<label id="ms" style="{{ '' if edit and edit.pay_type=='monthly' else 'display:none' }}">الراتب الشهري ({{ cur }})<input name="base_salary" value="{{ '%g'|format(edit.base_salary) if edit else '' }}" style="width:110px"></label>
<label>ملاحظات<input name="notes" value="{{ edit.notes or '' if edit else '' }}" style="width:240px"></label>
{% if edit %}<label>الحالة<select name="active"><option value="1">يعمل</option><option value="0" {{ 'selected' if not edit.active }}>توقف عن العمل</option></select></label>{% endif %}
<button class="btn">حفظ</button>{% if edit %}<a class="btn light" href="{{ url_for('staff') }}">إلغاء</a>{% endif %}</form></div>{% endif %}
<div class="card"><table><tr><th>العامل</th>{% if not br %}<th>الفرع</th>{% endif %}<th>الوظيفة</th><th>الهاتف</th><th>السن</th><th>الضمان الاجتماعي</th><th>بداية العمل</th>{% if cu.role=='admin' %}<th>الأجر</th><th>يوم الأجرة / القادمة</th>{% endif %}<th>اليوم</th><th></th></tr>
{% for e in rows %}<tr class="{{ 'cx' if not e.active }}"><td><a href="{{ url_for('employee_view', eid=e.id) }}">{{ e.name }}</a></td>{% if not br %}<td>{{ e.branch }}</td>{% endif %}
<td>{{ e.post or '' }}</td><td>{{ e.phone or '' }}</td><td>{{ e.birth_date|age }}</td><td>{% if e.social_security %}<span class="tag">نعم</span>{% else %}<span class="tag gray">لا</span>{% endif %}</td><td>{{ e.hire_date or '' }}</td>{% if cu.role=='admin' %}<td>{% if (e.pay_type or 'daily')=='daily' %}{{ e.daily_wage|money }} <span class="mut">/ يوم</span>{% else %}{{ e.base_salary|money }} <span class="mut">/ شهر</span>{% endif %}</td>
<td>{% if e.active %}يوم {{ pay_info[e.id][0] }} · <span class="mut">{{ pay_info[e.id][1] }}</span>{% else %}<span class="tag gray">غادر {{ e.end_date or '' }}</span>{% endif %}</td>{% endif %}
<td>{% if e.today_status %}<span class="tag {{ 'red' if e.today_status=='absent' else 'amber' if e.today_status not in ('present',) else '' }}">{{ ATT_STATUS[e.today_status] }}</span>{% else %}<span class="mut">لم يُسجَّل</span>{% endif %}</td>
<td><a class="btn light sm" href="{{ url_for('employee_view', eid=e.id) }}">الملف</a>{% if cu.role=='admin' %} <a class="btn light sm" href="?edit={{ e.id }}">تعديل</a>{% endif %}</td></tr>
{% else %}<tr><td colspan="8" class="mut">لا يوجد عمال بعد</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["attendance.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}ورقة الحضور — {{ branch_name(br) }}</h1>
<div class="card noprint"><form class="row">
<label>اليوم<input type="date" name="date" value="{{ d }}"></label>
{% if cu.role=='admin' %}<label>الفرع<select name="branch">{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>{% endif %}
<button class="btn light">عرض</button></form></div>
<div class="card"><form method="post"><input type="hidden" name="date" value="{{ d }}"><input type="hidden" name="branch" value="{{ br }}">
{% if is_off %}<div class="flash err noprint">هذا يوم راحة: لا يُخصم شيء. إذا عمل أحد اليوم سجّله «حاضر» فيُضاف له يوم.</div>{% endif %}
<div class="row noprint" style="margin-bottom:10px">{% if not auto %}<button type="button" class="btn light sm" onclick="document.querySelectorAll('select.st').forEach(s=>{if(!s.value)s.value='present'})">تحديد غير المسجَّلين «حاضر»</button>{% endif %}
<button type="button" class="btn light sm" onclick="window.print()">طباعة</button></div>
{% if auto %}<p class="mut noprint">كل العمال حاضرون تلقائيًا ويأخذون أجرتهم كاملة. سجّل فقط من غاب: «غياب يوم» يُخصم يومًا، و«غياب نصف يوم» يُخصم نصف يوم. الأجرة تُحسب وحدها.</p>
{% else %}<p class="mut noprint">«نصف يوم» يُحسب نصف أجرة اليوم. الحاضر والمتأخر يومٌ كامل.</p>{% endif %}
<table><tr><th>العامل</th><th>الحالة</th><th>ساعة الدخول</th><th>ساعة الخروج</th><th>ملاحظة</th></tr>
{% for e in emps %}{% set a = att.get(e.id) %}<tr><td>{{ e.name }}{% if e.post %}<div class="mut">{{ e.post }}</div>{% endif %}</td>
<td>{% if auto %}<span class="noprint"><button type="button" class="btn red sm" onclick="this.closest('td').querySelector('select').value='absent'">غياب يوم</button>
<button type="button" class="btn sm" style="background:#9a6200" onclick="this.closest('td').querySelector('select').value='half'">نصف يوم</button>
<button type="button" class="btn light sm" onclick="this.closest('td').querySelector('select').value=''">حاضر</button></span>{% endif %}
<select name="st_{{ e.id }}" class="st"><option value="">{{ '✓ حاضر (تلقائي)' if auto else '— لم يُسجَّل —' }}</option>{% for k,v in ATT_STATUS.items() %}<option value="{{ k }}" {{ 'selected' if a and a.status==k }}>{{ v }}</option>{% endfor %}</select></td>
<td><input type="time" name="in_{{ e.id }}" value="{{ a.check_in or '' if a else '' }}"></td>
<td><input type="time" name="out_{{ e.id }}" value="{{ a.check_out or '' if a else '' }}"></td>
<td><input name="note_{{ e.id }}" value="{{ a.note or '' if a else '' }}" placeholder="سبب الغياب..."></td></tr>
{% else %}<tr><td colspan="5" class="mut">لا يوجد عمال في هذا الفرع. {% if cu.role=='admin' %}<a href="{{ url_for('staff') }}">أضف عمالًا</a>{% endif %}</td></tr>{% endfor %}</table>
{% if emps %}<p><button class="btn">حفظ الحضور</button></p>{% endif %}</form></div>{% endblock %}"""

TEMPLATES["employee.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}{{ e.name }}</h1>
<div class="card"><h2>معلومات العامل {% if cu.role=='admin' %}<a class="btn light sm noprint" href="{{ url_for('staff', edit=e.id) }}">تعديل</a>{% endif %}</h2>
<table><tr><td class="mut">الهاتف</td><td>{{ e.phone or '-' }}</td><td class="mut">الفرع / الوظيفة</td><td>{{ e.branch }}{% if e.post %} — <b>{{ e.post }}</b>{% endif %}</td></tr>
<tr><td class="mut">تاريخ الميلاد</td><td>{{ e.birth_date or '-' }}{% if e.birth_date %} ({{ e.birth_date|age }} سنة){% endif %}</td><td class="mut">مكان الميلاد</td><td>{{ e.birth_place or '-' }}</td></tr>
<tr><td class="mut">العنوان</td><td>{{ e.address or '-' }}</td><td class="mut">بطاقة التعريف</td><td>{{ e.id_card or '-' }}</td></tr>
<tr><td class="mut">الحالة العائلية</td><td>{{ e.marital_status or '-' }}{% if e.children %} — {{ e.children }} أولاد{% endif %}</td><td class="mut">زمرة الدم</td><td>{{ e.blood_type or '-' }}</td></tr>
<tr><td class="mut">الضمان الاجتماعي</td><td>{% if e.social_security %}<span class="tag">مؤمَّن</span> {{ e.ss_number or '' }}{% else %}<span class="tag gray">غير مؤمَّن</span>{% endif %}</td><td class="mut">عند الطوارئ</td><td>{{ e.emergency_contact or '-' }}</td></tr>
<tr><td class="mut">بداية العمل</td><td>{{ e.hire_date or '-' }}</td><td class="mut">الأجر</td><td>{% if cu.role=='admin' %}{% if (e.pay_type or 'daily')=='daily' %}{{ e.daily_wage|money }} {{ cur }} لليوم{% else %}{{ e.base_salary|money }} {{ cur }} شهريًا{% endif %}{% endif %}</td></tr>
{% if e.notes %}<tr><td class="mut">ملاحظات</td><td colspan="3">{{ e.notes }}</td></tr>{% endif %}</table>
<p>{% if s %}فترة الأجرة: <b>{{ s.d1 }}</b> ← <b>{{ s.d2 }}</b> · يوم الأجرة: <b>{{ s.due }}</b>{% if s.paid %} <span class="tag">دُفعت</span>{% endif %}{% endif %}
{% if e.end_date %} · <span class="tag gray">غادر العمل يوم {{ e.end_date }}{% if e.end_reason %} ({{ e.end_reason }}){% endif %}</span>{% endif %}</p>
<form class="row noprint" style="margin-top:12px"><label>الفترة التي تبدأ في شهر<input type="month" name="month" value="{{ mm }}"></label><button class="btn light">عرض</button>
{% if cu.role=='admin' %}<a class="btn red" href="{{ url_for('employee_leave', eid=e.id) }}">{{ 'مغادرة العمل نهائيًا' if e.active else 'تصفية الحساب' }}</a>{% endif %}
{% if cu.role=='admin' %}<a class="btn gold" href="{{ url_for('payslip', eid=e.id, month=mm) }}">كشف الأجرة الشهرية (طباعة)</a>{% endif %}</form></div>
{% if s %}<div class="grid" style="margin-bottom:16px">
<div class="stat"><div class="l">أيام العمل المحسوبة ({{ mm }})</div><div class="n">{{ '%g'|format(s.days) }}</div>
<div class="mut">{% if s.auto %}أيام العمل: {{ s.wdays }} − غياب: {{ '%g'|format(s.lost) }}{% if s.extra %} + عمل يوم الراحة: {{ '%g'|format(s.extra) }}{% endif %}{% else %}كامل: {{ s.cnt.present + s.cnt.late }} · نصف يوم: {{ s.cnt.half }}{% endif %}</div></div>
<div class="stat"><div class="l">الغيابات</div><div class="n">{{ s.cnt.absent }}{% if s.cnt.half %} <span style="font-size:15px">+ {{ s.cnt.half }} نصف يوم</span>{% endif %}</div><div class="mut">مبرر: {{ s.cnt.justified }} · مرضية: {{ s.cnt.sick }} · عطلة: {{ s.cnt.leave }}</div></div>
{% if cu.role=='admin' %}
<div class="stat"><div class="l">الأجرة المستحقة</div><div class="n">{{ s.gross|money }}</div><div class="mut">{% if s.ptype=='daily' %}{{ '%g'|format(s.days) }} يوم × {{ s.rate|money }}{% if s.ded %} (خُصم {{ s.ded|money }} للغياب){% endif %}{% else %}الراتب − خصم الغياب ({{ s.ded|money }}){% endif %}</div></div>
<div class="stat"><div class="l">المنح / التسبيقات</div><div class="n" style="font-size:18px"><bdi dir="ltr">+{{ s.plus|money }}</bdi> / <bdi dir="ltr">−{{ s.advance|money }}</bdi></div><div class="mut">{{ s.advances|length }} تسبيق يُقتطع هذا الشهر</div></div>
<div class="stat"><div class="l">الصافي للدفع</div><div class="n">{{ s.net|money }} {{ cur }}</div></div>{% endif %}
</div>{% endif %}
{% if cu.role=='admin' %}<div class="card noprint"><h2>تسجيل تسبيق أو منحة</h2>
<form method="post" class="row"><label>النوع<select name="kind" id="gk" onchange="document.getElementById('dmw').style.display=this.value=='advance'?'':'none'">
{% for k,v in GRANT_KINDS.items() %}<option value="{{ k }}" {{ 'selected' if k=='advance' }}>{{ v }}</option>{% endfor %}</select></label>
<label>المبلغ ({{ cur }})<input name="amount" required style="width:110px"></label>
<label>تاريخ الأخذ<input type="date" name="day" value="{{ today }}"></label>
<label id="dmw">يُقتطع من أجرة شهر<input type="month" name="deduct_month" value="{{ today[:7] }}"></label>
<label>ملاحظة<input name="note"></label><button class="btn">تسجيل</button></form>
<p class="mut">التسبيق يُقتطع تلقائيًا من أجرة الشهر المحدد ويظهر بتاريخه في كشف الأجرة المطبوع.</p></div>{% endif %}
<div class="card"><h2>التسبيقات والمنح</h2><table><tr><th>التاريخ</th><th>النوع</th><th>المبلغ</th><th>يُقتطع من شهر</th><th>ملاحظة</th>{% if cu.role=='admin' %}<th class="noprint"></th>{% endif %}</tr>
{% for g in grants %}<tr><td>{{ g.day }}</td><td><span class="tag {{ 'red' if g.kind=='advance' else '' }}">{{ GRANT_KINDS[g.kind] }}</span></td><td>{{ g.amount|money }}</td>
<td>{{ g.deduct_month if g.kind=='advance' else '' }}</td><td>{{ g.note or '' }}</td>
{% if cu.role=='admin' %}<td class="noprint"><form method="post" action="{{ url_for('grant_delete', gid=g.id) }}" onsubmit="return confirm('حذف؟')"><button class="btn red sm">حذف</button></form></td>{% endif %}</tr>
{% else %}<tr><td colspan="6" class="mut">لا شيء</td></tr>{% endfor %}</table></div>
<div class="card"><h2>سجل الحضور خلال الشهر</h2><table><tr><th>اليوم</th><th>الحالة</th><th>الدخول</th><th>الخروج</th><th>ملاحظة</th></tr>
{% for a in att %}<tr><td>{{ a.day }}</td><td><span class="tag {{ 'red' if a.status=='absent' else '' if a.status=='present' else 'amber' }}">{{ ATT_STATUS[a.status] }}</span></td>
<td>{{ a.check_in or '' }}</td><td>{{ a.check_out or '' }}</td><td>{{ a.note or '' }}</td></tr>
{% else %}<tr><td colspan="5" class="mut">لا يوجد تسجيل</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["payslip_body.html"] = r"""<div class="card slip" style="max-width:760px;margin:0 auto 18px;page-break-after:always">
<div style="display:flex;align-items:center;gap:14px;border-bottom:2px solid #e4ab74;padding-bottom:10px;margin-bottom:10px">
<img src="{{ url_for('static', filename='logo_full.jpg') }}" style="width:76px;border-radius:8px">
<div><h2 style="margin:0">{{ center }}</h2><div class="mut">{{ s.e.branch }}</div></div>
<div style="margin-inline-start:auto;text-align:left"><b>كشف الأجرة الشهرية</b><div>{{ s.d1 }} ← {{ s.d2 }}</div><div class="mut">يوم الأجرة: {{ s.due }}</div></div></div>
<table><tr><td>العامل: <b>{{ s.e.name }}</b>{% if s.e.post %} — {{ s.e.post }}{% endif %}</td><td>الضمان الاجتماعي: {{ s.e.ss_number if s.e.social_security and s.e.ss_number else ('مؤمَّن' if s.e.social_security else 'غير مؤمَّن') }}</td><td>طريقة الأجر: {{ PAY_TYPES[s.ptype] }}</td></tr></table>
<h2 style="margin-top:14px">الحضور</h2>
{% if s.auto %}<table><tr><th>أيام العمل في الشهر</th><th>غياب يوم كامل</th><th>غياب نصف يوم</th><th>غياب مبرر/مرضية/عطلة</th><th>عمل يوم الراحة</th><th>أيام محسوبة</th></tr>
<tr><td>{{ s.wdays }}</td><td>{{ s.cnt.absent }}</td><td>{{ s.cnt.half }}</td><td>{{ s.cnt.justified + s.cnt.sick + s.cnt.leave }}</td><td>{{ '%g'|format(s.extra) }}</td><td><b>{{ '%g'|format(s.days) }}</b></td></tr></table>
{% else %}<table><tr><th>حاضر</th><th>متأخر</th><th>نصف يوم</th><th>غائب</th><th>غياب مبرر</th><th>مرضية</th><th>عطلة</th><th>أيام محسوبة</th></tr>
<tr><td>{{ s.cnt.present }}</td><td>{{ s.cnt.late }}</td><td>{{ s.cnt.half }}</td><td>{{ s.cnt.absent }}</td><td>{{ s.cnt.justified }}</td><td>{{ s.cnt.sick }}</td><td>{{ s.cnt.leave }}</td><td><b>{{ '%g'|format(s.days) }}</b></td></tr></table>{% endif %}
<h2 style="margin-top:14px">الحساب</h2>
<table>
{% if s.ptype=='daily' %}<tr><td>الأجرة المستحقة: {{ '%g'|format(s.days) }} يوم × {{ s.rate|money }}</td><td class="right">{{ s.gross|money }}</td></tr>
{% else %}<tr><td>الراتب الشهري</td><td class="right">{{ s.e.base_salary|money }}</td></tr>
{% if s.ded %}<tr><td>خصم الغياب</td><td class="right"><bdi dir="ltr">−{{ s.ded|money }}</bdi></td></tr>{% endif %}{% endif %}
{% for g in s.grants %}<tr><td>{{ GRANT_KINDS[g.kind] }} ({{ g.day }}){% if g.note %} — {{ g.note }}{% endif %}</td><td class="right"><bdi dir="ltr">+{{ g.amount|money }}</bdi></td></tr>{% endfor %}
{% for g in s.advances %}<tr><td>تسبيق مأخوذ يوم {{ g.day }}{% if g.note %} — {{ g.note }}{% endif %}</td><td class="right" style="color:#b3261e"><bdi dir="ltr">−{{ g.amount|money }}</bdi></td></tr>{% endfor %}
<tr style="background:#efe2cf"><td><b>الصافي للدفع</b></td><td class="right"><b style="font-size:18px">{{ s.net|money }} {{ cur }}</b></td></tr></table>
{% if s.advances %}<p class="mut">مجموع التسبيقات المقتطعة هذا الشهر: {{ s.advance|money }} {{ cur }} ({{ s.advances|length }})</p>{% endif %}
<div style="display:flex;justify-content:space-between;margin-top:34px"><div>إمضاء المسؤول</div><div>إمضاء العامل</div></div>
<div class="mut" style="margin-top:8px">طُبع في {{ now }}</div></div>"""

TEMPLATES["payslip.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="row noprint" style="margin-bottom:12px"><button class="btn gold" onclick="window.print()">طباعة الكشف</button>
{% if s.paid %}<span class="tag">دُفعت يوم {{ s.paid.day }}: {{ s.paid.amount|money }}</span>{% else %}<form method="post" action="{{ url_for('salary_paid', eid=s.e.id) }}" class="row" onsubmit="return confirm('تسجيل دفع الأجرة كمصروف؟')"><input type="hidden" name="month" value="{{ mm }}">
<input name="amount" value="{{ '%g'|format(s.net) }}" style="width:100px"><button class="btn">تسجيل دفع الأجرة في المصاريف</button></form>{% endif %}
<a class="btn light" href="{{ url_for('employee_view', eid=s.e.id, month=mm) }}">رجوع</a></div>
{% include "payslip_body.html" %}{% endblock %}"""

TEMPLATES["payslips_all.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="row noprint" style="margin-bottom:12px"><button class="btn gold" onclick="window.print()">طباعة كل الكشوف ({{ rows|length }})</button>
<a class="btn light" href="{{ url_for('staff_report', month=mm) }}">رجوع</a></div>
{% for s in rows %}{% include "payslip_body.html" %}{% else %}<div class="card">لا يوجد عمال</div>{% endfor %}{% endblock %}"""

TEMPLATES["staff_report.html"] = r"""{% extends "base.html" %}{% block body %}
<style>@media print{.printhead{display:block!important}}</style>
<h1 class="noprint">التقرير الشهري للعمال — {{ branch_name(br) }}</h1>
<div class="card noprint"><form class="row"><label>الشهر<input type="month" name="month" value="{{ mm }}"></label>
{% if cu.role=='admin' %}<label>الفرع<select name="branch"><option value="">كل الفروع</option>{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>{% endif %}
<button class="btn light">عرض</button><button type="button" class="btn gold" onclick="window.print()">طباعة التقرير</button>
{% if show_money %}<a class="btn light" href="{{ url_for('payslips_all', month=mm, branch=br or '') }}">طباعة كشوف الأجرة لكل العمال</a>{% endif %}</form></div>
<div class="card"><div class="printhead" style="display:none;text-align:center;margin-bottom:10px">
<img src="{{ url_for('static', filename='logo_full.jpg') }}" style="width:90px;border-radius:8px"><h2 style="margin:6px 0">{{ center }}</h2>
<div>تقرير الحضور والغيابات والمنح — {{ branch_name(br) }} — شهر {{ mm }}</div><div class="mut">{{ now }}</div></div>
<table><tr><th>العامل</th>{% if not br %}<th>الفرع</th>{% endif %}<th>الفترة</th><th>حضور</th><th>نصف يوم</th><th>تأخر</th><th>غياب</th><th>غياب مبرر</th><th>مرضية / عطلة</th><th>أيام محسوبة</th>
{% if show_money %}<th>الأجر</th><th>المستحق</th><th>المنح</th><th>التسبيقات</th><th>الصافي</th><th class="noprint"></th>{% endif %}</tr>
{% for r in rows %}<tr><td><a href="{{ url_for('employee_view', eid=r.e.id, month=mm) }}">{{ r.e.name }}</a>{% if r.e.post %}<div class="mut">{{ r.e.post }}</div>{% endif %}</td>{% if not br %}<td>{{ r.e.branch }}</td>{% endif %}<td class="mut">{{ r.d1[5:] }} ← {{ r.d2[5:] }}{% if r.e.end_date %}<div>غادر {{ r.e.end_date }}</div>{% endif %}</td>
<td>{{ r.cnt.present }}</td><td>{{ r.cnt.half }}</td><td>{{ r.cnt.late }}</td><td>{% if r.cnt.absent %}<span class="tag red">{{ r.cnt.absent }}</span>{% else %}0{% endif %}</td><td>{{ r.cnt.justified }}</td><td>{{ r.cnt.sick }} / {{ r.cnt.leave }}</td><td><b>{{ '%g'|format(r.days) }}</b></td>
{% if show_money %}<td>{% if r.ptype=='daily' %}{{ r.rate|money }}<span class="mut">/يوم</span>{% else %}{{ r.e.base_salary|money }}<span class="mut">/شهر</span>{% endif %}</td><td>{{ r.gross|money }}</td><td>{{ r.plus|money }}</td><td>{{ r.advance|money }}</td><td><b>{{ r.net|money }}</b></td>
<td class="noprint"><a class="btn light sm" href="{{ url_for('payslip', eid=r.e.id, month=mm) }}">الكشف</a></td>{% endif %}</tr>
{% else %}<tr><td colspan="13" class="mut">لا يوجد عمال</td></tr>{% endfor %}
{% if show_money and rows %}<tr style="background:#efe2cf"><td colspan="{{ 8 if br else 9 }}"><b>المجموع</b></td><td>{{ '%g'|format(tot.days) }}</td><td></td><td>{{ tot.gross|money }}</td><td>{{ tot.plus|money }}</td><td>{{ tot.adv|money }}</td><td><b>{{ tot.net|money }}</b></td><td class="noprint"></td></tr>{% endif %}
</table></div>{% endblock %}"""

TEMPLATES["plans.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}خطط الحصص{% if br %} — {{ branch_name(br) }}{% endif %}</h1>
<div class="row" style="margin-bottom:14px"><a class="btn" href="{{ url_for('plan_new') }}">+ خطة حصص جديدة</a></div>
<div class="card"><form class="row"><label>بحث<input name="q" value="{{ s }}" placeholder="الزبون أو الهاتف أو الخطة"></label>
<label>الحالة<select name="status"><option value="all">الكل</option>{% for k,v in PLAN_STATUS.items() %}<option value="{{ k }}" {{ 'selected' if status==k }}>{{ v }}</option>{% endfor %}</select></label>
<button class="btn light">عرض</button></form></div>
<div class="card"><table><tr><th>الزبون</th><th>الخطة</th>{% if not br %}<th>الفرع</th>{% endif %}<th>القسم</th><th>الحصص المنجزة</th><th>الحصة القادمة</th><th>السعر</th><th>المدفوع</th><th>الباقي</th><th>الحالة</th></tr>
{% for p in rows %}{% set total = p.total_price if p.price_mode=='total' else p.sum_price %}<tr>
<td><a href="{{ url_for('client_view', cid=p.client_id) }}">{{ p.client }}</a><div class="mut">{{ p.phone or '' }}</div></td>
<td><a href="{{ url_for('plan_view', pid=p.id) }}"><b>{{ p.title }}</b></a></td>{% if not br %}<td>{{ p.branch }}</td>{% endif %}<td>{{ DEPTS[p.dept] }}</td>
<td>{{ p.done }} / {{ p.n }}</td><td>{{ p.next_at or '-' }}</td><td>{{ total|money }}</td><td>{{ p.paid|money }}</td>
<td>{% if total - p.paid > 0 %}<span class="tag amber">{{ (total - p.paid)|money }}</span>{% else %}<span class="tag">خالص</span>{% endif %}</td>
<td>{{ PLAN_STATUS[p.status] }}</td></tr>
{% else %}<tr><td colspan="10" class="mut">لا توجد خطط</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["plan_new.html"] = r"""{% extends "base.html" %}{% from "macros.html" import client_picker, new_client_box with context %}{% block body %}
<h1>{{ page_icon() }}خطة حصص جديدة (موعد بعدة جلسات)</h1>
<div class="card"><form method="post">
<div class="row">{{ client_picker(sel_client, True) }}
{% if cu.role=='admin' %}<label>الفرع<select name="branch_id" onchange="location='?branch_id='+this.value">{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>{% else %}<input type="hidden" name="branch_id" value="{{ br }}">{% endif %}
{% if cu.role in ('admin','reception') %}<label>القسم<select name="dept">{% for k in depts %}<option value="{{ k }}" {{ 'selected' if k!='reception' and loop.index==2 }}>{{ DEPTS[k] }}</option>{% endfor %}</select></label>{% endif %}
<label>الخدمة<select name="service_id"><option value="">—</option>{% for s in services %}{% if cu.role not in ('laser','beauty') or s.dept==cu.role %}<option value="{{ s.id }}">{{ s.name }}</option>{% endif %}{% endfor %}</select></label>
<label>الغرفة<select name="post_id"><option value="">—</option>{% for p in posts %}<option value="{{ p.id }}">{{ p.name }}</option>{% endfor %}</select></label>
<label>اسم الخطة<input name="title" placeholder="مثلاً: ليزر إزالة الشعر — 8 حصص" style="width:260px"></label></div>
<h2 style="margin-top:16px">الحصص والسعر</h2>
<div class="row">
<label>عدد الحصص<input name="n" type="number" min="1" max="100" value="6" style="width:80px" required></label>
<label {{ 'hidden' if locked }}>طريقة التسعير<select name="price_mode" onchange="document.getElementById('sp').style.display=this.value=='session'?'':'none';document.getElementById('tp').style.display=this.value=='total'?'':'none'">
<option value="session">سعر لكل حصة</option><option value="total">سعر إجمالي للخطة</option></select></label>
<label id="sp">سعر الحصة ({{ cur }})<input name="session_price" {% if locked %}readonly title="السعر تحدده المديرة"{% endif %} style="width:110px"></label>
<label id="tp" style="display:none" {{ 'hidden' if locked }}>السعر الإجمالي ({{ cur }})<input name="total_price" style="width:120px"></label></div>
<h2 style="margin-top:16px">المواعيد (اختياري)</h2>
<div class="row">
<label>تاريخ الحصة الأولى<input type="date" name="first_date"></label>
<label>الساعة<input type="time" name="time" value="09:00"></label>
<label>كل كم يوم حصة؟<input name="interval" type="number" min="0" value="7" style="width:80px"></label>
<label>ملاحظة<input name="notes" style="width:240px"></label></div>
<p class="mut">إن تركت التاريخ فارغًا تُنشأ الحصص بدون موعد، وتحدد تاريخ كل حصة لاحقًا. يمكنك بعدها إضافة أو حذف حصص وتغيير سعر أي حصة.</p>
<button class="btn">إنشاء الخطة</button></form></div>
{{ new_client_box(request.path) }}{% endblock %}"""

TEMPLATES["plan_view.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}{{ p.title }}</h1>
<div class="grid" style="margin-bottom:16px">
<div class="stat"><div class="l">الزبون</div><div class="n" style="font-size:18px"><a href="{{ url_for('client_view', cid=p.client_id) }}">{{ p.client }}</a></div><div class="mut">{{ p.phone or '' }} · {{ p.branch }} · {{ DEPTS[p.dept] }}{% if p.room %} · {{ p.room }}{% endif %}</div></div>
<div class="stat"><div class="l">الحصص المنجزة</div><div class="n">{{ st.done }} / {{ st.n }}</div><div class="mut">{{ PLAN_STATUS[p.status] }}</div></div>
<div class="stat"><div class="l">سعر الخطة</div><div class="n">{{ st.total|money }}</div><div class="mut">{{ 'سعر إجمالي' if p.price_mode=='total' else 'مجموع أسعار الحصص' }}{% if p.price_mode=='total' and (st.sum_price - st.total)|abs > 0.01 %} · <span style="color:#b3261e">مجموع الحصص {{ st.sum_price|money }}</span>{% endif %}</div></div>
<div class="stat"><div class="l">المدفوع / الباقي</div><div class="n" style="font-size:20px">{{ st.paid|money }} / <span style="color:{{ '#9a6200' if st.remaining>0 else 'inherit' }}">{{ st.remaining|money }}</span></div><div class="mut">{{ st.paid_n }} حصة مدفوعة من {{ st.n }}</div></div></div>

<form method="post"><button name="action" value="save" style="display:none" aria-hidden="true"></button>
<div class="card"><h2>الحصص</h2>
<table><tr><th class="noprint"><input type="checkbox" onclick="document.querySelectorAll('.sel').forEach(c=>{if(!c.disabled)c.checked=this.checked})"></th><th>الحصة</th><th>التاريخ</th><th>الساعة</th><th>الغرفة</th><th>الحالة</th><th>سعر الحصة</th><th>الدفع</th><th class="noprint"></th></tr>
{% for x in sessions %}{% set k = x.id|string %}<tr>
<td class="noprint"><input type="checkbox" class="sel" name="sel" value="{{ x.id }}" {{ 'disabled' if x.paid }} data-p="{{ x.price or 0 }}" onchange="calc()"></td>
<td><b>{{ x.session_no }}</b></td>
<td><input type="date" name="d_{{ k }}" value="{{ (x.start_at or '')[:10] }}"></td>
<td><input type="time" name="t_{{ k }}" value="{{ (x.start_at or '')[11:16] }}" style="width:105px"></td>
<td><select name="r_{{ k }}"><option value="">—</option>{% for r in posts %}<option value="{{ r.id }}" {{ 'selected' if x.post_id==r.id }}>{{ r.name }}</option>{% endfor %}</select></td>
<td><select name="s_{{ k }}">{% for kk,v in APPT_STATUS.items() %}<option value="{{ kk }}" {{ 'selected' if x.status==kk }}>{{ v }}</option>{% endfor %}</select></td>
<td>{% if x.paid %}{{ x.price|money }}<input type="hidden" name="p_{{ k }}" value="{{ x.price }}">{% else %}<input name="p_{{ k }}" {% if locked %}readonly title="السعر تحدده المديرة"{% endif %} value="{{ '%g'|format(x.price or 0) }}" style="width:90px">{% endif %}</td>
<td>{% if x.paid %}<span class="tag">مدفوعة</span> <a class="mut" href="{{ url_for('receipt', pid=x.payment_id) }}">وصل {{ x.payment_id|rid }}</a>{% elif x.pending_charge %}<span class="tag amber">عند الاستقبال</span>{% else %}<span class="tag red">غير مدفوعة</span>{% endif %}</td>
<td class="noprint">{% if not x.paid %}<button class="btn red sm" formaction="{{ url_for('session_delete', aid=x.id) }}" onclick="return confirm('حذف الحصة {{ x.session_no }}؟')">حذف</button>{% endif %}</td></tr>
{% else %}<tr><td colspan="9" class="mut">لا توجد حصص</td></tr>{% endfor %}</table>
<div class="row noprint" style="margin-top:12px"><button class="btn" name="action" value="save">حفظ التعديلات (التواريخ، الحالات، الأسعار)</button></div></div>

<div class="card noprint"><h2>الدفع</h2>
<p class="mut">حدد الحصص التي يدفعها الزبون الآن (واحدة، عدة حصص، أو كلها) ثم سجّل الدفع. المبلغ يذهب إلى صندوق الفرع والصندوق المركزي.</p>
<div class="row">
<label>المحدد: <b id="selsum">0.00</b> {{ cur }}</label>
{% if can_collect %}
<label {{ 'hidden' if locked }}>المبلغ المستلم<input name="amount" id="payamt" style="width:110px" placeholder="تلقائي"></label>
<label>الدفع<select name="method">{% for kk,v in METHODS.items() %}<option value="{{ kk }}">{{ v }}</option>{% endfor %}</select></label>
<button class="btn gold" name="action" value="pay">تسجيل دفع الحصص المحددة</button>{% endif %}
<button class="btn light" name="action" value="send">إرسال المحدد للاستقبال للتحصيل</button></div></div>
</form>

<div class="grid noprint">
<div class="card"><h2>إضافة حصص</h2><form method="post" class="row"><input type="hidden" name="action" value="add">
<label>العدد<input name="count" type="number" min="1" value="1" style="width:70px"></label>
<label>سعر الحصة<input name="price" {% if locked %}readonly title="السعر تحدده المديرة"{% endif %} value="{{ '%g'|format(sessions[-1].price or 0) if sessions else '' }}" style="width:90px"></label>
<button class="btn">إضافة</button></form></div>
{% if not locked %}<div class="card"><h2>السعر الإجمالي</h2><form method="post" class="row"><input type="hidden" name="action" value="distribute">
<label>السعر الإجمالي للخطة<input name="total_price" value="{{ '%g'|format(st.total) }}" style="width:110px"></label>
<button class="btn light">توزيعه على الحصص غير المدفوعة</button></form></div>{% endif %}
<div class="card"><h2>معلومات الخطة</h2><form method="post" class="row"><input type="hidden" name="action" value="plan">
<label>الاسم<input name="title" value="{{ p.title }}"></label>
<label>التسعير<select name="price_mode"><option value="session">مجموع أسعار الحصص</option><option value="total" {{ 'selected' if p.price_mode=='total' }}>سعر إجمالي ثابت</option></select></label>
<label>السعر الإجمالي<input name="total_price" {% if locked %}readonly title="السعر تحدده المديرة"{% endif %} value="{{ '%g'|format(p.total_price or 0) }}" style="width:100px"></label>
<label>الغرفة<select name="post_id"><option value="">—</option>{% for r in posts %}<option value="{{ r.id }}" {{ 'selected' if p.post_id==r.id }}>{{ r.name }}</option>{% endfor %}</select></label>
<label>الحالة<select name="status">{% for kk,v in PLAN_STATUS.items() %}<option value="{{ kk }}" {{ 'selected' if p.status==kk }}>{{ v }}</option>{% endfor %}</select></label>
<label>ملاحظات<input name="notes" value="{{ p.notes or '' }}"></label><button class="btn light">حفظ</button></form></div></div>
<p class="noprint"><button class="btn light" onclick="window.print()">طباعة بطاقة الخطة للزبون</button></p>
<script>function calc(){var s=0;document.querySelectorAll('.sel:checked').forEach(c=>s+=parseFloat(c.dataset.p)||0);
document.getElementById('selsum').textContent=s.toFixed(2);var a=document.getElementById('payamt');if(a)a.placeholder=s.toFixed(2)}</script>
{% endblock %}"""

TEMPLATES["visit_new.html"] = r"""{% extends "base.html" %}{% from "macros.html" import client_picker, new_client_box with context %}{% block body %}
<h1>{{ page_icon() }}استقبال زبون — زيارة جديدة</h1>
<div class="card"><form method="post">
<div class="row">{{ client_picker(sel_client, True) }}
<label>يُرسَل إلى<select name="target">{% for k,v in targets.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></label></div>
{% if sel_client %}<div class="row" style="margin-top:10px;gap:18px">
{% if sel_client.chronic %}<span class="tag red">أمراض مزمنة: {{ sel_client.chronic }}</span>{% endif %}
{% if sel_client.allergies %}<span class="tag red">حساسية: {{ sel_client.allergies }}</span>{% endif %}
{% if sel_client.medications %}<span class="tag amber">أدوية: {{ sel_client.medications }}</span>{% endif %}
<a class="btn light sm" href="{{ url_for('client_view', cid=sel_client.id) }}">تعديل معلومات الزبون</a></div>{% endif %}
<h2 style="margin-top:16px">ماذا يريد الزبون؟</h2>
<table style="max-width:640px"><tr><th>الخدمة</th><th>السعر ({{ cur }})</th></tr>
{% for i in range(3) %}<tr><td><select name="service_id" onchange="var o=this.selectedOptions[0];this.closest('tr').querySelector('input').value=o.dataset.p||''"><option value="">—</option>
{% for s in services %}<option value="{{ s.id }}" data-p="{{ '%g'|format(s.price) }}">{{ s.name }} ({{ DEPTS[s.dept] }})</option>{% endfor %}</select></td>
<td><input name="price" {% if locked %}readonly title="السعر تحدده المديرة"{% endif %} style="width:110px"></td></tr>{% endfor %}</table>
<p><label style="display:block">طلب الزبون / ملاحظة للمعالج<textarea name="request" rows="2" placeholder="مثلاً: حجامة للظهر، يشتكي من صداع..."></textarea></label></p>
<button class="btn gold">إرسال الزبون</button></form></div>
{{ new_client_box(request.path) }}{% endblock %}"""

TEMPLATES["visit_queue.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}{{ 'زبائن المديرة' if tgt=='director' else 'قائمة الانتظار' }}{% if br %} — {{ branch_name(br) }}{% endif %}</h1>
{% if not tgt %}<div class="card">لا توجد قائمة انتظار لهذا المستخدم.</div>{% else %}
<div class="card"><div class="mut noprint" style="margin-bottom:8px">تتحدث القائمة تلقائيًا كل 5 ثوانٍ.</div>
<div id="qrows">…</div></div>
<script>
var last=-1;
function load(){fetch('{{ url_for("visit_queue_rows") }}',{cache:'no-store'}).then(r=>r.text()).then(function(h){
 var box=document.getElementById('qrows');box.innerHTML=h;var n=box.querySelectorAll('tr.v').length;
 if(last>=0&&n>last){document.title='('+n+') زبون جديد';try{new AudioContext().resume()}catch(e){}}
 last=n}).catch(function(){})}
load();setInterval(load,5000);
</script>{% endif %}{% endblock %}"""

TEMPLATES["visit_queue_rows.html"] = r"""<table><tr><th>#</th><th>الوصول</th><th>الزبون</th><th>السن</th><th>طلبه</th><th>تنبيه صحي</th><th>الحالة</th><th></th></tr>
{% for v in rows %}<tr class="v"><td>{{ v.id|rid }}</td><td>{{ v.created_at[11:16] }}</td>
<td><b>{{ v.client }}</b><div class="mut">{{ v.phone or '' }}{% if v.gender %} · {{ v.gender }}{% endif %}</div></td>
<td>{{ v.birth_date|age }}</td><td>{{ v.request or '' }}{% if v.n_items %} <span class="tag">{{ v.n_items }} بند</span>{% endif %}</td>
<td>{% if v.chronic %}<span class="tag red">{{ v.chronic }}</span>{% endif %}{% if v.allergies %} <span class="tag red">حساسية: {{ v.allergies }}</span>{% endif %}</td>
<td><span class="tag {{ 'amber' if v.status=='waiting' else '' }}">{{ VISIT_STATUS[v.status] }}</span></td>
<td><a class="btn sm" href="{{ url_for('visit_view', vid=v.id) }}">فتح الملف</a></td></tr>
{% else %}<tr><td colspan="8" class="mut">لا يوجد زبائن في الانتظار</td></tr>{% endfor %}</table>"""

TEMPLATES["visits.html"] = r"""{% extends "base.html" %}{% from "macros.html" import branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}الزيارات</h1>
<div class="row" style="margin-bottom:14px"><a class="btn" href="{{ url_for('visit_new') }}">+ استقبال زبون (زيارة جديدة)</a></div>
<div class="card"><form class="row"><label>اليوم<input type="date" name="date" value="{{ d }}"></label>{{ branch_filter(br) }}<button class="btn light">عرض</button></form></div>
<div class="card"><table><tr><th>#</th><th>الوقت</th>{% if not br %}<th>الفرع</th>{% endif %}<th>الزبون</th><th>عند</th><th>الطلب</th><th>المجموع</th><th>الحالة</th></tr>
{% for v in rows %}<tr><td><a href="{{ url_for('visit_view', vid=v.id) }}">{{ v.id|rid }}</a></td><td>{{ v.created_at[11:16] }}</td>{% if not br %}<td>{{ v.branch }}</td>{% endif %}
<td>{{ v.client }}</td><td>{{ VISIT_TARGETS.get(v.target, '') }}</td><td>{{ v.request or '' }}</td><td>{{ v.total|money }}</td>
<td><span class="tag {{ 'amber' if v.status in ('waiting','treating','done') else 'red' if v.status=='cancelled' else '' }}">{{ VISIT_STATUS[v.status] }}</span></td></tr>
{% else %}<tr><td colspan="8" class="mut">لا توجد زيارات</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["visit_view.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}ملف الزيارة رقم {{ v.id|rid }} — {{ v.client }}</h1>
<div class="grid" style="margin-bottom:16px">
<div class="stat"><div class="l">الزبون</div><div class="n" style="font-size:18px"><a href="{{ url_for('client_view', cid=v.client_id) }}">{{ v.client }}</a></div>
<div class="mut">{{ v.phone or '' }}{% if v.birth_date %} · {{ v.birth_date|age }} سنة{% endif %}{% if v.gender %} · {{ v.gender }}{% endif %}{% if v.address %} · {{ v.address }}{% endif %}</div></div>
<div class="stat" style="border-top-color:#c0392b"><div class="l">المعلومات الصحية</div>
<div>أمراض مزمنة: <b>{{ v.chronic or 'لا يوجد' }}</b></div><div>حساسية: <b>{{ v.allergies or 'لا يوجد' }}</b></div><div>أدوية: <b>{{ v.medications or 'لا يوجد' }}</b></div>
{% if v.cnotes %}<div class="mut">{{ v.cnotes }}</div>{% endif %}</div>
<div class="stat"><div class="l">طلب الزبون عند الاستقبال</div><div>{{ v.request or '-' }}</div>
<div class="mut">{{ v.created_at[11:16] }} · {{ v.by_name or '' }} · {{ v.branch }} · عند {{ VISIT_TARGETS.get(v.target,'') }}</div></div>
<div class="stat"><div class="l">المجموع</div><div class="n">{{ total|money }} {{ cur }}</div><div><span class="tag amber">{{ VISIT_STATUS[v.status] }}</span></div></div></div>

<div class="card"><h2>ما تم تقديمه للزبون</h2>
<table><tr><th>البند</th><th>النوع</th><th>الكمية</th><th>السعر</th><th>المجموع</th><th>أُضيف</th>{% if can_edit %}<th></th>{% endif %}</tr>
{% for i in items %}<tr><td>{{ i.description }}</td><td>{{ {'service':'خدمة','product':'منتج','other':'أخرى','discount':'تخفيض'}.get(i.kind,'') }}</td><td>{{ '%g'|format(i.qty) }}</td>
<td>{{ i.unit_price|money }}</td><td><b>{{ (i.qty*i.unit_price)|money }}</b></td>
<td>{% if i.stage=='reception' %}<span class="tag gray">طلب الاستقبال</span>{% else %}<span class="tag">إضافة أثناء العلاج</span>{% endif %} <span class="mut">{{ i.by_name or '' }}</span></td>
{% if can_edit %}<td><form method="post"><input type="hidden" name="action" value="remove"><input type="hidden" name="item_id" value="{{ i.id }}"><button class="btn red sm">حذف</button></form></td>{% endif %}</tr>
{% else %}<tr><td colspan="7" class="mut">لا شيء بعد</td></tr>{% endfor %}
<tr style="background:#efe2cf"><td colspan="4"><b>المجموع</b></td><td colspan="3"><b>{{ total|money }} {{ cur }}</b></td></tr></table></div>

{% if perm('medical') %}<div class="card"><h2>الملف الطبي للزبون</h2>
<form method="post" action="{{ url_for('client_note', cid=v.client_id) }}" class="row"><input type="hidden" name="visit_id" value="{{ v.id }}">
<label style="flex:1">ملاحظة هذه الجلسة<textarea name="note" rows="2"></textarea></label><button class="btn">حفظ الملاحظة</button>
<a class="btn light" href="{{ url_for('client_view', cid=v.client_id) }}#">الملف الكامل والصور</a>
<a class="btn light" href="{{ url_for('consent', cid=v.client_id, procedure=v.request or '') }}">وثيقة الموافقة</a></form>
{% for n in vnotes %}<div style="margin-top:6px"><span class="mut">{{ n.created_at[:10] }} · {{ n.by_name or '' }}:</span> {{ n.note }}</div>{% endfor %}</div>{% endif %}
{% if can_edit %}<div class="card"><h2>إضافة شيء قمت به</h2>
<form method="post" class="row"><input type="hidden" name="action" value="add">
<label>النوع<select name="kind" id="kind" onchange="sw()"><option value="service">خدمة</option><option value="product">منتج من المخزون</option>{% if not locked %}<option value="other">شيء آخر (أكتبه)</option><option value="discount">تخفيض (اكتب المبلغ في السعر)</option>{% endif %}</select></label>
<label id="k_service">الخدمة<select name="service_id" onchange="var o=this.selectedOptions[0];document.getElementById('pr').value=o.dataset.p||''"><option value="">—</option>{% for s in services %}<option value="{{ s.id }}" data-p="{{ '%g'|format(s.price) }}">{{ s.name }}</option>{% endfor %}</select></label>
<label id="k_product" style="display:none">المنتج<select name="product_id" onchange="var o=this.selectedOptions[0];document.getElementById('pr').value=o.dataset.p||''"><option value="">—</option>{% for p in prods %}<option value="{{ p.id }}" data-p="{{ '%g'|format(p.price) }}">{{ p.name }} (متوفر {{ '%g'|format(p.qty) }})</option>{% endfor %}</select></label>
<label>الوصف<input name="description" placeholder="مثلاً: 4 كؤوس إضافية" style="width:220px"></label>
<label>الكمية<input name="qty" value="1" style="width:60px"></label>
<label>سعر الوحدة ({{ cur }})<input name="price" id="pr" {% if locked %}readonly title="السعر تحدده المديرة"{% endif %} style="width:100px"></label>
<button class="btn">إضافة</button></form>
<p class="mut">اختر من قائمة الأسعار أو اكتب السعر بيدك. المنتجات تُخصم من مخزون الفرع تلقائيًا.</p></div>
<div class="row" style="margin-bottom:16px">
{% if can_treat and v.status=='waiting' %}<form method="post"><input type="hidden" name="action" value="start"><button class="btn light">بدء العلاج</button></form>{% endif %}
{% if can_treat %}<form method="post" onsubmit="return confirm('إنهاء العلاج وإرسال المجموع ({{ total|money|striptags }}) إلى الاستقبال؟')"><input type="hidden" name="action" value="finish"><button class="btn gold">إنهاء العلاج وإرسال المبلغ إلى الاستقبال</button></form>
{% if can_collect %}<form method="post" class="row" onsubmit="return confirm('إنهاء العلاج وتحصيل {{ total|money|striptags }} هنا؟')"><input type="hidden" name="action" value="finish"><input type="hidden" name="collect" value="1">
<select name="method">{% for k,v in METHODS.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select><button class="btn">إنهاء العلاج وتحصيل المبلغ هنا</button></form>{% endif %}{% endif %}
{% if cu.role=='admin' or perm('reception_visits') %}<form method="post" onsubmit="return confirm('إلغاء الزيارة؟')"><input type="hidden" name="action" value="cancel"><button class="btn red">إلغاء الزيارة</button></form>{% endif %}
</div>
<script>function sw(){var k=document.getElementById('kind').value;document.getElementById('k_service').style.display=k=='service'?'':'none';document.getElementById('k_product').style.display=k=='product'?'':'none'}</script>
{% endif %}{% endblock %}"""

TEMPLATES["courses.html"] = r"""{% extends "base.html" %}{% from "macros.html" import branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}الدورات التكوينية</h1>
{% if not locked %}<div class="card"><h2>دورة جديدة</h2>
<form method="post" class="row">
<label>اسم الدورة<input name="name" required style="width:260px" placeholder="مثلاً: دورة الحجامة العلاجية"></label>
{% if cu.role=='admin' %}<label>الفرع<select name="branch_id">{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if (br or 1)==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>{% endif %}
<label>السعر ({{ cur }})<input name="price" style="width:110px"></label>
<label>من<input type="date" name="start_date"></label><label>إلى<input type="date" name="end_date"></label>
<label>عدد الساعات<input name="hours" style="width:80px"></label>
<label>المكوّن(ة)<input name="trainer"></label>
<label>ملاحظات<input name="notes"></label>
<button class="btn">إنشاء الدورة</button></form></div>
{% else %}<div class="card mut">الدورات الجديدة وأسعارها تُنشئها المديرة. يمكنك تسجيل المتكونين وتحصيل المبالغ وطباعة الشهادات.</div>{% endif %}
<div class="card">{% if cu.role=='admin' %}<form class="row" style="margin-bottom:10px">{{ branch_filter(br) }}<button class="btn light">عرض</button></form>{% endif %}
<table><tr><th>الدورة</th>{% if not br %}<th>الفرع</th>{% endif %}<th>من</th><th>إلى</th><th>الساعات</th><th>المكوّن</th><th>المتكونون</th><th>السعر</th><th>الحالة</th></tr>
{% for c in rows %}<tr class="{{ 'cx' if c.status=='cancelled' }}"><td><a href="{{ url_for('course_view', cid=c.id) }}">{{ item_ic('دورة') }}<b>{{ c.name }}</b></a></td>{% if not br %}<td>{{ c.branch }}</td>{% endif %}
<td>{{ c.start_date or '' }}</td><td>{{ c.end_date or '' }}</td><td>{{ '%g'|format(c.hours) if c.hours else '' }}</td><td>{{ c.trainer or '' }}</td>
<td>{{ c.n }}</td><td>{{ c.price|money }}</td><td><span class="tag {{ 'amber' if c.status=='open' else '' }}">{{ COURSE_STATUS[c.status] }}</span></td></tr>
{% else %}<tr><td colspan="9" class="mut">لا توجد دورات بعد</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["course_view.html"] = r"""{% extends "base.html" %}{% from "macros.html" import client_picker, new_client_box with context %}{% block body %}
<h1>{{ page_icon() }}{{ c.name }}</h1>
<div class="grid" style="margin-bottom:16px">
<div class="stat"><div class="l">الدورة</div><div>{{ c.branch }}</div><div class="mut">من {{ c.start_date or '...' }} إلى {{ c.end_date or '...' }}{% if c.hours %} · {{ '%g'|format(c.hours) }} ساعة{% endif %}{% if c.trainer %} · {{ c.trainer }}{% endif %}</div>
<div><span class="tag amber">{{ COURSE_STATUS[c.status] }}</span></div></div>
<div class="stat"><div class="l">سعر الدورة</div><div class="n">{{ c.price|money }} {{ cur }}</div></div>
<div class="stat"><div class="l">المتكونون</div><div class="n">{{ rows|rejectattr('status','equalto','withdrawn')|list|length }}</div><div class="mut">أكملوا: {{ rows|selectattr('status','equalto','completed')|list|length }}</div></div>
<div class="stat"><div class="l">المحصّل / الباقي</div><div class="n" style="font-size:20px">{{ tot.paid|money }} / {{ (tot.price - tot.paid)|money }}</div></div></div>

<div class="card"><h2>تسجيل متكوّن</h2>
<form method="post" class="row"><input type="hidden" name="action" value="enroll">{{ client_picker(sel_client, True) }}
{% if not locked %}<label>السعر لهذا المتكوّن<input name="price" placeholder="{{ '%g'|format(c.price) }}" style="width:110px"></label>{% endif %}
<button class="btn">تسجيل</button></form></div>
{{ new_client_box(request.path) }}

<div class="card"><h2>المتكونون</h2>
<table><tr><th>الاسم</th><th>الهاتف</th><th>السعر</th><th>المدفوع</th><th>الباقي</th><th>دفع</th><th>الحالة</th><th>الشهادة</th></tr>
{% for t in rows %}{% set rest = t.price - t.paid %}<tr class="{{ 'cx' if t.status=='withdrawn' }}">
<td><a href="{{ url_for('client_view', cid=t.client_id) }}">{{ t.name }}</a></td><td>{{ t.phone or '' }}</td>
<td>{% if not locked %}<form method="post" style="display:inline-flex;gap:3px"><input type="hidden" name="action" value="price"><input type="hidden" name="tid" value="{{ t.id }}"><input name="price" value="{{ '%g'|format(t.price) }}" style="width:80px"><button class="btn light sm">✓</button></form>{% else %}{{ t.price|money }}{% endif %}</td>
<td>{{ t.paid|money }}</td><td>{% if rest > 0 %}<span class="tag amber">{{ rest|money }}</span>{% else %}<span class="tag">خالص</span>{% endif %}</td>
<td>{% if rest > 0 and t.status!='withdrawn' %}<form method="post" style="display:inline-flex;gap:3px"><input type="hidden" name="action" value="pay"><input type="hidden" name="tid" value="{{ t.id }}">
<input name="amount" value="{{ '%g'|format(rest) }}" style="width:85px"><select name="method">{% for k,v in METHODS.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select><button class="btn sm">دفع</button></form>{% endif %}</td>
<td><form method="post"><input type="hidden" name="action" value="status"><input type="hidden" name="tid" value="{{ t.id }}">
<select name="status" onchange="this.form.submit()">{% for k,v in TRAINEE_STATUS.items() %}<option value="{{ k }}" {{ 'selected' if t.status==k }}>{{ v }}</option>{% endfor %}</select></form></td>
<td>{% if t.status=='completed' %}<a class="btn gold sm" href="{{ url_for('certificate', tid=t.id) }}">الشهادة</a>{% if t.cert_printed_at %} <span class="mut">طُبعت</span>{% endif %}{% else %}<span class="mut">بعد إكمال الدورة</span>{% endif %}</td></tr>
{% else %}<tr><td colspan="8" class="mut">لا يوجد متكونون بعد</td></tr>{% endfor %}</table>
<p class="mut">يمكن الدفع على عدة أقساط: اكتب المبلغ المدفوع الآن. كل دفعة تدخل الصندوق بوصل.</p>
{% if c.status=='open' %}<form method="post" onsubmit="return confirm('إنهاء الدورة؟ كل المسجّلين يصبحون «أكمل الدورة»')"><input type="hidden" name="action" value="finish"><button class="btn gold">إنهاء الدورة (كل المسجّلين أكملوا)</button></form>{% endif %}</div>

{% if not locked %}<div class="card"><h2>تعديل الدورة</h2><form method="post" class="row"><input type="hidden" name="action" value="edit">
<label>الاسم<input name="name" value="{{ c.name }}" style="width:240px"></label><label>السعر<input name="price" value="{{ '%g'|format(c.price) }}" style="width:100px"></label>
<label>من<input type="date" name="start_date" value="{{ c.start_date or '' }}"></label><label>إلى<input type="date" name="end_date" value="{{ c.end_date or '' }}"></label>
<label>الساعات<input name="hours" value="{{ '%g'|format(c.hours) if c.hours else '' }}" style="width:70px"></label><label>المكوّن<input name="trainer" value="{{ c.trainer or '' }}"></label>
<label>الحالة<select name="status">{% for k,v in COURSE_STATUS.items() %}<option value="{{ k }}" {{ 'selected' if c.status==k }}>{{ v }}</option>{% endfor %}</select></label>
<label>ملاحظات<input name="notes" value="{{ c.notes or '' }}"></label><button class="btn light">حفظ</button></form></div>{% endif %}
{% endblock %}"""

TEMPLATES["certificate.html"] = r"""{% extends "base.html" %}{% block body %}
<style>
@page{size:A4 landscape;margin:0}
.cert{width:297mm;height:210mm;margin:0 auto;background:#fffdf7;position:relative;box-sizing:border-box;padding:12mm;
font-family:"Amiri","Traditional Arabic","Times New Roman",serif;color:#1f3d34}
.cert .b1{position:absolute;inset:8mm;border:3px solid #2a6153;border-radius:4px}
.cert .b2{position:absolute;inset:11mm;border:1.5px solid #c99a5b}
.cert .in{position:relative;height:100%;display:flex;flex-direction:column;align-items:center;padding:6mm 18mm;box-sizing:border-box;text-align:center}
.cert img.lg{height:30mm}
.cert .ttl{font-size:34pt;color:#2a6153;margin:3mm 0 2mm;font-weight:bold;letter-spacing:1px}
.cert .bod{font-size:17pt;line-height:2;max-width:230mm;margin:4mm auto}
.cert .ftr{font-size:12.5pt;color:#555;margin-top:2mm}
.cert .bot{margin-top:auto;width:100%;display:flex;justify-content:space-between;align-items:flex-end;font-size:13pt}
.cert .sig{position:relative;width:75mm;height:38mm;text-align:center}
.cert .sig img.st{position:absolute;left:8mm;top:4mm;height:32mm;opacity:.9}
.cert .sig img.sg{position:absolute;left:22mm;top:9mm;height:22mm}
.cert .no{position:absolute;top:2mm;left:4mm;font-size:10pt;color:#777}
[contenteditable]{outline:1px dashed #c99a5b;outline-offset:3px;border-radius:3px}
@media print{[contenteditable]{outline:none}.cert{margin:0}main{margin:0!important;padding:0!important;max-width:none}body{background:#fff!important}}
</style>
<div class="card noprint">
<div class="row" style="align-items:center">
<b>شهادة {{ t.name }} — {{ c.name }}</b>
{% if t.price - t.paid > 0 %}<span class="tag red">تنبيه: لم يُكمل الدفع (الباقي {{ (t.price - t.paid)|money }})</span>{% endif %}
{% if not stamp or not signature %}<span class="tag amber">الختم أو الإمضاء غير موجود — تضعه المديرة من الإعدادات</span>{% endif %}</div>
<p class="mut">اضغط على أي نص في الشهادة لتعديله مباشرة، ثم احفظ أو اطبع. التعديل يخص هذه الشهادة فقط.</p>
<form method="post" id="sv" class="row"><input type="hidden" name="title"><input type="hidden" name="body"><input type="hidden" name="footer">
<button class="btn" onclick="grab()">حفظ التعديلات</button>
<button type="button" class="btn gold" onclick="grab();fetch('',{method:'POST',body:new URLSearchParams({action:'printed'})});window.print()">طباعة الشهادة</button>
<button type="button" class="btn light" onclick="fs(1)">تكبير النص</button><button type="button" class="btn light" onclick="fs(-1)">تصغير النص</button>
{% if txt.custom %}<button class="btn light" name="action" value="reset" onclick="return confirm('الرجوع للنص الافتراضي؟')">النص الافتراضي</button>{% endif %}
<a class="btn light" href="{{ url_for('course_view', cid=c.id) }}">رجوع</a></form></div>
<div class="cert"><div class="b1"></div><div class="b2"></div>
<div class="in"><div class="no">رقم: <bdi dir="ltr">{{ cert_no }}</bdi></div>
<img class="lg" src="{{ url_for('static', filename='logo_full.jpg') }}" alt="">
<div style="font-size:15pt;margin-top:2mm">{{ center }}</div>
<div class="ttl" id="e_title" contenteditable="true">{{ txt.title }}</div>
<div class="bod" id="e_body" contenteditable="true">{{ txt.body }}</div>
<div class="ftr" id="e_footer" contenteditable="true">{{ txt.footer }}</div>
<div class="bot"><div contenteditable="true">حُرّر بـ {{ txt.place_date }}</div>
<div class="sig"><div contenteditable="true">{{ signer }}</div>
{% if stamp %}<img class="st" src="{{ stamp }}" alt="">{% endif %}{% if signature %}<img class="sg" src="{{ signature }}" alt="">{% endif %}</div></div></div></div>
<script>
function grab(){var f=document.getElementById('sv');f.title.value=document.getElementById('e_title').innerText.trim();
f.body.value=document.getElementById('e_body').innerText.trim();f.footer.value=document.getElementById('e_footer').innerText.trim()}
var sz=17;function fs(d){sz=Math.max(11,Math.min(26,sz+d));document.getElementById('e_body').style.fontSize=sz+'pt'}
</script>{% endblock %}"""

TEMPLATES["expenses.html"] = r"""{% extends "base.html" %}{% from "macros.html" import branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}المصاريف{% if br %} — {{ branch_name(br) }}{% endif %}</h1>
<div class="card"><h2>{{ 'إخراج مبلغ من صندوق اليوم' if worker else 'تسجيل مصروف' }}</h2><form method="post" class="row">
{% if not worker %}<label>الفرع<select name="branch_id">{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>
<label>التاريخ<input type="date" name="day" value="{{ today }}"></label>{% endif %}
<label>الفئة<select name="category">{% for c in EXPENSE_CATS %}<option>{{ c }}</option>{% endfor %}</select></label>
<label>البيان<input name="description" style="width:240px" placeholder="مثلاً: كراء شهر نوفمبر"></label>
<label>المبلغ ({{ cur }})<input name="amount" required style="width:110px"></label>
{% if not worker %}<label>الدفع<select name="method">{% for k,v in METHODS.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></label>
<label style="flex-direction:row;align-items:center;gap:4px"><input type="checkbox" name="from_cash" value="1"> خرج من صندوق</label>
<label><select name="role">{% for k,v in PLACES.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></label>{% endif %}
<button class="btn">تسجيل</button></form>{% if worker %}<p class="mut">المبلغ يخرج من صندوق اليوم ويظهر عند المديرة مع السبب.</p>{% endif %}</div>
{% if worker %}<div class="card"><h2>ما أخرجته اليوم</h2><table>{% for e in rows %}<tr><td>{{ e.category }}</td><td>{{ e.description or '' }}</td><td>{{ e.amount|money }}</td>
<td><form method="post"><input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{{ e.id }}"><button class="btn red sm">حذف</button></form></td></tr>{% else %}<tr><td class="mut">لا شيء</td></tr>{% endfor %}</table></div>{% else %}
<div class="card"><form class="row"><label>الشهر<input type="month" name="month" value="{{ mm }}"></label>{{ branch_filter(br) }}
<label>الفئة<select name="cat"><option value="">الكل</option>{% for c in EXPENSE_CATS %}<option {{ 'selected' if cat==c }}>{{ c }}</option>{% endfor %}</select></label>
<button class="btn light">عرض</button></form></div>
<div class="grid" style="margin-bottom:16px"><div class="stat"><div class="l">مجموع المصاريف ({{ mm }})</div><div class="n">{{ total|money }} {{ cur }}</div></div>
<div class="stat"><div class="l">حسب الفئة</div>{% for k,v in by_cat %}<div>{{ k }}: <b>{{ v|money }}</b></div>{% else %}<div class="mut">لا شيء</div>{% endfor %}</div></div>
<div class="card"><table><tr><th>التاريخ</th>{% if not br %}<th>الفرع</th>{% endif %}<th>الفئة</th><th>البيان</th><th>الدفع</th><th>المبلغ</th><th></th></tr>
{% for e in rows %}<tr><td>{{ e.day }}</td>{% if not br %}<td>{{ e.branch }}</td>{% endif %}<td>{{ e.category }}</td><td>{{ e.description or '' }}</td><td>{{ METHODS.get(e.method, e.method or '') }}</td><td><b>{{ e.amount|money }}</b></td>
<td><form method="post" onsubmit="return confirm('حذف المصروف؟')"><input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{{ e.id }}"><button class="btn red sm">حذف</button></form></td></tr>
{% else %}<tr><td colspan="7" class="mut">لا توجد مصاريف</td></tr>{% endfor %}</table></div>{% endif %}{% endblock %}"""

TEMPLATES["bars.html"] = r"""{% set m = (items|map(attribute=1)|max) if items else 1 %}{% for k,v in items %}
<div style="display:flex;align-items:center;gap:8px;margin:5px 0"><div style="width:150px;font-size:13px">{{ k }}</div>
<div style="flex:1;background:#efe2cf;border-radius:4px;height:18px"><div style="width:{{ (v/(m or 1)*100)|round(1) }}%;background:{{ color or '#2a6153' }};height:18px;border-radius:4px"></div></div>
<div style="width:110px;text-align:left;font-size:13px"><b>{{ v|money }}</b></div></div>{% else %}<div class="mut">لا شيء</div>{% endfor %}"""

TEMPLATES["reports.html"] = r"""{% extends "base.html" %}{% from "macros.html" import branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}التقارير{% if br %} — {{ branch_name(br) }}{% endif %}</h1>
<div class="card noprint"><form class="row"><label>الشهر<input type="month" name="month" value="{{ mm or '' }}"></label>
<span class="mut">أو</span><label>من<input type="date" name="from" value="{{ d1 if not mm else '' }}"></label><label>إلى<input type="date" name="to" value="{{ d2 if not mm else '' }}"></label>
{{ branch_filter(br) }}<button class="btn light">عرض</button><button type="button" class="btn gold" onclick="window.print()">طباعة</button></form></div>
<p class="mut">الفترة: {{ d1 }} ← {{ d2 }}</p>
<div class="grid" style="margin-bottom:16px">
<div class="stat"><div class="l">المداخيل</div><div class="n">{{ r.income|money }}</div><div class="mut">{{ r.n_pay }} عملية</div></div>
<div class="stat"><div class="l">المصاريف</div><div class="n" style="color:#b3261e">{{ r.expense|money }}</div></div>
<div class="stat" style="border-top-color:#2a6153"><div class="l">الربح الصافي (المداخيل − المصاريف)</div><div class="n" style="color:{{ '#1f4d43' if r.profit>=0 else '#b3261e' }}">{{ r.profit|money }}</div></div>
<div class="stat"><div class="l">الزبائن</div><div class="n">{{ r.served }}</div><div class="mut">جدد: {{ r.new_clients }} · ديون الزبائن الحالية: {{ r.debts|money }}</div></div></div>
<div class="card"><h2>المداخيل اليومية</h2>
<div style="display:flex;align-items:flex-end;gap:2px;height:160px;border-bottom:1px solid #e2d3bd">
{% for d,v in r.days %}<div title="{{ d }}: {{ v|money|striptags }}" style="flex:1;background:#2a6153;height:{{ (v/r.max_day*100)|round(1) }}%;min-height:{{ 1 if v else 0 }}px;border-radius:2px 2px 0 0"></div>{% endfor %}</div>
<div class="mut" style="display:flex;justify-content:space-between"><span>{{ r.days[0][0] if r.days }}</span><span>{{ r.days[-1][0] if r.days }}</span></div></div>
<div class="card"><h2>آخر 6 أشهر: المداخيل والمصاريف</h2>
{% for k,a,b in months %}<div style="display:flex;align-items:center;gap:8px;margin:6px 0"><div style="width:80px">{{ k }}</div>
<div style="flex:1"><div style="width:{{ (a/mx*100)|round(1) }}%;background:#2a6153;height:12px;border-radius:3px"></div><div style="width:{{ (b/mx*100)|round(1) }}%;background:#c0392b;height:12px;border-radius:3px;margin-top:2px"></div></div>
<div style="width:220px;font-size:13px">{{ a|money }} / <span style="color:#b3261e">{{ b|money }}</span> = <b>{{ (a-b)|money }}</b></div></div>{% endfor %}
<p class="mut"><span style="color:#2a6153">■</span> المداخيل · <span style="color:#c0392b">■</span> المصاريف</p></div>
<div class="grid">
<div class="card"><h2>المداخيل حسب القسم</h2>{% with items=r.by_dept, color=None %}{% include "bars.html" %}{% endwith %}</div>
<div class="card"><h2>حسب النوع</h2>{% with items=r.by_kind, color='#c99a5b' %}{% include "bars.html" %}{% endwith %}</div>
{% if not br %}<div class="card"><h2>حسب الفرع</h2>{% with items=r.by_branch, color=None %}{% include "bars.html" %}{% endwith %}
<h2 style="margin-top:12px">مصاريف كل فرع</h2>{% with items=r.exp_branch, color='#c0392b' %}{% include "bars.html" %}{% endwith %}</div>{% endif %}
<div class="card"><h2>المصاريف حسب الفئة</h2>{% with items=r.exp_cat, color='#c0392b' %}{% include "bars.html" %}{% endwith %}</div>
<div class="card"><h2>طرق الدفع</h2>{% with items=r.by_method, color='#c99a5b' %}{% include "bars.html" %}{% endwith %}</div></div>
<div class="card"><h2>أكثر الخدمات طلبًا</h2><table><tr><th>الخدمة</th><th>العدد</th><th>المداخيل</th></tr>
{% for s in r.top_services %}<tr><td>{{ item_ic(s.name) }}{{ s.name }}</td><td>{{ '%g'|format(s.n or 0) }}</td><td>{{ s.rev|money }}</td></tr>{% else %}<tr><td colspan="3" class="mut">لا شيء</td></tr>{% endfor %}</table></div>
<div class="card"><h2>أكثر المنتجات مبيعًا</h2><table><tr><th>المنتج</th><th>الكمية</th><th>المبيعات</th><th>الربح (البيع − الشراء)</th></tr>
{% for p in r.top_products %}<tr><td>{{ item_ic(p.name, 'product') }}{{ p.name }}</td><td>{{ '%g'|format(p.q) }}</td><td>{{ p.rev|money }}</td><td>{{ p.margin|money }}</td></tr>{% else %}<tr><td colspan="4" class="mut">لا شيء</td></tr>{% endfor %}</table>
<p class="mut">تكلفة المنتجات المباعة في الفترة: {{ r.cogs|money }} {{ cur }} (حسب سعر الشراء المسجل).</p></div>{% endblock %}"""

TEMPLATES["debts.html"] = r"""{% extends "base.html" %}{% from "macros.html" import branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}ديون الزبائن{% if br %} — {{ branch_name(br) }}{% endif %}</h1>
{% if cu.role=='admin' %}<div class="card"><form class="row">{{ branch_filter(br) }}<button class="btn light">عرض</button></form>
<div class="stat" style="margin-top:10px;max-width:320px"><div class="l">مجموع الديون</div><div class="n">{{ total|money }} {{ cur }}</div></div></div>{% endif %}
<div class="card"><p class="mut">عندما يدفع الزبون أقل من المستحق عند التحصيل، يُسجَّل الباقي هنا دينًا عليه حتى يسدده.</p>
<table><tr><th>الزبون</th><th>الهاتف</th>{% if not br %}<th>الفرع</th>{% endif %}<th>التاريخ</th><th>البيان</th><th>الدين</th><th>تسديد</th></tr>
{% for d in rows %}<tr><td><a href="{{ url_for('client_view', cid=d.client_id) }}">{{ d.client or '-' }}</a></td><td>{{ d.phone or '' }}</td>{% if not br %}<td>{{ d.branch }}</td>{% endif %}
<td>{{ d.created_at[:10] }}</td><td>{{ d.description }}</td><td><b>{{ d.amount|money }}</b></td>
<td><form method="post" style="display:inline-flex;gap:4px"><input type="hidden" name="id" value="{{ d.id }}"><input name="paid" value="{{ '%g'|format(d.amount) }}" style="width:85px">
<select name="method">{% for k,v in METHODS.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select><button class="btn sm">تسديد</button></form></td></tr>
{% else %}<tr><td colspan="7" class="mut">لا توجد ديون</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["consent.html"] = r"""{% extends "base.html" %}{% block body %}
<style>@page{size:A4 portrait;margin:14mm}
.cs{max-width:190mm;margin:0 auto;background:#fff;padding:10mm;color:#1f2a26;font-size:12.5pt;line-height:1.9}
.cs h2{text-align:center;color:#1f4d43;font-size:17pt;margin:4mm 0}
.cs table td{border:1px solid #ddd;padding:5px 8px}
.cs .sg{display:flex;justify-content:space-between;margin-top:14mm}.cs .sg div{width:45%;border-top:1px solid #333;padding-top:4px;text-align:center}
[contenteditable]{outline:1px dashed #c99a5b;outline-offset:2px}
@media print{[contenteditable]{outline:none}body{background:#fff!important}.cs{padding:0}main{margin:0!important}}</style>
<div class="card noprint"><form class="row"><label>الإجراء<input name="procedure" value="{{ proc if proc[0]!='.' else '' }}" list="procs" style="width:280px"></label>
<datalist id="procs">{% for s in services %}<option value="{{ s.name }}">{% endfor %}</datalist><button class="btn light">تحديث</button>
<button type="button" class="btn gold" onclick="fetch('',{method:'POST',body:new URLSearchParams({procedure:'{{ proc }}'})});window.print()">طباعة</button>
<a class="btn light" href="{{ url_for('client_view', cid=c.id) }}">رجوع</a></form>
<p class="mut">اضغط على أي نص لتعديله قبل الطبع. النص الافتراضي تعدّله المديرة من الإعدادات. يُنصح بمراجعة النص مع مختص قانوني.</p></div>
<div class="cs">
<div style="display:flex;align-items:center;gap:12px;border-bottom:2px solid #c99a5b;padding-bottom:6px">
<img src="{{ url_for('static', filename='logo_full.jpg') }}" style="width:60px;border-radius:6px"><div><b>{{ center }}</b></div>
<div style="margin-inline-start:auto">التاريخ: {{ vals.date }}</div></div>
<h2 contenteditable="true">{{ title }}</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:5mm"><tr><td>الاسم واللقب: <b>{{ c.name }}</b></td><td>تاريخ الميلاد: {{ vals.birth_date }}</td><td>الهاتف: {{ c.phone or '' }}</td></tr>
<tr><td colspan="3" contenteditable="true">الإجراء: <b>{{ proc }}</b></td></tr>
<tr><td colspan="3">أمراض مزمنة: {{ c.chronic or 'لا يوجد' }} — حساسية: {{ c.allergies or 'لا يوجد' }} — أدوية: {{ c.medications or 'لا يوجد' }}</td></tr></table>
<div contenteditable="true">{% for l in lines %}<div>{{ l }}</div>{% endfor %}</div>
<div class="sg"><div>إمضاء الزبون(ة)<br>(مع عبارة «قرأت وفهمت ووافقت»)</div><div>إمضاء المعالج(ة) وختم المركز</div></div>
</div>{% endblock %}"""

TEMPLATES["calendar.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}جدول الغرف الأسبوعي — {{ branch_name(br) }}</h1>
<div class="row noprint" style="margin-bottom:12px"><a class="btn light" href="?week={{ prev }}&branch={{ br }}">→ الأسبوع السابق</a>
<a class="btn light" href="?branch={{ br }}">هذا الأسبوع</a><a class="btn light" href="?week={{ next }}&branch={{ br }}">الأسبوع القادم ←</a>
{% if cu.role=='admin' %}<form class="row"><select name="branch" onchange="this.form.submit()">{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select><input type="hidden" name="week" value="{{ days[0] }}"></form>{% endif %}
<button class="btn light" onclick="window.print()">طباعة</button></div>
<div class="card" style="overflow-x:auto"><table style="min-width:900px;table-layout:fixed"><tr><th style="width:120px">الغرفة</th>
{% set dn = ['الإثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت','الأحد'] %}
{% for d in days %}<th style="{{ 'background:#e4ab74' if d.isoformat()==today }}">{{ dn[d.weekday()] }}<div class="mut">{{ d.strftime('%d/%m') }}</div></th>{% endfor %}</tr>
{% for r in rooms %}<tr><td><b>{{ r.name }}</b></td>
{% for d in days %}<td style="vertical-align:top;padding:4px">{% for a in grid.get((r.id, d.isoformat()), []) %}
<a href="{{ url_for('plan_view', pid=a.plan_id) if a.plan_id else url_for('client_view', cid=a.client_id) }}" style="display:block;text-decoration:none;margin-bottom:4px;padding:4px 6px;border-radius:6px;font-size:12px;
background:{{ '#e3efe8' if a.status=='done' else '#fbeedd' if a.status=='scheduled' else '#eee' }};color:#1f2a26;border-inline-start:3px solid {{ '#2a6153' if a.status=='done' else '#c99a5b' }}">
<b>{{ a.start_at[11:16] }}</b> {{ a.client }}<div class="mut" style="font-size:11px">{{ a.plan_title or a.service or '' }}{% if a.plan_id %} · حصة {{ a.session_no }}{% endif %} · {{ a.dur }} د</div></a>
{% endfor %}</td>{% endfor %}</tr>{% endfor %}</table></div>
<p class="mut">المدة حسب الخدمة (تُحدد في «الخدمات والأسعار»). البرنامج يمنع حجز موعدين متداخلين في نفس الغرفة.</p>{% endblock %}"""

TEMPLATES["sms_campaign.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}رسالة جماعية للزبائن</h1>
<div class="card"><form method="post">
<div class="row"><label>الفرع<select name="branch"><option value="">كل الفروع</option>{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if f.get('branch')==b.id|string }}>{{ b.name }}</option>{% endfor %}</select></label>
<label>الجنس<select name="gender"><option value="">الكل</option>{% for g in ('ذكر','أنثى') %}<option {{ 'selected' if f.get('gender')==g }}>{{ g }}</option>{% endfor %}</select></label>
<label>زاروا المركز منذ<input type="date" name="since" value="{{ f.get('since','') }}"></label>
<label>تعاملوا مع قسم<select name="dept"><option value="">الكل</option>{% for k,v in DEPTS.items() %}<option value="{{ k }}" {{ 'selected' if f.get('dept')==k }}>{{ v }}</option>{% endfor %}</select></label></div>
<p><label>نص الرسالة<textarea name="message" rows="3" placeholder="مثلاً: {name}، بمناسبة الصيف تخفيض 20% على جلسات الليزر في {center}...">{{ msg }}</textarea></label></p>
<p class="mut">{name} اسم الزبون، {center} اسم المركز. الرسالة الطويلة (أكثر من 70 حرفًا عربيًا) تُحسب أكثر من رسالة.</p>
<div class="row"><button class="btn light" name="action" value="preview">معاينة وعدّ الزبائن</button>
<button class="btn gold" name="action" value="send" onclick="return confirm('إرسال الرسالة إلى {{ targets|length }} زبون؟')">إرسال</button></div></form></div>
<div class="card"><h2>سيستقبلها {{ targets|length }} زبون</h2>{% if sample %}<p>مثال: <i>{{ sample }}</i></p>{% endif %}
<div class="mut">{% for c in targets[:60] %}{{ c.name }}{{ '، ' if not loop.last }}{% endfor %}{% if targets|length > 60 %} ...{% endif %}</div></div>{% endblock %}"""

TEMPLATES["suppliers.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}الموردون</h1>
<div class="row" style="margin-bottom:12px"><a class="btn" href="{{ url_for('purchase_new') }}">+ طلبية شراء</a><a class="btn light" href="{{ url_for('purchases') }}">كل الطلبيات</a></div>
<div class="card"><h2>{{ 'تعديل مورد' if edit else 'مورد جديد' }}</h2><form method="post" class="row">{% if edit %}<input type="hidden" name="id" value="{{ edit.id }}">{% endif %}
<label>الاسم<input name="name" value="{{ edit.name if edit else '' }}" required></label><label>الهاتف<input name="phone" value="{{ edit.phone or '' if edit else '' }}"></label>
<label>العنوان<input name="address" value="{{ edit.address or '' if edit else '' }}"></label><label>ملاحظات (ماذا يبيع)<input name="notes" value="{{ edit.notes or '' if edit else '' }}" style="width:220px"></label>
{% if edit %}<label>الحالة<select name="active"><option value="1">نشط</option><option value="0" {{ 'selected' if not edit.active }}>موقوف</option></select></label>{% endif %}
<button class="btn">حفظ</button></form></div>
<div class="card"><table><tr><th>المورد</th><th>الهاتف</th><th>ملاحظات</th><th>مجموع المشتريات</th><th>المدفوع</th><th>الباقي له</th><th></th></tr>
{% for s in rows %}<tr class="{{ 'cx' if not s.active }}"><td><span class="itm">{{ ic('truck') }}</span><b>{{ s.name }}</b></td><td>{{ s.phone or '' }}</td><td class="mut">{{ s.notes or '' }}</td>
<td>{{ s.total|money }}</td><td>{{ s.paid|money }}</td><td>{% if s.rest>0 %}<span class="tag red">{{ s.rest|money }}</span>{% else %}<span class="tag">0</span>{% endif %}</td>
<td><a class="btn light sm" href="{{ url_for('purchases', supplier=s.id) }}">الطلبيات</a> <a class="btn light sm" href="?edit={{ s.id }}">تعديل</a></td></tr>
{% else %}<tr><td colspan="7" class="mut">لا يوجد موردون</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["purchases.html"] = r"""{% extends "base.html" %}{% from "macros.html" import branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}طلبيات الشراء</h1>
<div class="row" style="margin-bottom:12px"><a class="btn" href="{{ url_for('purchase_new') }}">+ فاتورة / طلبية شراء</a>{% if cu.role=='admin' %}<a class="btn light" href="{{ url_for('suppliers') }}">الموردون</a>{% endif %}</div>
<div class="card"><form class="row" style="margin-bottom:10px">{{ branch_filter(br) }}<button class="btn light">عرض</button></form>
<table><tr><th>#</th><th>التاريخ</th><th>المورد</th>{% if not br %}<th>الفرع</th>{% endif %}<th>أدخلها</th><th>المجموع</th><th>المدفوع</th><th>الحالة</th></tr>
{% for p in rows %}<tr class="{{ 'cx' if p.status=='cancelled' }}"><td><a href="{{ url_for('purchase_view', pid=p.id) }}">{{ p.id }}</a></td><td>{{ p.day }}</td><td>{{ p.supplier or '-' }}</td>{% if not br %}<td>{{ p.branch }}</td>{% endif %}<td>{{ p.by_name or '' }}</td>
<td>{{ p.total|money }}</td><td>{{ p.paid|money }}</td><td><span class="tag {{ 'amber' if p.status=='ordered' else '' }}">{{ PURCHASE_STATUS[p.status] }}</span></td></tr>
{% else %}<tr><td colspan="8" class="mut">لا توجد طلبيات</td></tr>{% endfor %}</table></div>
{% if who %}<div class="card"><h2>{{ ic('key') }}من يقدر يدخل المشتريات؟</h2>
<p class="mut">شغّل أو أوقف لكل مكان. يصل لحاسوبه في ثوانٍ. «الدفع من الصندوق» يسمح له يسجّل المبلغ اللي خلّصه للمورد كمصروف.</p>
<style>.sw{position:relative;display:inline-block;width:46px;height:24px}.sw input{opacity:0;width:0;height:0}
.sl{position:absolute;inset:0;background:#cfc6b8;border-radius:24px;cursor:pointer;transition:.2s}
.sl:before{content:"";position:absolute;width:18px;height:18px;right:3px;top:3px;background:#fff;border-radius:50%;transition:.2s}
.sw input:checked+.sl{background:#2a6153}.sw input:checked+.sl:before{transform:translateX(-22px)}</style>
<table><tr><th>الفرع</th><th>المكان</th><th style="text-align:center">إدخال واستلام المشتريات</th><th style="text-align:center">الدفع من الصندوق (مصاريف)</th></tr>
{% for w in who %}<tr><td>{{ w.branch }}</td><td>{{ w.place }}</td>
{% for k in ('purchases','expenses') %}<td style="text-align:center"><label class="sw"><input type="checkbox" {{ 'checked' if w[k] }}
 onchange="var c=this;fetch('{{ url_for('permissions') }}',{method:'POST',headers:{'X-Requested-With':'fetch','Content-Type':'application/x-www-form-urlencoded'},body:'branch_id={{ w.branch_id }}&role={{ w.role }}&perm={{ k }}&enabled='+(c.checked?1:0)}).then(function(r){if(!r.ok)throw 0}).catch(function(){c.checked=!c.checked;alert('تعذّر الحفظ')})"><span class="sl"></span></label></td>{% endfor %}</tr>{% endfor %}</table></div>{% endif %}
{% endblock %}"""

TEMPLATES["purchase_new.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}طلبية شراء جديدة</h1>
<div class="card"><form method="post">
<div class="row"><label>المورد<select name="supplier_id"><option value="">—</option>{% for s in sups %}<option value="{{ s.id }}">{{ s.name }}</option>{% endfor %}</select></label>
{% if cu.role=='admin' %}<a class="btn light sm" href="{{ url_for('suppliers') }}">+ مورد جديد</a>
<label>للفرع<select name="branch_id">{% for b in all_branches %}<option value="{{ b.id }}" {{ 'selected' if br==b.id }}>{{ b.name }}</option>{% endfor %}</select></label>{% endif %}
<label>التاريخ<input type="date" name="day" value="{{ today }}"></label><label>ملاحظة<input name="notes"></label></div>
<table style="margin-top:12px" id="lines"><tr><th>المنتج</th><th>الكمية</th><th>سعر الشراء للوحدة</th><th></th></tr></table>
<p><button type="button" class="btn light sm" onclick="addLine()">+ سطر</button>
<button type="button" class="btn gold sm" onclick="qpShow(true)">{{ ic('products') }} منتج جديد غير مسجّل</button></p>
<button class="btn gold">حفظ الطلبية</button></form></div>
{% include "quick_product.html" %}
<script>
var P={{ prods|tojson }}, PRE={{ pre|tojson }}, QP_NEED_PRICE=false;
function qpDone(p,existed){if(!P.find(x=>x.id==p.id))P.push(p);
 var empty=[].find.call(document.querySelectorAll('#lines select'),function(s){return !s.value});
 if(empty){var o=document.createElement('option');o.value=p.id;o.dataset.c=p.cost_price||0;o.textContent=p.name;empty.appendChild(o);empty.value=p.id;empty.onchange()}
 else addLine(p.id);
 document.querySelectorAll('#lines select').forEach(function(s){if(![].some.call(s.options,function(o){return o.value==p.id})){var o=document.createElement('option');o.value=p.id;o.dataset.c=p.cost_price||0;o.textContent=p.name;s.appendChild(o)}});
 if(existed)alert('هذا المنتج مسجّل من قبل، اخترناه في الطلبية')}
function addLine(pid,q){var t=document.getElementById('lines'),r=t.insertRow();
 var opts='<option value="">—</option>'+P.map(function(p){return '<option value="'+p.id+'" data-c="'+(p.cost_price||0)+'"'+(p.id==pid?' selected':'')+'>'+p.name.replace(/</g,'&lt;')+'</option>'}).join('');
 r.innerHTML='<td><select name="product_id" style="min-width:260px">'+opts+'</select></td><td><input name="qty" style="width:80px" value="'+(q||'')+'"></td><td><input name="cost" style="width:100px"></td><td><button type="button" class="btn red sm">×</button></td>';
 var s=r.querySelector('select'),c=r.querySelector('input[name=cost]');function fc(){var o=s.selectedOptions[0];c.value=o&&o.dataset.c&&o.dataset.c!='0'?o.dataset.c:''}
 s.onchange=fc;fc();r.querySelector('button').onclick=function(){r.remove()}}
if(PRE.length){PRE.forEach(function(x){addLine(x[0],x[1])})}else{addLine();addLine();addLine()}
</script>{% endblock %}"""

TEMPLATES["purchase_view.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="row noprint" style="margin-bottom:12px"><a class="btn light" href="{{ url_for('purchases') }}">رجوع</a><button class="btn gold" onclick="window.print()">طباعة الطلبية للمورد</button></div>
<div class="card">
<div style="display:flex;align-items:center;gap:12px;border-bottom:2px solid #c99a5b;padding-bottom:8px;margin-bottom:10px">
<img src="{{ url_for('static', filename='logo_full.jpg') }}" style="width:64px;border-radius:6px"><div><b>{{ center }}</b><div class="mut">{{ p.branch }}</div></div>
<div style="margin-inline-start:auto;text-align:left"><b>طلبية شراء رقم {{ p.id }}</b><div>{{ p.day }}</div></div></div>
<p>المورد: <b>{{ p.supplier or '-' }}</b> {{ p.sphone or '' }} {{ p.saddress or '' }} — الحالة: <span class="tag amber">{{ PURCHASE_STATUS[p.status] }}</span>{% if p.notes %} — {{ p.notes }}{% endif %}</p>
<form method="post">
<table><tr><th>المنتج</th><th>الكمية</th><th>سعر الوحدة</th><th>المجموع</th>{% if p.status=='ordered' %}<th class="noprint">الكمية التي وصلت</th><th class="noprint">السعر الفعلي</th>{% endif %}</tr>
{% for i in items %}<tr><td>{{ i.name }}</td>
<td>{% if p.status=='ordered' %}<input name="q_{{ i.id }}" value="{{ '%g'|format(i.qty) }}" style="width:70px">{% else %}{{ '%g'|format(i.qty) }}{% endif %}</td>
<td>{% if p.status=='ordered' %}<input name="c_{{ i.id }}" value="{{ '%g'|format(i.unit_cost) }}" style="width:90px">{% else %}{{ i.unit_cost|money }}{% endif %}</td>
<td>{{ (i.qty*i.unit_cost)|money }}</td>
{% if p.status=='ordered' %}<td class="noprint"><input name="rq_{{ i.id }}" value="{{ '%g'|format(i.qty) }}" style="width:70px"></td><td class="noprint"><input name="rc_{{ i.id }}" value="{{ '%g'|format(i.unit_cost) }}" style="width:90px"></td>{% endif %}</tr>{% endfor %}
<tr style="background:#efe2cf"><td colspan="3"><b>المجموع</b></td><td><b>{{ total|money }} {{ cur }}</b></td>{% if p.status=='ordered' %}<td colspan="2" class="noprint"></td>{% endif %}</tr></table>
{% if p.status=='ordered' %}<div class="row noprint" style="margin-top:12px"><button class="btn light" name="action" value="edit">حفظ تعديل الطلبية</button>
{% if perm('expenses') %}<label>المدفوع للمورد الآن (من الصندوق)<input name="paid_now" style="width:100px" placeholder="0"></label>{% endif %}
<select name="method">{% for k,v in METHODS.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select>
<button class="btn gold" name="action" value="receive" onclick="return confirm('تأكيد استلام السلعة؟ تُضاف الكميات إلى مخزون الفرع')">استلام السلعة</button>
<button class="btn red" name="action" value="cancel" onclick="return confirm('إلغاء الطلبية؟')">إلغاء</button></div>
<p class="mut noprint">عند الاستلام: اكتب الكمية التي وصلت فعلًا والسعر الفعلي. تُضاف للمخزون، ويتحدّث سعر الشراء، والمدفوع يُسجَّل في المصاريف.</p>{% endif %}
</form>
{% if p.status=='received' %}<p>المدفوع للمورد: <b>{{ paid|money }}</b> — الباقي: <b style="color:{{ '#b3261e' if total-paid>0 else 'inherit' }}">{{ (total-paid)|money }}</b></p>
{% if total-paid > 0 and cu.role=='admin' %}<form method="post" class="row noprint"><input type="hidden" name="action" value="pay"><label>دفع للمورد<input name="amount" value="{{ '%g'|format(total-paid) }}" style="width:100px"></label>
<select name="method">{% for k,v in METHODS.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select><button class="btn">تسجيل الدفع</button></form>{% endif %}{% endif %}
<div class="mut" style="margin-top:20px">{{ now }}</div></div>{% endblock %}"""

TEMPLATES["permissions.html"] = r"""{% extends "base.html" %}{% block body %}
<style>.sw{position:relative;display:inline-block;width:46px;height:24px}.sw input{opacity:0;width:0;height:0}
.sl{position:absolute;inset:0;background:#cfc6b8;border-radius:24px;cursor:pointer;transition:.2s}
.sl:before{content:"";position:absolute;width:18px;height:18px;right:3px;top:3px;background:#fff;border-radius:50%;transition:.2s}
.sw input:checked+.sl{background:#2a6153}.sw input:checked+.sl:before{transform:translateX(-22px)}
td.c{text-align:center}</style>
<h1>{{ page_icon() }}صلاحيات العمال</h1>
<div class="card mut">كل مكان (استقبال، غرفة ليزر، غرفة تجميل) في كل فرع له صلاحياته. كل من يعمل في ذلك المكان يأخذها.
المهمة المغلقة تختفي من شاشة العامل ولا يستطيع فتحها. التغيير يظهر في حاسوب العامل خلال ثوانٍ (إذا كان متصلًا)، وشاشته تتحدث وحدها.
<b>الصندوق والمجاميع والتقارير والرواتب والأسعار والإعدادات للمديرة وحدها دائمًا.</b></div>
{% for d in data %}<div class="card" id="b{{ d.b.id }}"><h2>{{ d.b.name }}</h2>
<table><tr><th>المهمة</th>{% for p in d.places %}<th class="c">{{ PLACES[p] }}<div class="mut">{{ d.staff.get(p,0) }} عامل</div>
{% for dv in d.devices.get(p, []) %}<div style="font-size:12px;font-weight:normal" title="آخر اتصال: {{ dv.last_seen or 'لم يتصل بعد' }}">{{ '🟢' if dv.online else '🔴' }} {{ dv.full_name }}{% if not dv.online %} <span class="mut">(غير متصل: يأخذ التغيير عند اتصاله)</span>{% endif %}</div>{% endfor %}</th>{% endfor %}</tr>
{% for k,label,_ in PERMS %}<tr><td>{{ label }}</td>{% for p in d.places %}<td class="c">
<label class="sw"><input type="checkbox" {{ 'checked' if d.perms[p][k] }} onchange="tg(this,{{ d.b.id }},'{{ p }}','{{ k }}')"><span class="sl"></span></label></td>{% endfor %}</tr>{% endfor %}</table></div>{% endfor %}
<script>function tg(el,b,r,k){var fd=new URLSearchParams({branch_id:b,role:r,perm:k,enabled:el.checked?'1':'0'});
fetch('{{ url_for("permissions") }}',{method:'POST',body:fd,headers:{'X-Requested-With':'fetch'}}).then(r=>r.json()).then(function(d){el.checked=d.enabled==1})
.catch(function(){el.checked=!el.checked;alert('تعذر الحفظ')})}</script>{% endblock %}"""

TEMPLATES["cash_close.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}إغلاق صندوق اليوم — {{ PLACES.get(cu.role,'') }}</h1>
<div class="card" style="max-width:520px">
{% if ex %}<div class="flash ok">أُغلق الصندوق اليوم على الساعة {{ ex.closed_at[11:16] }}. يمكنك تصحيح المبلغ إن أخطأت في العدّ.</div>{% endif %}
<p>عُدّ النقود الموجودة في الصندوق الآن واكتب المبلغ. البرنامج يقارنه بما سُجّل، والمديرة ترى النتيجة.</p>
<form method="post" class="row"><label>المبلغ الموجود نقدًا ({{ cur }})<input name="counted" required style="width:150px" inputmode="decimal"></label>
<label>ملاحظة<input name="note" placeholder="اختياري"></label><button class="btn gold" onclick="return confirm('تأكيد المبلغ المعدود؟')">إغلاق الصندوق</button></form>
<p class="mut">غدًا يبدأ صندوق جديد من صفر. المدفوعات بالبطاقة أو CCP لا تُعدّ هنا.</p></div>{% endblock %}"""

TEMPLATES["cash_daily.html"] = r"""{% extends "base.html" %}{% from "macros.html" import branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}الصندوق اليومي</h1>
<div class="card noprint"><form class="row"><label>من<input type="date" name="from" value="{{ d1 }}"></label><label>إلى<input type="date" name="to" value="{{ d2 }}"></label>
{{ branch_filter(br) }}<button class="btn light">عرض</button>
<a class="btn light" href="?from={{ today }}&to={{ today }}">اليوم</a><button type="button" class="btn gold" onclick="window.print()">طباعة</button></form>
<p class="mut">كل يوم صندوق جديد يبدأ من صفر لكل مكان. «المتوقع» = النقد المحصّل − ما خرج من الصندوق. «المعدود» = ما كتبه العامل عند الإغلاق دون أن يرى المتوقع.</p></div>
<div class="grid" style="margin-bottom:16px">
<div class="stat"><div class="l">مجموع المداخيل</div><div class="n">{{ tot.total|money }}</div><div class="mut">نقدًا {{ tot.cash|money }} · بطاقة {{ tot.card|money }} · CCP {{ tot.ccp|money }}</div></div>
<div class="stat"><div class="l">خرج من الصناديق</div><div class="n" style="color:#b3261e">{{ tot.out|money }}</div></div>
<div class="stat"><div class="l">فرق العدّ في الفترة</div><div class="n" style="color:{{ '#b3261e' if tot.diff < 0 else '#1f4d43' }}">{{ tot.diff|money }}</div></div>
{% if admin_pay %}<div class="stat"><div class="l">حصّلته المديرة بنفسها</div><div class="n">{{ admin_pay|money }}</div></div>{% endif %}</div>
<div class="card"><table><tr><th>اليوم</th>{% if not br %}<th>الفرع</th>{% endif %}<th>المكان</th><th>العمليات</th><th>نقدًا</th><th>بطاقة/CCP</th><th>خرج</th><th>المتوقع في الصندوق</th><th>المعدود</th><th>الفرق</th><th>الإغلاق</th><th class="noprint"></th></tr>
{% for r in rows %}<tr><td>{{ r.day }}</td>{% if not br %}<td>{{ r.branch }}</td>{% endif %}<td>{{ PLACES.get(r.role,'') }}</td><td>{{ r.c.n }}</td>
<td>{{ r.c.cash|money }}</td><td>{{ (r.c.card + r.c.ccp)|money }}</td><td>{{ r.c.out|money }}</td><td><b>{{ r.c.expected|money }}</b></td>
<td>{% if r.cd %}{{ r.cd.counted|money }}{% else %}<span class="tag gray">لم يُعدّ</span>{% endif %}</td>
<td>{% if r.diff is not none %}{% if r.diff|abs < 0.01 %}<span class="tag">مطابق</span>{% else %}<span class="tag {{ 'red' if r.diff < 0 else 'amber' }}">{{ r.diff|money }}</span>{% endif %}{% endif %}</td>
<td class="mut">{% if r.cd %}{{ r.cd.by_name or '' }} {{ r.cd.closed_at[11:16] }}{% if r.cd.note %}<div>{{ r.cd.note }}</div>{% endif %}{% endif %}</td>
<td class="noprint"><a class="btn light sm" href="{{ url_for('cashbox', **{'from': r.day, 'to': r.day, 'branch': r.bid}) }}">التفاصيل</a></td></tr>
{% else %}<tr><td colspan="12" class="mut">لا توجد عمليات في هذه الفترة</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["audit.html"] = r"""{% extends "base.html" %}{% from "macros.html" import branch_filter with context %}{% block body %}
<h1>{{ page_icon() }}سجل العمليات</h1>
<div class="card"><form class="row"><label>من<input type="date" name="from" value="{{ d1 }}"></label><label>إلى<input type="date" name="to" value="{{ d2 }}"></label>
{{ branch_filter(br) }}<label>بحث<input name="q" value="{{ qq }}" placeholder="إلغاء، سعر، صندوق..."></label><button class="btn light">عرض</button></form></div>
<div class="card"><table><tr><th>الوقت</th><th>العامل</th><th>الفرع</th><th>العملية</th><th>التفاصيل</th></tr>
{% for a in rows %}<tr><td>{{ a.created_at[:16] }}</td><td>{{ a.full_name or a.username or '' }}<div class="mut">{{ ROLES.get(a.role,'') }}</div></td><td>{{ a.branch or '' }}</td>
<td><span class="tag {{ 'red' if 'إلغاء' in a.action or 'حذف' in a.action else 'amber' if 'سعر' in a.action or 'تخفيض' in a.action else '' }}">{{ a.action }}</span></td><td>{{ a.details }}</td></tr>
{% else %}<tr><td colspan="5" class="mut">لا شيء</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["backup.html"] = r"""{% extends "base.html" %}{% block body %}
<h1>{{ page_icon() }}النسخ الاحتياطي</h1>
<div class="grid" style="margin-bottom:16px">
<div class="stat" style="border-top-color:{{ '#c0392b' if st.warn else '#2a6153' }}"><div class="l">آخر نسخة</div><div class="n" style="font-size:20px">{{ st.last or 'لم تُصنع بعد' }}</div>
<div class="mut">{% if st.age is not none %}منذ {{ '%.0f'|format(st.age) }} ساعة{% endif %} · تلقائيًا كل {{ st.every }} ساعات</div></div>
<div class="stat"><div class="l">حجم البيانات</div><div class="n" style="font-size:20px">{{ '%.1f'|format(dbsize/1048576) }} ميغا</div><div class="mut">النسخة المضغوطة: {{ '%.1f'|format((st.size|int if st.size else 0)/1048576) }} ميغا</div></div>
<div class="stat"><div class="l">النسخ المحفوظة</div><div class="n">{{ files|length }}</div><div class="mut">{{ '%.1f'|format(total/1048576) }} ميغا في {{ st.dir }}</div></div></div>
{% if st.err %}<div class="flash err">{{ st.err }}</div>{% endif %}
{% if pending %}<div class="flash err">يوجد استرجاع في الانتظار: أعد تشغيل البرنامج لتطبيقه.</div>{% endif %}
<div class="card"><form method="post"><input type="hidden" name="action" value="now"><button class="btn gold">صنع نسخة احتياطية الآن</button></form>
<p class="mut">كل عملية في البرنامج تُحفظ فورًا. النسخة الاحتياطية نسخة كاملة إضافية في مكان آخر، تحمي من عطب الحاسوب أو القرص أو الفيروسات.
الاحتفاظ: كل النسخ لآخر 30 يومًا، ثم نسخة لكل شهر (أي نسخة لكل سنة إلى الأبد).</p></div>
<div class="card"><h2>أين تُحفظ النسخ</h2><form method="post" class="row"><input type="hidden" name="action" value="settings">
<label>المجلد الرئيسي<input name="backup_dir" value="{{ st.dir }}" dir="ltr" style="width:280px"></label>
<label>مجلد ثانٍ (فلاشة أو مجلد Google Drive) — اختياري<input name="backup_dir2" value="{{ st.dir2 or '' }}" dir="ltr" style="width:280px" placeholder="E:\\Bilsan_Backup"></label>
<label>كل كم ساعة<input name="backup_every_hours" value="{{ st.every }}" style="width:70px"></label><button class="btn light">حفظ</button></form>
<p class="mut">أنصح بمجلد ثانٍ داخل Google Drive للحاسوب: هكذا تبقى نسخة خارج المحل حتى لو ضاع الحاسوب.</p></div>
<div class="card"><h2>النسخ</h2><table><tr><th>التاريخ</th><th>الحجم</th><th></th></tr>
{% for f in files %}<tr><td>{{ f.dt.strftime('%Y-%m-%d %H:%M') }}</td><td>{{ '%.1f'|format(f.size/1048576) }} ميغا</td>
<td><a class="btn light sm" href="{{ url_for('backup_download', name=f.name) }}">تحميل</a>
<form method="post" style="display:inline" onsubmit="return confirm('استرجاع البيانات كما كانت في {{ f.dt.strftime('%Y-%m-%d %H:%M') }}؟ كل ما سُجّل بعدها سيُلغى (البيانات الحالية تُحفظ نسخة قبل الاسترجاع).')">
<input type="hidden" name="action" value="restore"><input type="hidden" name="name" value="{{ f.name }}"><button class="btn red sm">استرجاع</button></form></td></tr>
{% else %}<tr><td colspan="3" class="mut">لا توجد نسخ بعد</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["leave.html"] = r"""{% extends "base.html" %}{% block body %}
<h1 class="noprint">مغادرة العمل وتصفية الحساب — {{ e.name }}</h1>
{% if not done and e.active %}<div class="card noprint"><form class="row"><label>آخر يوم عمل<input type="date" name="last_day" value="{{ last }}"></label><button class="btn light">حساب</button></form>
<p class="mut">البرنامج يحسب أجرة الأيام من بداية فترته الحالية إلى آخر يوم عمل (مع الغيابات والمنح)، ويقتطع كل التسبيقات التي لم تُقتطع بعد.
بعد التأكيد: يُسجَّل المبلغ في المصاريف مرة واحدة، ويُوقف العامل فلا تُحسب له أجرة بعدها.</p></div>{% endif %}
<div class="card" style="max-width:760px;margin:auto">
<div style="display:flex;align-items:center;gap:14px;border-bottom:2px solid #e4ab74;padding-bottom:10px;margin-bottom:10px">
<img src="{{ url_for('static', filename='logo_full.jpg') }}" style="width:70px;border-radius:8px"><div><h2 style="margin:0">{{ center }}</h2><div class="mut">{{ e.branch }}</div></div>
<div style="margin-inline-start:auto;text-align:left"><b>تصفية حساب نهائية</b><div>{{ now[:10] }}</div></div></div>
<table><tr><td>العامل: <b>{{ e.name }}</b>{% if e.post %} — {{ e.post }}{% endif %}</td><td>بداية العمل: {{ e.hire_date or '-' }}</td><td>آخر يوم عمل: <b>{{ e.end_date or last }}</b></td></tr></table>
{% if prev %}<h2 style="margin-top:12px">أجرة الفترة السابقة (لم تُدفع): {{ prev.d1 }} ← {{ prev.d2 }}</h2>
<table><tr><td>{{ '%g'|format(prev.days) }} يوم{% if prev.ptype=='daily' %} × {{ prev.rate|money }}{% endif %}</td><td class="right">{{ prev.gross|money }}</td></tr>
{% if prev.plus %}<tr><td>منح</td><td class="right">+{{ prev.plus|money }}</td></tr>{% endif %}{% if prev.advance %}<tr><td>تسبيقات</td><td class="right">−{{ prev.advance|money }}</td></tr>{% endif %}
<tr><td><b>صافي الفترة السابقة</b></td><td class="right"><b>{{ prev.net|money }}</b></td></tr></table>{% endif %}
<h2 style="margin-top:12px">الفترة الأخيرة: {{ s.d1 }} ← {{ last }}</h2>
<table><tr><td>أيام العمل: {{ s.wdays }} − غياب {{ '%g'|format(s.lost) }}{% if s.extra %} + {{ '%g'|format(s.extra) }}{% endif %} = {{ '%g'|format(s.days) }} يوم{% if s.ptype=='daily' %} × {{ s.rate|money }}{% endif %}</td><td class="right">{{ s.gross|money }}</td></tr>
{% for g in s.grants %}<tr><td>{{ GRANT_KINDS[g.kind] }} ({{ g.day }})</td><td class="right"><bdi dir="ltr">+{{ g.amount|money|striptags }}</bdi></td></tr>{% endfor %}
{% for g in s.advances %}<tr><td>تسبيق يوم {{ g.day }}{% if g.note %} — {{ g.note }}{% endif %}</td><td class="right" style="color:#b3261e"><bdi dir="ltr">−{{ g.amount|money|striptags }}</bdi></td></tr>{% endfor %}
<tr style="background:#efe2cf"><td><b>المبلغ النهائي المستحق للعامل</b></td><td class="right"><b style="font-size:18px">{{ total|money }} {{ cur }}</b></td></tr></table>
{% if total < 0 %}<p style="color:#b3261e">التسبيقات أكبر من الأجرة: العامل مدين للمركز بـ {{ (-total)|money }}.</p>{% endif %}
{% if not done and e.active %}<form method="post" class="row noprint" style="margin-top:14px" onsubmit="return confirm('تأكيد تصفية الحساب وإيقاف العامل نهائيًا؟')">
<input type="hidden" name="last_day" value="{{ last }}"><label>المبلغ المسلَّم<input name="amount" value="{{ '%g'|format(total) }}" style="width:110px"></label>
<label>سبب المغادرة<input name="reason" placeholder="استقالة، نهاية العقد..."></label><button class="btn red">تأكيد المغادرة وتسليم الأجرة</button></form>
{% else %}<p class="tag">تمت التصفية — العامل موقوف{% if e.end_reason %} ({{ e.end_reason }}){% endif %}</p>
<div style="display:flex;justify-content:space-between;margin-top:34px"><div>إمضاء المسؤول</div><div>إمضاء العامل (استلمت كل حقوقي)</div></div>
<p class="noprint"><button class="btn gold" onclick="window.print()">طباعة</button> <a class="btn light" href="{{ url_for('staff') }}">رجوع</a></p>{% endif %}</div>{% endblock %}"""


TEMPLATES["devices.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="card"><h1>{{ page_icon() }} الحواسيب وكلمات السر</h1>
<p class="mut">كل حاسوب مربوط بفرع ومكان، ويدخل بكلمة سر خاصة به. تغيير كلمة السر أو الإيقاف يصل للحاسوب عند اتصاله بالإنترنت.
الحاسوب الموقوف لا يستطيع الدخول ولا إرسال أي شيء.</p>
<p>نسخة البرنامج في هذا الحاسوب: <b dir="ltr">{{ version }}</b>. الحواسيب الأخرى تتحدث وحدها إلى هذه النسخة عند تشغيلها أو بعد 5 دقائق بلا استعمال.</p>
<table><tr><th>الحاسوب</th><th>الفرع</th><th>المكان</th><th>آخر اتصال</th><th>النسخة</th><th>الحالة</th><th>كلمة سر جديدة</th><th></th></tr>
{% for d in rows %}<tr{% if not d.active %} style="opacity:.55"{% endif %}>
<td><b>{{ d.full_name }}</b><div class="mut">رقم {{ d.slot }}</div></td><td>{{ d.branch }}</td><td>{{ PLACES.get(d.role, d.role) }}</td>
<td>{% if d.last_seen %}{{ d.last_seen[:16] }}{% else %}<span class="mut">لم يتصل بعد</span>{% endif %}</td>
<td dir="ltr">{% if d.app_version %}{{ d.app_version }}{% if d.app_version != version %} <span title="سيتحدث قريبًا">⏳</span>{% else %} ✅{% endif %}{% else %}<span class="mut">—</span>{% endif %}</td>
<td>{% if d.active %}<span style="color:#1a7a40">🟢 يعمل</span>{% else %}<span style="color:#a12">⛔ موقوف</span>{% endif %}
{% if codes.get(d.id) %}<div class="mut">رمز الربط: <b dir="ltr" style="font-size:16px;letter-spacing:2px">{{ codes[d.id].code }}</b></div>{% endif %}</td>
<td><form method="post" style="display:flex;gap:4px"><input type="hidden" name="act" value="password"><input type="hidden" name="id" value="{{ d.id }}">
<input name="password" placeholder="كلمة السر" minlength="4" required style="width:120px"><button class="btn sm">حفظ</button></form></td>
<td style="white-space:nowrap"><form method="post" style="display:inline"><input type="hidden" name="act" value="toggle"><input type="hidden" name="id" value="{{ d.id }}">
<button class="btn sm {{ 'red' if d.active else '' }}" onclick="return confirm('{{ 'إيقاف' if d.active else 'تشغيل' }} {{ d.full_name }}؟')">{{ 'إيقاف' if d.active else 'تشغيل' }}</button></form>
<form method="post" style="display:inline"><input type="hidden" name="act" value="code"><input type="hidden" name="id" value="{{ d.id }}">
<button class="btn sm ghost" title="لإعادة تثبيت البرنامج على حاسوب جديد مكان هذا">رمز ربط</button></form></td></tr>
{% else %}<tr><td colspan="8" class="mut">لا توجد حواسيب بعد</td></tr>{% endfor %}</table></div>
<div class="card"><h2>➕ إضافة حاسوب جديد</h2>
<p class="mut">بعد الإضافة يظهر <b>رمز ربط من 6 أرقام</b>. ثبّت البرنامج العام (Bilsan-Setup) على الحاسوب الجديد واكتب الرمز. الرمز صالح يومين ولمرة واحدة.</p>
<form method="post" class="grid" style="grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px;align-items:end">
<input type="hidden" name="act" value="add">
<label>اسم الحاسوب<input name="full_name" placeholder="مثلًا: تجميل الحروش 2" required></label>
<label>الفرع<select name="branch_id">{% for b in branches %}<option value="{{ b.id }}">{{ b.name }}</option>{% endfor %}</select></label>
<label>المكان<select name="role">{% for k, v in PLACES.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></label>
<label>كلمة السر<input name="password" minlength="4" required></label>
<button class="btn">إضافة</button></form></div>
{% endblock %}"""


TEMPLATES["tiles.html"] = r"""<div class="tiles noprint">
{% if perm('reception_visits') %}<a class="tile" href="{{ url_for('visit_new') }}">{{ ic('reception') }}استقبال زبون</a>{% endif %}
{% if perm('collect') %}<a class="tile" href="{{ url_for('reception') }}">{{ ic('cash') }}التحصيل</a>{% endif %}
{% if perm('pos') %}<a class="tile" href="{{ url_for('pos') }}">{{ ic('cart') }}بيع المنتجات</a>{% endif %}
<a class="tile" href="{{ url_for('appointments') }}">{{ ic('calendar') }}المواعيد</a>
<a class="tile" href="{{ url_for('clients') }}">{{ ic('clients') }}الزبائن</a>
<a class="tile" href="{{ url_for('plans') }}">{{ ic('plans') }}خطط الحصص</a>
{% if cu.role=='admin' %}
<a class="tile" href="{{ url_for('cash_daily') }}">{{ ic('safe') }}الصندوق اليومي</a>
<a class="tile" href="{{ url_for('reports') }}">{{ ic('reports') }}التقارير والأرباح</a>
<a class="tile" href="{{ url_for('products') }}">{{ ic('products') }}المنتجات والمخزون</a>
<a class="tile" href="{{ url_for('services') }}">{{ ic('services') }}الخدمات والأسعار</a>
<a class="tile" href="{{ url_for('staff') }}">{{ ic('staff') }}العمال والحضور</a>
<a class="tile" href="{{ url_for('permissions') }}">{{ ic('key') }}الصلاحيات</a>
{% if not NODE %}<a class="tile" href="{{ url_for('devices') }}">{{ ic('monitor') }}الحواسيب</a>{% endif %}
{% else %}
{% if perm('attendance') %}<a class="tile" href="{{ url_for('staff') }}">{{ ic('staff') }}العمال والحضور</a>{% endif %}
{% if perm('courses') %}<a class="tile" href="{{ url_for('courses') }}">{{ ic('course') }}الدورات</a>{% endif %}
{% if perm('cash_close') %}<a class="tile" href="{{ url_for('cash_close') }}">{{ ic('lock') }}إغلاق الصندوق</a>{% endif %}
{% endif %}</div>"""
