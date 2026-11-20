# -*- coding: utf-8 -*-
"""
i18n — ترجمة الواجهة / UI translation
======================================
النصوص الأصلية بالعربية. القاموس EN بيترجم النص العربي (حرفياً) للإنجليزية، سواء في القوالب
(من خلال المتصفح) أو في رسائل السيرفر. أي نص مالوش ترجمة بيفضل بالعربية.

لإضافة لغة جديدة (مثلاً الفرنسية):
  1) أضف قاموس FR = {...} هنا.   2) سجّلها في LANGS داخل app.py.   3) أضف فرع في translate().

Source strings are Arabic. EN maps exact Arabic strings to English; anything missing stays Arabic.
"""

EN = {
    # ---- التنقل والأقسام ----
    'الرئيسية': 'Home', 'الملخص المالي': 'Financial summary', 'المبيعات': 'Sales', 'الفواتير': 'Invoices',
    'تصميم الفاتورة': 'Invoice design', 'العملاء والمديونيات': 'Customers & debts', 'الأسعار والمخزن': 'Prices & stock',
    'الخدمات والمخزون': 'Services & inventory', 'التجليد والتشطيب': 'Binding & finishing', 'حسابات الوكالات (B2B)': 'Partner accounts (B2B)',
    'المالية والفريق': 'Finance & team', 'المصاريف والخزينة': 'Expenses & cash', 'الموظفون والحسابات': 'Staff & accounts',
    'النظام': 'System', 'سجل الرقابة': 'Audit log', 'الإعدادات': 'Settings', 'الأقسام': 'Sections', 'القائمة': 'Menu',
    'لوحة الإدارة': 'Admin panel', 'لوحة الأدمن': 'Admin panel', 'لوحة تحكم الأدمن': 'Admin control panel', 'أدمن المطبعة': 'Shop admin',
    'فتح شاشة الكاشير': 'Open cashier screen', 'تسجيل الخروج': 'Log out', 'خروج': 'Logout', 'جديد': 'New', 'مساعدة': 'Help',
    'كل الفروع': 'All branches', 'لوحة المالك — كل الفروع': 'Owner dashboard — all branches', 'فتح لوحة الفرع': 'Open branch panel',
    'العودة لكل الفروع': 'Back to all branches', 'أنت بتتصفح فرع:': 'You are browsing branch:', 'الرئيسي': 'Main',
    # ---- الأزرار العامة ----
    'حفظ': 'Save', 'إلغاء': 'Cancel', 'إغلاق': 'Close', 'حذف': 'Delete', 'تعديل': 'Edit', 'إضافة': 'Add', 'بحث': 'Search',
    'تأكيد': 'Confirm', 'التالي': 'Next', 'السابق': 'Previous', 'رجوع': 'Back', 'احذف': 'Delete', 'تسجيل': 'Record', 'قيد': 'Post',
    'عرض وطباعة': 'View & print', '🖨️ طباعة': '🖨️ Print', 'إجراءات': 'Actions', 'مسح الفلاتر': 'Clear filters', 'إزالة': 'Remove',
    'حفظ التعديلات': 'Save changes', 'حفظ البيانات': 'Save details', 'تغيير كلمة المرور': 'Change password',
    'جاري التحميل...': 'Loading...', 'اختياري': 'Optional', 'الكل': 'All', 'بدون': 'None', 'ج.م': 'EGP', 'مساعدة': 'Help',
    'الوضع الفاتح': 'Light mode', 'تبديل بين الوضع الداكن والفاتح': 'Toggle dark / light mode', 'النهاري (كريمي)': 'Light (cream)',
    # ---- الملخص ----
    'إجمالي المبيعات': 'Total sales', 'المحصّل فعلياً (الخزينة)': 'Collected (cash)', 'المصروفات': 'Expenses', 'صافي الربح': 'Net profit',
    'المحصّل − المصروفات': 'Collected − expenses', 'ديون عند العملاء': 'Customer debts', 'عدد الفواتير': 'Invoice count',
    'مستحقات الموظفين': 'Staff dues', 'الأكثر مبيعاً': 'Top sellers', 'خامات قربت تخلص': 'Low-stock items',
    'المبيعات والمصروفات — آخر 7 أيام': 'Sales & expenses — last 7 days', 'أرقام المطبعة لحظة بلحظة': 'Your shop numbers in real time',
    'أهلاً بيك!': 'Welcome!', 'كل الخامات في الحد الآمن ✅': 'All stock is at a safe level ✅', 'لسه مفيش مبيعات': 'No sales yet',
    'النواقص': 'Shortages', 'إكسيل': 'Excel', 'تقرير الإغلاق': 'Closing report', 'إعلام النواقص': 'Shortage alert',
    'اضغط لعرض الفواتير غير المسددة': 'Click to view unpaid invoices',
    # ---- الفواتير ----
    'الكود': 'Code', 'العميل': 'Customer', 'الإجمالي': 'Total', 'المدفوع': 'Paid', 'المتبقي': 'Remaining', 'الحالة': 'Status',
    'التاريخ': 'Date', 'خالص ✓': 'Paid ✓', 'خالص ✅': 'Paid ✅', 'اكتب وابحث...': 'Type to search...', 'حالة الطلب': 'Order status',
    'عليها مديونية فقط': 'With debt only', 'بحث (رقم الفاتورة / اسم العميل / الهاتف)': 'Search (invoice no. / customer / phone)',
    'قيد التنفيذ': 'In progress', 'دخلت الطباعة': 'In printing', 'في التجهيز': 'Finishing', 'جاهز للاستلام': 'Ready for pickup',
    'شكراً لتعاملكم': 'Thank you', 'تعديل الفاتورة': 'Edit invoice', 'تعديل فاتورة': 'Edit invoice', 'اسم العميل': 'Customer name',
    'اسم العميل *': 'Customer name *', 'الهاتف': 'Phone', 'طريقة الدفع': 'Payment method', 'نقدي': 'Cash', 'آجل': 'Credit',
    'فودافون كاش': 'Vodafone Cash', 'إنستا باي': 'InstaPay', 'تحويل بنكي': 'Bank transfer', 'ملاحظات الفاتورة': 'Invoice notes',
    'البند': 'Item', 'الكمية': 'Qty', 'الطول': 'Height', 'العرض': 'Width', 'الإجمالي الكلي': 'Grand total', 'بند جديد': 'New item',
    '+ إضافة من الخدمات...': '+ Add from services...', 'مصاريف التصميم': 'Design fee', 'الخصم': 'Discount', 'سعر الوحدة/م²': 'Unit price / m²',
    'سبب التعديل * (يُسجل في الرقابة)': 'Reason for edit * (logged)', 'خدمة تشطيب': 'Finishing service', 'خدمات التشطيب الإضافية': 'Extra finishing services',
    'إلغاء التعديل': 'Cancel edit', '✏️ تعديل': '✏️ Edit', '✏️ جاري تعديل الفاتورة': '✏️ Editing invoice',
    'لسه مفيش فواتير': 'No invoices yet',
    # ---- تصميم الفاتورة ----
    'حفظ التصميم': 'Save design', 'الرجوع للتصميم الأصلي': 'Reset to default design', 'معاينة حية': 'Live preview',
    'معاينة على فاتورة:': 'Preview on invoice:', 'فاتورة تجريبية': 'Sample invoice', 'تغييرات غير محفوظة': 'Unsaved changes',
    'المقاس والورق': 'Size & paper', 'الخط والألوان': 'Font & colors', 'ترويسة الفاتورة (اللوجو والعنوان)': 'Invoice header (logo & title)',
    'إيه اللي يظهر في الفاتورة؟': 'What appears on the invoice?', 'أسماء الحقول والعناوين': 'Field names & labels',
    'الأرقام والعملة': 'Numbers & currency', 'التذييل والشروط': 'Footer & terms', 'مقاس الورق الافتراضي': 'Default paper size',
    'مقاس الورق': 'Paper size', 'العرض (مم)': 'Width (mm)', 'الطول (مم)': 'Height (mm)', 'اتجاه الورقة (A4 / A5)': 'Orientation (A4 / A5)',
    'طولي': 'Portrait', 'عرضي': 'Landscape', 'الهوامش (مم)': 'Margins (mm)', 'حجم الخط:': 'Font size:', 'نوع الخط': 'Font family',
    'سُمك الخط': 'Font weight', 'عادي': 'Normal', 'عريض': 'Bold', 'عريض جداً': 'Extra bold', 'لون النص': 'Text color',
    'لون النص الثانوي': 'Secondary text color', 'لون التنبيه (المتبقي)': 'Alert color (remaining)', 'خلفية رأس الجدول': 'Table header background',
    'لون الخطوط': 'Line color', 'لون الورقة': 'Paper color', 'نمط الفواصل': 'Divider style', 'متقطع': 'Dashed', 'متصل': 'Solid', 'نقاط': 'Dotted',
    'كثافة الصفوف': 'Row density', 'مضغوط': 'Compact', 'مريح': 'Relaxed', 'اللوجو': 'Logo', 'رفع صورة': 'Upload image', 'ارتفاع اللوجو (مم)': 'Logo height (mm)',
    'محاذاة الترويسة': 'Header alignment', 'وسط': 'Center', 'يمين': 'Right', 'يسار': 'Left', 'العنوان الفرعي': 'Subtitle',
    'اسم يظهر بدل اسم المطبعة': 'Name shown instead of shop name', 'رمز العملة': 'Currency symbol', 'عدد الأرقام العشرية': 'Decimal places',
    'رسالة الشكر': 'Thank-you message', 'الشروط والأحكام': 'Terms & conditions', 'سطر الشعار السفلي': 'Bottom brand line',
    'حجم كود QR (مم)': 'QR code size (mm)', 'خانات التوقيع': 'Signature boxes', 'تلقائي (A4 و A5 فقط)': 'Auto (A4 & A5 only)',
    'دايماً': 'Always', 'أبداً': 'Never', 'بتتحدث تلقائياً مع كل تعديل': 'Updates automatically with every change',
    'السعر': 'Price', 'التكلفة': 'Cost',
    # ---- الخدمات والمخزون ----
    'إضافة خدمة أو خامة جديدة': 'Add a new service or material', 'الاسم *': 'Name *', 'سعر التكلفة': 'Cost price', 'سعر القطاعي': 'Retail price',
    'سعر القطاعي *': 'Retail price *', 'سعر الجملة': 'Wholesale price', 'حد الجملة (كمية)': 'Wholesale threshold (qty)', 'حد الجملة': 'Wholesale threshold',
    'الرصيد بالمخزن': 'Stock on hand', 'حد الطلب': 'Reorder level', 'الوحدة': 'Unit', 'سعر المتر المربع': 'Price per m²', 'حساب بالمتر (م²)': 'Area-based (m²)',
    'حساب بالمتر': 'Area-based', 'بنر / يافطة': 'Banner / signage', 'مفضلة ⭐': 'Favorite ⭐', 'ابحث في الخدمات...': 'Search services...',
    'الاسم': 'Name', 'قطاعي': 'Retail', 'جملة': 'Wholesale', 'المخزون': 'Stock', 'سعر المتر': 'Price / m²', 'غير محدود': 'Unlimited',
    'تعديل خدمة': 'Edit service', 'حذف خدمة': 'Delete service', 'بالمتر': 'By m²', 'بنر': 'Banner',
    'الرصيد (فاضي = غير محدود)': 'Stock (empty = unlimited)', 'فاضي = غير محدود': 'Empty = unlimited',
    # ---- التجليد والتشطيب ----
    'إضافة أسلوب تجليد': 'Add binding method', 'النوع *': 'Type *', 'السعر للوحدة (ج.م) *': 'Unit price (EGP) *', 'خدمات التشطيب الثابتة': 'Fixed finishing services',
    'اسم الخدمة *': 'Service name *', 'السعر (ج.م) *': 'Price (EGP) *', 'ظاهرة': 'Visible', 'تعديل أسلوب التجليد': 'Edit binding method',
    'لسه مفيش أساليب تجليد.': 'No binding methods yet.',
    # ---- العملاء ----
    'العملاء اللي عليهم مديونية': 'Customers with debt', 'كل العملاء': 'All customers', 'العملاء المتميزون': 'VIP customers', 'تسجيل عميل متميز يدوياً (VIP)': 'Register a VIP customer manually',
    'العميل المتميز (VIP)': 'VIP customer', 'نسبة الخصم % *': 'Discount % *', 'الرتبة': 'Tier', 'الفئة': 'Tier', 'مديونية قديمة': 'Old balance',
    'المشتريات': 'Purchases', 'فواتير': 'Invoices', 'حفظ العميل': 'Save customer', 'تعديل عميل متميز': 'Edit VIP customer',
    'صفحة سداد المديونيات': 'Debt payments page', 'ابحث عن عميل...': 'Search customers...', 'تذكير واتساب': 'WhatsApp reminder', 'سداد': 'Pay',
    'عدد الفواتير': 'Invoice count', 'اسم الفئة': 'Tier name', 'عدد الفواتير (على الأقل)': 'Invoices (at least)', 'إجمالي المشتريات (ج.م)': 'Total purchases (EGP)',
    'خصم تلقائي %': 'Auto discount %', 'فئات العملاء المميزين وصلاحيات الكاشير': 'VIP tiers & cashier permissions',
    'تعديل الفواتير للكاشير': 'Cashier invoice editing', 'ممنوع (الأدمن فقط)': 'Not allowed (admin only)', 'فواتيره هو اللي عملها النهاردة': "Only the cashier's own invoices from today",
    'كل فواتير الفرع': 'All branch invoices', 'يقدر الكاشير يحذف فاتورة (بسبب)': 'Cashier can delete an invoice (with reason)',
    'لسه مفيش عملاء — هيتسجلوا تلقائياً مع أول فاتورة.': 'No customers yet — they are registered automatically with the first invoice.',
    # ---- صفحة السداد والبيع السريع ----
    'سداد المديونيات': 'Debt payments', 'سداد الديون': 'Pay debts', 'العملاء عليهم مبالغ': 'Customers who owe', 'إضافة مديونية قديمة على عميل': 'Add an old balance to a customer',
    'تسجيل المديونية': 'Record balance', 'المبلغ المتبقي *': 'Amount owed *', 'ملاحظة': 'Note', 'اختر عميل من القائمة لعرض فواتيره وتسجيل السداد.': 'Select a customer to view invoices and record payments.',
    'دفعة عامة (ج.م)': 'General payment (EGP)', 'تسجيل السداد': 'Record payment', 'الفواتير غير المسددة': 'Unpaid invoices',
    'سجل السداد (بالتاريخ والوقت)': 'Payment history (with date & time)', 'التاريخ والوقت': 'Date & time', 'العملية': 'Operation', 'المبلغ': 'Amount', 'بواسطة': 'By',
    'مفيش مديونيات مفتوحة 🎉': 'No open debts 🎉', 'بيع سريع': 'Quick sale', 'بيع سريع بدون فاتورة': 'Quick sale without invoice', 'إجمالي اليوم': "Today's total",
    'اختر الخدمة / الخامة': 'Choose service / material', 'الخدمة المختارة': 'Selected service', '— اختر خدمة —': '— Choose a service —', 'العدد': 'Count',
    'هالك': 'Wasted', 'هالك (ورق باظ)': 'Wasted (spoiled paper)', 'سعر الوحدة': 'Unit price', 'الإجمالي': 'Total', 'صفر': 'Zero', 'تسجيل (Enter)': 'Record (Enter)',
    'ملخص اليوم حسب الخدمة': "Today's summary by service", 'آخر العمليات': 'Recent operations', 'الفلوس': 'Money', 'الوقت': 'Time', 'الخدمة': 'Service',
    'أو اكتب خدمة يدوية': 'Or type a manual service', 'استخدام الخدمة اليدوية': 'Use manual service', 'ابحث...': 'Search...',
    # ---- الموظفون ----
    'إضافة موظف جديد': 'Add a new employee', 'الاسم الكامل *': 'Full name *', 'اسم المستخدم *': 'Username *', 'كلمة المرور (6+) *': 'Password (6+) *',
    'الراتب الأساسي': 'Base salary', 'الوظيفة': 'Role', 'كاشير': 'Cashier', 'مشرف': 'Supervisor', 'إنشاء الحساب': 'Create account', 'تعديل بيانات موظف': 'Edit employee',
    'الأساسي': 'Base', 'مكافآت': 'Bonuses', 'سلف/خصم': 'Advances/deductions', 'الصافي': 'Net', 'سلفة': 'Advance', 'مكافأة': 'Bonus', 'خصم': 'Deduction',
    'إقفال الشهر': 'Close month', 'حذف موظف': 'Delete employee', 'كلمة مرور جديدة': 'New password', 'الحساب مفعّل (يقدر يسجل الدخول)': 'Account active (can log in)',
    'موقوف': 'Suspended', 'اسم المستخدم': 'Username', 'كلمة المرور': 'Password', 'الاسم الكامل': 'Full name',
    # ---- المصاريف ----
    'قيد مصروف جديد': 'Record a new expense', 'البيان *': 'Description *', 'المبلغ (ج.م) *': 'Amount (EGP) *', 'قيد المصروف': 'Post expense', 'البيان': 'Description',
    'المسؤول': 'Responsible', 'مفيش مصاريف مسجلة.': 'No expenses recorded.', 'ملاحظات': 'Notes',
    # ---- B2B ----
    'إضافة شريك': 'Add partner', 'تسجيل الشريك': 'Register partner', 'قيد حركة': 'Post a transaction', 'نوع الحركة': 'Transaction type', 'قيد الحركة': 'Post transaction',
    'الأرصدة': 'Balances', 'الشريك': 'Partner', 'الموقف': 'Position', 'كشف حساب': 'Statement', 'تسوية / دفعة': 'Settlement / payment', 'الحركة': 'Transaction',
    'طبعنا عنده (يزيد اللي لنا طرفه)': 'We printed for them (they owe us more)', 'طبع عندنا (يزيد اللي له طرفنا)': 'They printed for us (we owe them more)',
    # ---- الرقابة / الإعدادات ----
    'ابحث في السجل...': 'Search the log...', 'السجل نظيف — مفيش تعديلات أو حذف.': 'The log is clean — no edits or deletions.', 'بيانات المطبعة': 'Shop details',
    'اسم المطبعة *': 'Shop name *', 'اسم المالك': 'Owner name', 'رقم الهاتف (واتساب)': 'Phone (WhatsApp)', 'العنوان': 'Address',
    'كلمة المرور الحالية': 'Current password', 'الجديدة (6 أحرف على الأقل)': 'New (at least 6 characters)', 'المساعدة': 'Help',
    'إعادة الجولة التعريفية': 'Restart the guided tour', 'إظهار الملاحظات المخفية': 'Show hidden notes', 'الدعم الفني': 'Technical support',
    'تواصل مع كيرو على واتساب': 'Contact Kiro on WhatsApp', 'نوع النشاط والقوالب الجاهزة': 'Business type & ready-made templates',
    'تطبيق القالب المختار': 'Apply selected template', 'تطبيق قالب نشاط': 'Apply a business template', 'طبّق القالب': 'Apply template',
    # ---- الكاشير ----
    'سلة الفاتورة الحالية': 'Current invoice cart', 'سلة المبيعات فارغة': 'The cart is empty', 'إفراغ السلة': 'Clear cart', 'الخدمات السريعة (المفضلة)': 'Quick services (favorites)',
    'خدمات تشطيب إضافية': 'Extra finishing services', '— اختر من خدمات التشطيب —': '— Choose a finishing service —', '+ إضافة': '+ Add', 'خدمة يدوية (الاسم)': 'Manual service (name)',
    'إجمالي البنود:': 'Items subtotal:', 'المجموع الكلي:': 'Grand total:', 'حفظ وطباعة 🖨️': 'Save & print 🖨️', 'حفظ فقط': 'Save only',
    'فواتير الوردية الحالية (إدارة الحالة + الواتساب + الحذف)': "This shift's invoices (status + WhatsApp + delete)",
    'لا توجد فواتير مسجلة في ورديتك حتى الآن': 'No invoices recorded in your shift yet', '🔍 اكتب الاسم أو اضغط F2': '🔍 Type the name or press F2',
    'إدراج البند في السلة': 'Add item to cart', 'الخدمة / الخامة:': 'Service / material:', 'الكمية:': 'Quantity:', 'نوع التسعير:': 'Pricing type:',
    'تلقائي حسب الكمية': 'Auto by quantity', 'قطاعي (يدوي)': 'Retail (manual)', 'جملة (يدوي)': 'Wholesale (manual)',
    'الطول (سم):': 'Height (cm):', 'العرض (سم):': 'Width (cm):', 'الهاتف': 'Phone', 'المتبقي': 'Remaining',
    '⚠️ متبقي سابق على هذا العميل:': '⚠️ Previous balance for this customer:', 'تسعير الكتب والمذكرات والتغليف': 'Books, notes & binding pricing',
    'إدراج المذكرات بالسلة': 'Add notes to cart', 'اسم الكتاب / المذكرة:': 'Book / note name:', 'عدد الأوراق': 'Page count', 'سعر الورقة': 'Price per page',
    'نوع التغليف:': 'Binding type:', 'تحديث الحالة وإرسال إشعار طباعة': 'Update status & send printing notice', '🖨️ طباعة': '🖨️ Print', '✂️ تجهيز': '✂️ Finishing', '📦 جاهز': '📦 Ready',
    '🌺 شكر': '🌺 Thanks', 'تعليق': 'Hold', 'سلك عادي، حراري...': 'Wire, thermal...',
    # ---- الدخول ----
    'دخول إلى النظام': 'Sign in', 'أدخل اسم المستخدم': 'Enter username', 'جاري مزامنة الوقت...': 'Syncing time...',
    'تسجيل الدخول — منظومة كيرو السحابية لإدارة المطابع': 'Sign in — KIRO cloud print management',
    'المنظومة السحابية الموحدة لإدارة المطابع ونقاط البيع': 'Unified cloud platform for print shops & POS',
    # ---- الفروع ----
    'إضافة فرع جديد': 'Add a new branch', 'اسم الفرع *': 'Branch name *', 'هاتف الفرع': 'Branch phone', 'حساب أدمن الفرع (يشوف فرعه بس)': 'Branch admin account (sees only their branch)',
    'حساب كاشير الفرع (اختياري — تقدر تضيف غيره بعدين)': 'Branch cashier account (optional — add more later)', 'إنشاء الفرع وحساباته': 'Create branch & accounts',
    'نوع نشاط الفرع (يحمّل خدمات جاهزة)': 'Branch business type (loads ready services)', 'مبيعات اليوم': "Today's sales", 'إجمالي المبيعات': 'Total sales',
    'مبيعات كل الفروع': 'All branches sales', 'المحصّل': 'Collected', 'فواتير / موظفين': 'Invoices / staff', 'مصروفات': 'Expenses', 'ديون': 'Debts',
    'انسخ الخدمات والأسعار وتصميم الفاتورة من الفرع الرئيسي بدل القالب': 'Copy services, prices & invoice design from the main branch instead of a template',
    # ---- السوبر أدمن ----
    'قائمة المطابع': 'Shops list', 'الخطط والأسعار': 'Plans & pricing', 'إضافة مطبعة جديدة': 'Add a new shop', 'إنشاء المطبعة': 'Create shop', 'تجديد': 'Renew',
    'مدى الحياة': 'Lifetime', 'دائم': 'Lifetime', '✅ نشط': '✅ Active', '❌ منتهي': '❌ Expired', '⛔ معلق': '⛔ Suspended', '⚠️ فترة سماح': '⚠️ Grace period',
    '⏳ بدون اشتراك': '⏳ No subscription', 'اسم الخطة': 'Plan name', 'إضافة الخطة': 'Add plan', 'عدد الفروع': 'Branches', 'عدد الفروع المسموح بها': 'Allowed branches',
    'عدد الفروع المسموح بها (أكثر من 1 = حساب سلسلة)': 'Allowed branches (more than 1 = chain account)', 'نوع النشاط (يحمّل خدمات جاهزة)': 'Business type (loads ready services)',
    'إعادة تعيين كلمة مرور الأدمن': 'Reset admin password', 'حالة الاشتراك': 'Subscription status', 'المطابع المشتركة': 'Subscribed shops', 'اشتراكات نشطة': 'Active subscriptions',
    'تغيير كلمة مرور السوبر أدمن': 'Change super-admin password', 'تواصل للتجديد فورا': 'Contact us to renew now',
    # ---- الرسائل (Toasts / Flash) ----
    'السلة فارغة!': 'The cart is empty!', 'يرجى إدخال اسم العميل': 'Please enter the customer name', 'فشل الاتصال بالسيرفر': 'Could not reach the server',
    'تعذر الاتصال بالسيرفر': 'Could not reach the server', 'تمت إضافة البند للسلة ✅': 'Item added to cart ✅', 'اختر خدمة تشطيب أولاً': 'Choose a finishing service first',
    'اكتب اسم الخدمة وسعرها': 'Enter the service name and price', 'تم تحميل الفاتورة للتعديل ✏️': 'Invoice loaded for editing ✏️',
    'تم التسجيل ✅': 'Recorded ✅', 'اختر الخدمة الأول.': 'Choose a service first.', 'اكتب العدد.': 'Enter the count.', 'تم حفظ تصميم الفاتورة — هيظهر على كل الفواتير الجاية والقديمة.': 'Invoice design saved — it applies to all new and old invoices.',
    'تمت إعادة التصميم الافتراضي.': 'Default design restored.', 'تم حفظ بيانات المطبعة.': 'Shop details saved.', 'تم تغيير كلمة المرور بنجاح.': 'Password changed successfully.',
    '❌ كلمة المرور الحالية غير صحيحة.': '❌ Current password is incorrect.', '❌ اسم المستخدم أو كلمة المرور غير صحيحة!': '❌ Incorrect username or password!',
    '🔒 يرجى تسجيل الدخول أولاً!': '🔒 Please sign in first!', '🚫 ليس لديك صلاحية الوصول!': '🚫 You do not have access!',
    'انتهت الجلسة. سجّل الدخول من جديد.': 'Session expired. Please sign in again.', 'انتهت صلاحية الصفحة. حدّث الصفحة (F5) ثم أعد المحاولة.': 'Page expired. Refresh (F5) and try again.',
    'تم تسجيل السداد ✅': 'Payment recorded ✅', 'تمت إضافة المديونية القديمة ✅': 'Old balance added ✅', 'اكتب اسم العميل والمبلغ.': 'Enter the customer name and amount.',
    'اكتب مبلغ السداد.': 'Enter the payment amount.', 'تم حفظ الفاتورة بنجاح ✅': 'Invoice saved ✅', 'اختر العميل واكتب المبلغ بشكل صحيح!': 'Choose the customer and enter a valid amount!',
    'لا توجد مديونيات مفتوحة لهذا العميل.': 'No open debts for this customer.', 'اكتب سبب التعديل أولاً.': 'Enter the reason for the edit first.',
    'اكتب سبب التعديل ليتم قيده في سجل الرقابة.': 'Enter the edit reason so it can be logged.', 'مفيش صلاحية تعديل لهذه الفاتورة.': 'No permission to edit this invoice.',
    'الفاتورة غير موجودة!': 'Invoice not found!', 'تم حذف الفاتورة': 'Invoice deleted', 'تم': 'Done',
    # ---- تأكيدات ----
    'تأكيد الإجراء': 'Confirm action', 'نعم، متأكد': 'Yes, I am sure', 'تأكيد الحذف': 'Confirm deletion', 'إفراغ السلة؟': 'Clear the cart?',
    'هتتمسح كل البنود المضافة للفاتورة الحالية. متأكد؟': 'All items in the current invoice will be removed. Sure?', 'نعم، فضّي السلة': 'Yes, clear it',
    'حفظ التعديل': 'Save edit', 'احفظ التعديل': 'Save edit',
    # ---- الجولة التعريفية ----
    'أهلاً بيك في لوحة الإدارة 👋': 'Welcome to the admin panel 👋', 'أهلاً بيك في شاشة الكاشير 👋': 'Welcome to the cashier screen 👋', 'ابدأ الشغل': 'Start working', 'تخطي': 'Skip',
    'القائمة الرئيسية': 'Main menu', 'تصميم الفاتورة 🎨': 'Invoice design 🎨', 'الموظفون': 'Staff', 'سلة الفاتورة': 'Invoice cart', 'حفظ وطباعة': 'Save & print',
    'خدمات التشطيب': 'Finishing services', 'جاهز! 🚀': 'Ready! 🚀', 'مساعدتك دايماً هنا': 'Help is always here',
    'أهلاً بيك يا صاحب الفروع 👋': 'Welcome, branch owner 👋', 'الأرقام الإجمالية': 'Overall numbers', 'كارت لكل فرع': 'A card per branch', 'إضافة فرع': 'Add branch',
}


EN.update({
    'ابحث، اطبع، عدّل أو احذف أي فاتورة': 'Search, print, edit or delete any invoice',
    'غيّر الشكل والمقاس والبيانات وشوف النتيجة فوراً': 'Change the look, size and details and see the result instantly',
    'الأسعار والخامات وحد الطلب': 'Prices, materials and reorder levels',
    'الديون المفتوحة والعملاء المتميزين': 'Open debts and VIP customers',
    'الحساب الجاري المتبادل مع المطابع والوكالات الشريكة': 'Running account with partner shops and agencies',
    'كل ما يخرج من الخزينة': 'Everything paid out of the cash box',
    'حسابات الدخول والرواتب والسلف': 'Login accounts, salaries and advances',
    'أساليب التجليد وخدمات التشطيب الثابتة اللي يختار منها الكاشير': 'Binding methods and fixed finishing services cashiers can pick from',
    'كل تعديل وحذف بيتسجل هنا بالاسم والسبب': 'Every edit and deletion is logged here with name and reason',
    'بيانات المطبعة وحسابك': 'Shop details and your account',
    'أنا': 'Me',
})

# أنماط بها أرقام (تطبَّق في المتصفح): (regex, replacement)
EN_PATTERNS = [
    (r'(\d+) خدمة', r'\1 services'), (r'(\d+) فاتورة', r'\1 invoices'),
    (r'(\d+) / (\d+) فروع', r'\1 / \2 branches'), (r'صفحة (\d+) من (\d+)', r'Page \1 of \2'),
]


def translate(msg, lang):
    if lang == 'en':
        return EN.get(msg, msg)
    return msg
