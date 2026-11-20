# KIRO Print OS — منظومة إدارة المطابع ومحلات الطباعة والهدايا

**العربية** · [English](#english)

نظام ويب كامل (Flask + SQLite) لإدارة المطابع ومكتبات التصوير ومحلات الطباعة على الهدايا: كاشير سريع، فواتير قابلة للتخصيص بالكامل، مخزون، عملاء ومديونيات، موظفين، تقارير، واشتراكات متعددة المطابع والفروع.

## المميزات

| المجال | الوظائف |
|---|---|
| **الكاشير** | فواتير بالمتر/بالقطعة/كتب ومذكرات، تسعير جملة تلقائي، **تعديل الفواتير** (بصلاحية من الأدمن)، **خدمات تشطيب** (ثابتة من الأدمن + يدوية بسعر يحدده الكاشير)، حفظ وطباعة، إشعارات واتساب بحالة الطلب |
| **بيع سريع** | عدّاد للتصوير والخدمات اللحظية **بدون فاتورة**: اختر الخامة، اكتب العدد (+ الهالك)، والفلوس والمخزن بيتسجلوا |
| **السداد والديون** | صفحة مخصصة: سداد **جزء من الفلوس** أو **جزء من فاتورة قديمة**، إضافة **مديونية قديمة** على عميل بدون فاتورة، وكل عملية بتاريخها ووقتها |
| **العملاء** | تسجيل تلقائي بمجرد كتابة الاسم، **فئات مميزة** (مثال: بعد 20 فاتورة ومشتريات 300 ج) بخصم تلقائي واسم الفئة يظهر على الفاتورة |
| **تصميم الفاتورة** | مقاسات (حراري 58/80، A4، A5، مخصص)، خطوط وألوان، لوجو، إظهار/إخفاء 28 عنصر، تغيير 29 عنوان، QR، شروط، **معاينة حية** |
| **الأدمن** | ملخص مالي، مخزون وحد الطلب، مصروفات، موظفين ورواتب وسلف، حسابات وكالات B2B، سجل رقابة، إكسيل، تقرير إغلاق |
| **الفروع** | حساب **مالك** بعدة فروع: لكل فرع أدمن وكاشير، أدمن الفرع يشوف فرعه فقط، والمالك يتابع كل فرع لوحده من لوحة موحدة |
| **قوالب الأنشطة** | تحميل خدمات وأسعار وتشطيبات جاهزة لـ: مطبعة شاملة، مكتبة وتصوير، ديجيتال، بنرات وإعلانات، أوفست وكتب، علب وتغليف، طباعة ملابس، هدايا، استيكرات |
| **المنصة** | واجهة عربي/إنجليزي، حماية CSRF، نوافذ منبثقة وجولات تعريفية، وضع داكن/فاتح، اشتراكات وخطط من لوحة السوبر أدمن |

## التشغيل المحلي

```bash
git clone <your-repo-url> kiro-print-os && cd kiro-print-os
python -m venv venv && source venv/bin/activate      # ويندوز: venv\Scripts\activate
pip install -r requirements.txt
python app.py                                         # http://127.0.0.1:5000
```

عند **أول تشغيل** بيتولّد حساب السوبر أدمن (`sa`) بباسورد عشوائي بيتطبع في الـ terminal ويتحفظ في `initial_credentials.txt`. تقدر تحدده بنفسك بـ `SA_USERNAME` و`SA_PASSWORD` (انظر `.env.example`). **غيّر الباسورد بعد أول دخول.**

## النشر على PythonAnywhere

1. ارفع المشروع (أو `git clone`) في `/home/YOURUSER/kiro-print-os` — **لازم مجلدات `templates/` و`static/` تتحمل معاه.**
2. في Bash: `cd kiro-print-os && pip install --user -r requirements.txt`
3. تبويب **Web** ← Add a new web app ← Manual configuration (Python 3.10+).
4. افتح ملف WSGI وخلّيه يستدعي `wsgi.py` (الشرح داخل الملف نفسه).
5. اضغط **Reload**. قاعدة البيانات `kiro_platform.db` بتتعمل تلقائي، **والترقية من نسخة أقدم بتضيف الأعمدة الجديدة بدون ما تمسح أي بيانات** — فقط احتفظ بملف القاعدة القديم جنب `app.py`.

## الأدوار والصلاحيات

| الدور | بيشوف إيه |
|---|---|
| **السوبر أدمن** `/sa` | كل المطابع والاشتراكات والخطط (عدد الفروع لكل خطة) |
| **المالك** `/owner` | لوحة كل الفروع + إنشاء فروع (حسب الخطة) + الدخول للوحة أي فرع |
| **أدمن الفرع** `/admin` | بيانات فرعه فقط |
| **مشرف / كاشير** `/cashier` | شاشة الكاشير وصفحات السداد والبيع السريع لفرعه |

### إعداد حساب سلسلة فروع
1. من لوحة السوبر أدمن: **إضافة مطبعة** ← عدد الفروع المسموح به > 1 (أو اختر خطة «سلسلة فروع»). الحساب الأول بيتعمل بدور **مالك**.
2. المالك يدخل ← `/owner` ← **إضافة فرع** (اسم الفرع + أدمن + كاشير + قالب نشاط، أو نسخ الأسعار من الفرع الرئيسي).
3. من «فتح لوحة الفرع» يقدر يتحكم في أي فرع، وأدمن الفرع بياناته معزولة عن باقي الفروع.

## هيكل المشروع

```
app.py            التطبيق (النماذج، المسارات، المنطق)
presets.py        قوالب الأنشطة الجاهزة (عدّلها أو أضف قالب)
i18n.py           قاموس الترجمة (EN) — أضف لغة جديدة بسهولة
wsgi.py           نقطة التشغيل للاستضافة
templates/        صفحات HTML (Jinja2 + Tailwind CDN)
static/           ui.css / ui.js (إشعارات، نوافذ، جولات، ترجمة) و app.css
tests/            اختبارات pytest
```

## إضافة لغة

افتح `i18n.py`، أضف قاموس (مثلاً `FR = {...}` يترجم النص العربي حرفياً)، سجّل اللغة في `LANGS` داخل `app.py`، وأضف فرعاً لها في `translate()` و`i18n_js()`. أي نص بدون ترجمة بيفضل بالعربية.

## الاختبارات

```bash
pip install -r requirements-dev.txt && python -m pytest -q
```

## الأمان

- كل طلبات POST محمية بـ CSRF، وكلمات المرور مشفّرة، والمفتاح السري بيتولّد تلقائي.
- بوابة العميل `/portal/<الهاتف>` عامة لأي حد يعرف الرقم — لو حابب تقفلها أضف كود سري.
- شغّل الموقع على HTTPS (PythonAnywhere بيوفره).

## الترخيص

MIT — انظر `LICENSE` (تقدر تغيّره لترخيص مناسب لك).

---

<a id="english"></a>
# English

**KIRO Print OS** is a complete web system (Flask + SQLite) for print shops, copy centers and personalized-gift stores: fast cashier, fully customizable invoices, inventory, customers & debts, staff, reports, and multi-shop / multi-branch subscriptions. The UI is available in **Arabic and English**.

## Highlights
- **Cashier:** area/unit/book pricing, automatic wholesale tiers, **invoice editing** (admin-controlled), **finishing services** (fixed ones from the admin + manual ones priced by the cashier).
- **Quick sale:** a counter for photocopying & instant services **without invoices** — pick a material, enter the count (+ wasted sheets); revenue and stock are updated.
- **Payments & debts:** a dedicated page to pay **part of the money** or **part of an old invoice**, add **old balances** without an invoice, every entry timestamped.
- **Customers:** automatically registered when you type a name; **VIP tiers** (e.g. 20 invoices *and* 300 EGP spent) with automatic discount and the tier printed on the invoice.
- **Invoice designer:** thermal 58/80, A4, A5, custom sizes; fonts, colors, logo, 28 show/hide switches, 29 editable labels, QR, terms, **live preview**.
- **Branches:** an *owner* account with many branches — each branch gets its own admin and cashier; branch admins only see their branch; the owner follows every branch from one dashboard. The branch limit comes from the subscription plan.
- **Business templates:** one-click catalogs for general print shops, copy centers, digital printing, large format/signage, offset & books, packaging, apparel (DTF/screen/sublimation), gifts, stickers & labels (indicative EGP prices — edit freely).

## Quick start
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py        # http://127.0.0.1:5000
```
On first run a super-admin (`sa`) is created with a random password printed to the terminal and saved to `initial_credentials.txt` (or set `SA_USERNAME` / `SA_PASSWORD`, see `.env.example`).

## Deploy on PythonAnywhere
Upload the project (with `templates/` and `static/`), `pip install --user -r requirements.txt`, create a manual-configuration web app, point its WSGI file to `wsgi.py` (instructions inside), then **Reload**. Upgrading from an older version keeps your `kiro_platform.db` — new columns/tables are migrated automatically.

## Roles
Super admin (`/sa`) → Owner (`/owner`) → Branch admin (`/admin`) → Supervisor / Cashier (`/cashier`).

## Tests & license
`python -m pytest -q` · MIT license (see `LICENSE`).
