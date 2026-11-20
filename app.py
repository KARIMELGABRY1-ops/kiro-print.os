# -*- coding: utf-8 -*-
import os
import secrets
import io
import hashlib
import copy
from datetime import datetime, timedelta
from types import SimpleNamespace
import pytz
import base64
from functools import wraps
import urllib.parse
import sqlite3
import json
import sys
import re

from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify, send_file, abort,
                   Response, get_flashed_messages)
from markupsafe import Markup
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from presets import PRESETS, DEFAULT_PRESET, preset_choices
import i18n
from werkzeug.security import generate_password_hash, check_password_hash
import openpyxl
from sqlalchemy import text, func, or_

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
_TPL_DIR = os.path.join(BASE_DIR, 'templates')
# القوالب داخل templates/ (ولو الملفات بجوار app.py مباشرة بيشتغل برضو)
app = Flask(__name__, template_folder=_TPL_DIR if os.path.isdir(_TPL_DIR) else BASE_DIR,
            static_folder=os.path.join(BASE_DIR, 'static'), static_url_path='/static')
app.config['JSON_AS_ASCII'] = False
try:
    app.json.ensure_ascii = False
except Exception:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _load_secret_key():
    """مفتاح الجلسات: من متغير البيئة، وإلا يُولَّد مرة واحدة ويُحفظ بجوار app.py
    (بدل المفتاح الثابت المكتوب داخل الكود)."""
    env = os.environ.get('SECRET_KEY')
    if env:
        return env
    path = os.path.join(BASE_DIR, '.secret_key')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            k = f.read().strip()
        if k:
            return k
    except OSError:
        pass
    k = secrets.token_hex(32)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(k)
    except FileExistsError:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                k = f.read().strip() or k
        except OSError:
            pass
    except OSError:
        pass
    return k


app.secret_key = _load_secret_key()
app.permanent_session_lifetime = timedelta(minutes=180)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

DB_PATH = os.environ.get('DATABASE_PATH') or os.path.join(BASE_DIR, 'kiro_platform.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
EGYPT_TZ = pytz.timezone('Africa/Cairo')
GRACE_DAYS = 7

# ------------------------------ أدوات مساعدة ------------------------------
def sanitize_egyptian_phone(phone_input):
    """تنظيف وتوحيد رقم الهاتف وتحويله للصيغة الدولية الصحيحة للواتساب بدون 404"""
    if not phone_input:
        return None
    raw = str(phone_input).strip()
    # تحويل الأرقام العربية المشرقية إلى إنجليزية
    for ar, en in zip("٠١٢٣٤٥٦٧٨٩", "0123456789"):
        raw = raw.replace(ar, en)
    # استخراج الأرقام فقط وتجاهل أي حروف أو مسافات أو رموز
    digits = re.sub(r'\D', '', raw)
    
    if not digits:
        return None
    
    # ضبط كود الدولة لمصر (+20)
    if digits.startswith('002'):
        digits = digits[2:]
    elif digits.startswith('01'):
        digits = '2' + digits
    elif len(digits) == 10 and digits.startswith('1'):
        digits = '20' + digits

    return digits

def to_float(val, default=0.0):
    try:
        v = float(val)
        return v if v == v else default
    except (TypeError, ValueError):
        return default

def to_int(val, default=0):
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default

def now():
    return datetime.now(EGYPT_TZ).replace(tzinfo=None)

def now_str():
    return now().strftime('%Y-%m-%d %I:%M:%S %p')

def today_str():
    return now().strftime('%Y-%m-%d')

def generate_secure_pin(shop_id):
    rand_part = secrets.token_hex(3).upper()
    rand_num = secrets.randbelow(8999) + 1000
    return f"KP{shop_id:03d}-{rand_num}-{rand_part}"

@app.context_processor
def global_ctx():
    shop_name = session.get('shop_name') or 'منظومة كيرو السحابية لإدارة المطابع'
    return {'press_name': shop_name, 'current_year': now().year}

@app.template_filter('currency')
def currency_filter(value):
    try:
        return f"{value:,.2f} ج.م"
    except Exception:
        return "0.00 ج.م"

# ------------------------------ نماذج قاعدة البيانات ------------------------------
class SuperAdmin(db.Model):
    __tablename__ = 'super_admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Plan(db.Model):
    __tablename__ = 'plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, default=0.0)
    duration_days = db.Column(db.Integer, default=30)
    max_cashiers = db.Column(db.Integer, default=3)
    max_branches = db.Column(db.Integer, default=1)
    is_lifetime = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

class PrintShop(db.Model):
    __tablename__ = 'print_shops'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    owner_name = db.Column(db.String(120), default='')
    phone = db.Column(db.String(30), default='')
    address = db.Column(db.String(255), default='')
    is_suspended = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, nullable=True, index=True)   # فرع تابع لمطبعة رئيسية
    max_branches = db.Column(db.Integer, default=1)               # عدد الفروع المسموح بها (للحساب الرئيسي)
    business_type = db.Column(db.String(30), default='general')
    created_at = db.Column(db.DateTime, default=now)
    users = db.relationship('User', backref='shop', lazy='dynamic')

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'))
    plan = db.relationship('Plan')
    starts_at = db.Column(db.DateTime, default=now)
    ends_at = db.Column(db.DateTime, nullable=True)
    is_lifetime = db.Column(db.Boolean, default=False)
    amount_paid = db.Column(db.Float, default=0.0)
    notes = db.Column(db.String(255), default='')

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='cashier')
    barcode_token = db.Column(db.String(64), nullable=True)
    base_salary = db.Column(db.Float, default=0.0)
    bonus = db.Column(db.Float, default=0.0)
    advances = db.Column(db.Float, default=0.0)
    deductions = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)

class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    cost_price = db.Column(db.Float, default=0.0)
    price_reg = db.Column(db.Float, default=0.0)
    price_bulk = db.Column(db.Float, default=0.0)
    bulk_threshold = db.Column(db.Float, default=0.0)
    threshold = db.Column(db.Float, default=10.0)
    stock = db.Column(db.Float, default=-1.0)
    unit_name = db.Column(db.String(50), default='بالقطعة')
    is_banner = db.Column(db.Boolean, default=False)
    is_favorite = db.Column(db.Boolean, default=False)
    is_measurement_based = db.Column(db.Boolean, default=False)
    price_per_sqm = db.Column(db.Float, default=0.0)

class Binding(db.Model):
    __tablename__ = 'bindings'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price_per_unit = db.Column(db.Float, default=0.0)

class PremiumCustomer(db.Model):
    __tablename__ = 'premium_customers'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), default='')
    discount_percentage = db.Column(db.Float, default=0.0)
    tier_name = db.Column(db.String(50), default='')

class B2BPartner(db.Model):
    __tablename__ = 'b2b_partners'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    partner_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), default='')
    notes = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=now)

class B2BTransaction(db.Model):
    __tablename__ = 'b2b_transactions'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('b2b_partners.id'), index=True, nullable=False)
    trans_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    date_str = db.Column(db.String(50), nullable=False)
    created_by = db.Column(db.String(100), default='')
    sync_token = db.Column(db.String(64), unique=True, default=lambda: secrets.token_hex(16))

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    cashier_name = db.Column(db.String(100), default='الإدارة')
    created_by = db.Column(db.String(100), default='الإدارة')
    date_str = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, default='')

class ShiftLog(db.Model):
    __tablename__ = 'shift_logs'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    cashier_username = db.Column(db.String(50), nullable=False)
    login_time = db.Column(db.String(50), nullable=False)
    logout_time = db.Column(db.String(50), default='نشط حالياً')
    collected_cash = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='مفتوح')

class CashierLog(db.Model):
    __tablename__ = 'cashier_logs'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    cashier_username = db.Column(db.String(50), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_str = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.String(255), default='')

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    action = db.Column(db.String(100), nullable=False)
    invoice_token = db.Column(db.String(50), default='')
    action_by = db.Column(db.String(100), default='')
    reason = db.Column(db.String(255), default='')
    timestamp = db.Column(db.DateTime, default=now)

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    token = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), default='عميل نقدي')
    customer_phone = db.Column(db.String(50), default='')
    cashier_username = db.Column(db.String(50), default='')
    cashier_full_name = db.Column(db.String(100), default='')
    date_str = db.Column(db.String(50), nullable=False)
    subtotal = db.Column(db.Float, default=0.0)
    design_price = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, default=0.0)
    deposit = db.Column(db.Float, default=0.0)
    remaining = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(50), default='نقدي')
    delivery_status = db.Column(db.String(50), default='قيد التنفيذ')
    notes = db.Column(db.Text, default='')
    cutting_qty = db.Column(db.Integer, default=0)
    cutting_price = db.Column(db.Float, default=0.0)
    cutting_total = db.Column(db.Float, default=0.0)
    solofan_qty = db.Column(db.Integer, default=0)
    solofan_price = db.Column(db.Float, default=0.0)
    solofan_total = db.Column(db.Float, default=0.0)
    beshr_qty = db.Column(db.Integer, default=0)
    beshr_price = db.Column(db.Float, default=0.0)
    beshr_total = db.Column(db.Float, default=0.0)
    extras_json = db.Column(db.Text, default='[]')      # خدمات التشطيب الإضافية [{name, qty, price, total}]
    extras_total = db.Column(db.Float, default=0.0)
    customer_tier = db.Column(db.String(60), default='')

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    invoice_token = db.Column(db.String(50), nullable=False)
    service_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    qty = db.Column(db.Float, default=1)
    height = db.Column(db.Float, default=0.0)
    width = db.Column(db.Float, default=0.0)
    unit_price = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)


class ShopConfig(db.Model):
    """إعدادات عامة للمطبعة (JSON): نوع النشاط، فئات العملاء، صلاحيات الكاشير."""
    __tablename__ = 'shop_configs'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), unique=True, index=True, nullable=False)
    data = db.Column(db.Text, default='{}')


class Customer(db.Model):
    """سجل العميل التلقائي: يُنشأ بمجرد كتابة اسمه في فاتورة، وتتجمع عليه الإحصائيات."""
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    name = db.Column(db.String(100), nullable=False, index=True)
    phone = db.Column(db.String(50), default='')
    old_balance = db.Column(db.Float, default=0.0)        # مديونية قديمة بدون فاتورة
    invoices_count = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0.0)
    notes = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=now)


class Payment(db.Model):
    """كل عملية سداد أو إضافة مديونية قديمة بتاريخها ووقتها."""
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False, index=True)
    invoice_token = db.Column(db.String(50), default='')
    kind = db.Column(db.String(20), default='invoice')   # invoice | old_balance | old_balance_add
    amount = db.Column(db.Float, nullable=False)
    date_str = db.Column(db.String(50), nullable=False)
    created_by = db.Column(db.String(100), default='')
    note = db.Column(db.String(255), default='')


class FinishingService(db.Model):
    """خدمات التشطيب الثابتة (يضيفها الأدمن ويختار منها الكاشير)."""
    __tablename__ = 'finishing_services'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)


class QuickSale(db.Model):
    """بيع سريع بدون فاتورة (مثل التصوير بالورقة): عدد + سعر + هالك."""
    __tablename__ = 'quick_sales'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), index=True, nullable=False)
    service_id = db.Column(db.Integer, default=0)
    name = db.Column(db.String(150), nullable=False)
    qty = db.Column(db.Float, default=0.0)
    wasted = db.Column(db.Float, default=0.0)
    unit_price = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    date_str = db.Column(db.String(50), nullable=False)
    created_by = db.Column(db.String(100), default='')
    note = db.Column(db.String(255), default='')



class InvoiceSetting(db.Model):
    """إعدادات تصميم الفاتورة لكل مطبعة (JSON) — يتحكم فيها الأدمن بالكامل."""
    __tablename__ = 'invoice_settings'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('print_shops.id'), unique=True, index=True, nullable=False)
    data = db.Column(db.Text, default='{}')
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)


# ------------------------------ حالات الطلب ------------------------------
DELIVERY_STATUSES = ['قيد التنفيذ', 'دخلت الطباعة', 'في التجهيز', 'جاهز للاستلام', 'شكراً لتعاملكم']

# ------------------------------ تصميم الفاتورة (مرن بالكامل) ------------------------------
PAPERS = {
    'thermal80': {'label': 'حراري 80 مم', 'w': 80, 'h': 0, 'fs': 12.5, 'margin': 2},
    'thermal58': {'label': 'حراري 58 مم', 'w': 58, 'h': 0, 'fs': 11, 'margin': 1.5},
    'a5': {'label': 'A5', 'w': 148, 'h': 210, 'fs': 12.5, 'margin': 8},
    'a4': {'label': 'A4', 'w': 210, 'h': 297, 'fs': 14, 'margin': 12},
    'custom': {'label': 'مقاس مخصص', 'w': 80, 'h': 0, 'fs': 12.5, 'margin': 3},
}
FONTS = {
    'tajawal': ("تجوال (حديث)", "'Tajawal','Segoe UI',Tahoma,Arial,sans-serif"),
    'cairo': ("القاهرة", "'Cairo','Segoe UI',Tahoma,Arial,sans-serif"),
    'almarai': ("المراعي", "'Almarai','Segoe UI',Tahoma,Arial,sans-serif"),
    'system': ("خط النظام", "'Segoe UI',Tahoma,Arial,sans-serif"),
    'mono': ("آلة كاتبة (Mono)", "'Courier New',Courier,monospace"),
}

INVOICE_DEFAULTS = {
    'paper': 'thermal80', 'custom_w': 80, 'custom_h': 0, 'orientation': 'portrait',
    'margin': -1, 'scale': 100, 'font': 'tajawal', 'weight': 'bold',
    'color_text': '#000000', 'color_muted': '#333333', 'color_accent': '#b91c1c',
    'color_head_bg': '#f1f1f1', 'color_line': '#000000', 'color_paper': '#ffffff',
    'border_style': 'dashed', 'align': 'center', 'row_density': 'normal',
    'title': '', 'subtitle': 'فاتورة مبيعات وخدمات إلكترونية', 'header_lines': '',
    'logo': '', 'logo_size': 18,
    'currency': 'ج.م', 'decimals': 2,
    'footer_text': 'شكراً لثقتكم الغالية بنا 🌟', 'terms': '', 'footer_lines': '',
    'brand_text': 'منظومة كيرو السحابية لإدارة المطابع KIRO Print OS',
    'qr_size': 22, 'signatures': 'auto',
    'show': {
        'logo': False, 'title': True, 'subtitle': True, 'header_lines': True,
        'number': True, 'date': True, 'customer': True, 'phone': True,
        'cashier': True, 'payment': True, 'status': True, 'tier': True,
        'col_index': True, 'col_qty': True, 'col_price': True, 'dims': True,
        'design': True, 'extras': True, 'discount': True, 'paid': True, 'remaining': True,
        'debt_stamp': True, 'notes': True, 'terms': True, 'qr': True,
        'footer': True, 'brand': True, 'copyright': True,
    },
    'labels': {
        'doc': 'رقم الفاتورة', 'date': 'التاريخ', 'customer': 'العميل', 'phone': 'الهاتف',
        'cashier': 'الكاشير المسؤول', 'payment': 'طريقة الدفع', 'status': 'حالة الطلب', 'tier': 'فئة العميل',
        'c_index': '#', 'c_item': 'البيان', 'c_qty': 'كمية', 'c_price': 'سعر', 'c_total': 'إجمالي',
        'subtotal': 'إجمالي الخدمات', 'design': 'مصاريف التصميم',
        'cutting': '✂️ القص والتجهيز', 'solofan': '📦 السولفان', 'beshr': '📌 تجهيز بشر',
        'discount': 'الخصم الممنوح', 'grand': 'المجموع الكلي', 'paid': 'المدفوع مقدماً',
        'remaining': 'المتبقي طرفكم', 'debt': '⚠️ متبقي مديونية واجبة السداد',
        'notes': 'ملاحظات الفاتورة', 'terms': 'الشروط والأحكام',
        'sig_customer': 'توقيع واستلام العميل', 'sig_shop': 'اعتماد مسؤول المطبعة',
        'dims': 'المقاس', 'cm': 'سم',
    },
}
_ENUMS = {
    'paper': tuple(PAPERS), 'orientation': ('portrait', 'landscape'), 'font': tuple(FONTS),
    'weight': ('normal', 'bold', 'black'), 'border_style': ('solid', 'dashed', 'dotted', 'none'),
    'align': ('center', 'right', 'left'), 'row_density': ('compact', 'normal', 'relaxed'),
    'signatures': ('auto', 'on', 'off'),
}
_TEXT_LIMITS = {'title': 120, 'subtitle': 120, 'header_lines': 600, 'currency': 12,
                'footer_text': 300, 'terms': 1500, 'footer_lines': 400, 'brand_text': 160}
_COLOR_KEYS = ('color_text', 'color_muted', 'color_accent', 'color_head_bg', 'color_line', 'color_paper')
_HEX = re.compile(r'^#[0-9a-fA-F]{6}$')
_LOGO = re.compile(r'^data:image/(png|jpeg|jpg|webp|gif);base64,[A-Za-z0-9+/=]+$')


def _num(val, lo, hi, default, integer=False):
    try:
        v = float(val)
        if v != v:
            return default
    except (TypeError, ValueError):
        return default
    v = max(lo, min(hi, v))
    return int(round(v)) if integer else round(v, 2)


def sanitize_invoice_settings(raw):
    """يقبل أي JSON من المتصفح ويُرجع إعدادات سليمة 100% (قيم مسموحة ومقاسات منطقية)."""
    raw = raw if isinstance(raw, dict) else {}
    S = copy.deepcopy(INVOICE_DEFAULTS)
    for k, allowed in _ENUMS.items():
        if raw.get(k) in allowed:
            S[k] = raw[k]
    for k, lim in _TEXT_LIMITS.items():
        if k in raw and isinstance(raw[k], str):
            S[k] = raw[k].replace('\r', '').strip()[:lim] if k != 'terms' else raw[k].replace('\r', '')[:lim].strip()
    for k in _COLOR_KEYS:
        if isinstance(raw.get(k), str) and _HEX.match(raw[k]):
            S[k] = raw[k].lower()
    S['custom_w'] = _num(raw.get('custom_w'), 30, 400, S['custom_w'])
    S['custom_h'] = _num(raw.get('custom_h'), 0, 800, S['custom_h'])
    S['margin'] = _num(raw.get('margin'), -1, 30, S['margin'])
    S['scale'] = _num(raw.get('scale'), 60, 180, S['scale'], integer=True)
    S['logo_size'] = _num(raw.get('logo_size'), 6, 70, S['logo_size'])
    S['qr_size'] = _num(raw.get('qr_size'), 12, 60, S['qr_size'])
    S['decimals'] = _num(raw.get('decimals'), 0, 3, S['decimals'], integer=True)
    logo = raw.get('logo')
    if isinstance(logo, str) and (logo == '' or (len(logo) <= 600000 and _LOGO.match(logo))):
        S['logo'] = logo
    rs = raw.get('show') if isinstance(raw.get('show'), dict) else {}
    for k in S['show']:
        if k in rs:
            S['show'][k] = bool(rs[k])
    rl = raw.get('labels') if isinstance(raw.get('labels'), dict) else {}
    for k in S['labels']:
        if isinstance(rl.get(k), str):
            S['labels'][k] = rl[k].strip()[:60]
    return S


def get_invoice_settings(sid):
    row = InvoiceSetting.query.filter_by(shop_id=sid).first()
    data = {}
    if row and row.data:
        try:
            data = json.loads(row.data)
        except ValueError:
            data = {}
    return sanitize_invoice_settings(data)


def invoice_layout(S):
    """مقاسات كل نوع ورق بعد تطبيق إعدادات الأدمن (مم / px)."""
    out = {}
    for k, p in PAPERS.items():
        w, h = p['w'], p['h']
        if k == 'custom':
            w, h = S['custom_w'], S['custom_h']
        if S['orientation'] == 'landscape' and k in ('a4', 'a5'):
            w, h = h, w
        m = S['margin'] if S['margin'] >= 0 else p['margin']
        out[k] = {'w': w, 'h': h, 'm': m, 'fs': round(p['fs'] * S['scale'] / 100.0, 2),
                  'label': p['label'], 'thermal': k.startswith('thermal') or (k == 'custom' and w <= 100)}
    return out


def make_fmt(S):
    d = S['decimals']
    def fmt(v):
        try:
            return f"{float(v or 0):,.{d}f}"
        except (TypeError, ValueError):
            return f"{0:,.{d}f}"
    return fmt


def sample_invoice():
    """فاتورة تجريبية لمعاينة التصميم قبل الحفظ."""
    items = [
        SimpleNamespace(name='طباعة بنر فلكس', qty=2, height=200, width=100, unit_price=150.0, total=300.0),
        SimpleNamespace(name='كروت شخصية (علبة)', qty=3, height=0, width=0, unit_price=85.0, total=255.0),
        SimpleNamespace(name='استيكر لامع', qty=10, height=0, width=0, unit_price=12.5, total=125.0),
    ]
    inv = SimpleNamespace(token='A1B2C3D4', date_str=now_str(), customer_name='أحمد محمد', customer_phone='01012345678',
                          cashier_full_name=session.get('full_name') or 'الكاشير', cashier_username='',
                          payment_method='نقدي', delivery_status='قيد التنفيذ',
                          subtotal=680.0, design_price=50.0, discount=30.0,
                          cutting_qty=2, cutting_price=10.0, cutting_total=20.0,
                          solofan_qty=0, solofan_price=0.0, solofan_total=0.0,
                          beshr_qty=0, beshr_price=0.0, beshr_total=0.0,
                          extras_json=json.dumps([{'name': 'تغليف هدية', 'qty': 1, 'price': 25.0, 'total': 25.0}], ensure_ascii=False),
                          extras_total=25.0, customer_tier='عميل مميز',
                          grand_total=745.0, deposit=500.0, remaining=245.0,
                          notes='التسليم خلال يومين عمل. الألوان حسب العينة المعتمدة.')
    return inv, items


def make_qr(url, box=6):
    if not QR_AVAILABLE:
        return None
    try:
        qr = qrcode.QRCode(box_size=box, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def render_receipt(invoice, items, shop, S, preview=False, qr_url=None):
    try:
        extras = json.loads(getattr(invoice, 'extras_json', '') or '[]')
    except ValueError:
        extras = []
    return render_template(
        'receipt.html', invoice=invoice, items=items, shop=shop, S=S, extras=extras,
        presets=invoice_layout(S), fmt=make_fmt(S), fonts={k: v[1] for k, v in FONTS.items()},
        qr_base64=make_qr(qr_url) if (qr_url and S['show']['qr']) else None,
        press_name=(S['title'] or (shop.name if shop else 'المطبعة')),
        preview=preview,
        can_design=(session.get('role') in ('shop_admin', 'owner') and bool(shop) and session.get('shop_id') == shop.id))


# ------------------------------ اللغة (i18n) ------------------------------
LANGS = {'ar': {'name': 'العربية', 'dir': 'rtl'}, 'en': {'name': 'English', 'dir': 'ltr'}}


def current_lang():
    lang = session.get('lang') or request.cookies.get('lang') or 'ar'
    return lang if lang in LANGS else 'ar'


@app.context_processor
def lang_context():
    lg = current_lang()
    return {'lang': lg, 'dir': LANGS[lg]['dir'], 'langs': LANGS,
            't': lambda msg: i18n.translate(msg, lg)}


@app.route('/lang/<code>')
def set_lang(code):
    if code in LANGS:
        session['lang'] = code
    ref = request.referrer or ''
    back = '/' + ref.split('/', 3)[3] if ref.startswith(request.host_url) and len(ref.split('/', 3)) > 3 else '/'
    resp = redirect(back)
    resp.set_cookie('lang', code if code in LANGS else 'ar', max_age=3600 * 24 * 365, samesite='Lax')
    return resp


@app.route('/i18n/<code>.js')
def i18n_js(code):
    data = i18n.EN if code == 'en' else {}
    pats = [[p, re.sub(r'\\(\d)', r'$\1', r)] for p, r in i18n.EN_PATTERNS] if code == 'en' else []
    body = ('window.I18N=' + json.dumps(data, ensure_ascii=False) + ';window.I18N_LANG=' + json.dumps(code)
            + ';window.I18N_PATTERNS=' + json.dumps(pats, ensure_ascii=False) + ';')
    return Response(body, mimetype='application/javascript', headers={'Cache-Control': 'public, max-age=3600'})


# ------------------------------ إعدادات المطبعة (JSON) ------------------------------
CONFIG_DEFAULTS = {
    'business_type': DEFAULT_PRESET,
    'tiers': [{'name': 'عميل مميز', 'min_invoices': 20, 'min_spent': 300.0, 'discount': 0.0}],
    'cashier_edit': 'own_today',     # off | own_today | all
    'cashier_delete': True,
}


def _sanitize_config(raw):
    raw = raw if isinstance(raw, dict) else {}
    cfg = copy.deepcopy(CONFIG_DEFAULTS)
    if raw.get('business_type') in PRESETS:
        cfg['business_type'] = raw['business_type']
    if raw.get('cashier_edit') in ('off', 'own_today', 'all'):
        cfg['cashier_edit'] = raw['cashier_edit']
    if 'cashier_delete' in raw:
        cfg['cashier_delete'] = bool(raw['cashier_delete'])
    if isinstance(raw.get('tiers'), list):
        tiers = []
        for t in raw['tiers'][:5]:
            if not isinstance(t, dict) or not str(t.get('name', '')).strip():
                continue
            tiers.append({'name': str(t['name']).strip()[:40],
                          'min_invoices': _num(t.get('min_invoices'), 0, 100000, 0, integer=True),
                          'min_spent': _num(t.get('min_spent'), 0, 100000000, 0),
                          'discount': _num(t.get('discount'), 0, 100, 0)})
        cfg['tiers'] = tiers
    return cfg


def get_config(sid):
    row = ShopConfig.query.filter_by(shop_id=sid).first()
    try:
        data = json.loads(row.data) if row and row.data else {}
    except ValueError:
        data = {}
    return _sanitize_config(data)


def save_config(sid, cfg):
    cfg = _sanitize_config(cfg)
    row = ShopConfig.query.filter_by(shop_id=sid).first()
    if not row:
        row = ShopConfig(shop_id=sid)
        db.session.add(row)
    row.data = json.dumps(cfg, ensure_ascii=False)
    return cfg


# ------------------------------ العملاء وفئات الولاء ------------------------------
ANON_CUSTOMER = 'عميل نقدي'


def norm_name(n):
    return ' '.join(str(n or '').split())[:100]


def recalc_customer(sid, name, phone=''):
    """يسجّل العميل تلقائياً (لو جديد) ويحدّث عدد فواتيره وإجمالي مشترياته."""
    name = norm_name(name)
    if not name or name == ANON_CUSTOMER:
        return None
    c = Customer.query.filter_by(shop_id=sid, name=name).first()
    if not c:
        c = Customer(shop_id=sid, name=name, phone=(phone or '')[:50])
        db.session.add(c)
    elif phone and not c.phone:
        c.phone = phone[:50]
    cnt, spent = db.session.query(func.count(Invoice.id), func.coalesce(func.sum(Invoice.grand_total), 0)).filter(
        Invoice.shop_id == sid, Invoice.customer_name == name).one()
    c.invoices_count, c.total_spent = int(cnt or 0), float(spent or 0)
    return c


def customer_tier(cfg, customer):
    """أعلى فئة يحققها العميل (عدد الفواتير ≥ الحد  و  إجمالي المشتريات ≥ الحد)."""
    if not customer:
        return None
    best = None
    for t in sorted(cfg.get('tiers', []), key=lambda x: (x['min_spent'], x['min_invoices'])):
        if customer.invoices_count >= t['min_invoices'] and customer.total_spent >= t['min_spent']:
            best = t
    return best


def customer_debt(sid, name):
    inv_debt = db.session.query(func.coalesce(func.sum(Invoice.remaining), 0)).filter(
        Invoice.shop_id == sid, Invoice.customer_name == name, Invoice.remaining > 0).scalar() or 0.0
    c = Customer.query.filter_by(shop_id=sid, name=name).first()
    return float(inv_debt), float(c.old_balance or 0.0 if c else 0.0)


# ------------------------------ الفروع (سلسلة مطابع) ------------------------------
def root_shop_id(sid):
    shop = db.session.get(PrintShop, sid)
    return (shop.parent_id or shop.id) if shop else sid


def group_shops(sid):
    root = root_shop_id(sid)
    return PrintShop.query.filter(or_(PrintShop.id == root, PrintShop.parent_id == root)).order_by(PrintShop.id).all()


ADMIN_ROLES = ('shop_admin', 'owner')


def apply_preset(sid, key):
    """يضيف خدمات وتشطيبات القالب (من غير تكرار الموجود). يرجع (عدد الخدمات، عدد التشطيبات)."""
    p = PRESETS.get(key)
    if not p:
        return 0, 0
    have = {s.name.strip().lower() for s in Service.query.filter_by(shop_id=sid).all()}
    added_s = 0
    for sv in p['services']:
        if sv['name'].lower() in have:
            continue
        db.session.add(Service(shop_id=sid, stock=-1.0, threshold=10.0, cost_price=0.0, **sv))
        added_s += 1
    have_f = {f.name.strip().lower() for f in FinishingService.query.filter_by(shop_id=sid).all()}
    added_f = 0
    for name, price in p['finishing']:
        if name.lower() in have_f:
            continue
        db.session.add(FinishingService(shop_id=sid, name=name, price=float(price)))
        added_f += 1
    cfg = get_config(sid)
    cfg['business_type'] = key
    save_config(sid, cfg)
    shop = db.session.get(PrintShop, sid)
    if shop:
        shop.business_type = key
    return added_s, added_f


# ------------------------------ حماية CSRF + رأس الواجهة المشتركة ------------------------------
def csrf_token():
    t = session.get('_csrf')
    if not t:
        t = secrets.token_hex(16)
        session['_csrf'] = t
    return t


@app.before_request
def _csrf_protect():
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        sent = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token') or ''
        good = session.get('_csrf', '')
        if not good or not secrets.compare_digest(sent.encode('utf-8'), good.encode('utf-8')):
            msg = 'انتهت صلاحية الصفحة. حدّث الصفحة (F5) ثم أعد المحاولة.'
            if request.headers.get('X-CSRF-Token') is not None or request.is_json:
                return jsonify({'success': False, 'message': msg, 'csrf': True}), 400
            flash('⚠️ ' + msg, 'error')
            return redirect(url_for('login_page'))


@app.context_processor
def ui_context():
    def ui_head():
        flashes = [{'c': c, 'm': m} for c, m in get_flashed_messages(with_categories=True)]
        data = json.dumps(flashes, ensure_ascii=False).replace('<', '\\u003c')
        return Markup(
            '<meta name="csrf-token" content="%s">'
            '<link rel="stylesheet" href="/static/ui.css?v=%s">'
            '<script src="/i18n/%s.js?v=%s"></script>'
            '<script src="/static/ui.js?v=%s"></script>'
            '<script type="application/json" id="flash-data">%s</script>'
            % (csrf_token(), _UI_VER, current_lang(), _UI_VER, _UI_VER, data))
    return {'ui_head': ui_head, 'csrf_token': csrf_token}


# ------------------------------ فحص الاشتراكات والصلاحيات ------------------------------
def subscription_state(shop_id):
    shop = db.session.get(PrintShop, shop_id)
    root = db.session.get(PrintShop, shop.parent_id) if (shop and shop.parent_id) else shop
    if (shop and shop.is_suspended) or (root and root.is_suspended):
        return 'suspended', None
    sub = Subscription.query.filter_by(shop_id=root.id if root else shop_id).order_by(Subscription.id.desc()).first()
    if not sub:
        return 'none', None
    if sub.is_lifetime:
        return 'active', sub
    if sub.ends_at and sub.ends_at >= now():
        return 'active', sub
    if sub.ends_at and (sub.ends_at + timedelta(days=GRACE_DAYS)) >= now():
        return 'grace', sub
    return 'expired', sub


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            wants_json = request.path.startswith('/api/') or request.is_json or request.method != 'GET' \
                or request.headers.get('X-CSRF-Token') is not None
            if 'logged_in' not in session:
                if wants_json:
                    return jsonify({'success': False, 'auth': True,
                                    'message': 'انتهت الجلسة. سجّل الدخول من جديد.'}), 401
                flash('🔒 يرجى تسجيل الدخول أولاً!', 'error')
                return redirect(url_for('login_page'))
            r = session.get('role')
            if r == 'super_admin':
                return f(*args, **kwargs)
            allowed = (role is None or r == role or (role == 'cashier' and r in ('shop_admin', 'owner', 'supervisor'))
                       or (role == 'shop_admin' and r == 'owner'))
            if not allowed:
                if wants_json:
                    return jsonify({'success': False, 'message': 'ليس لديك صلاحية لهذه العملية.'}), 403
                flash('🚫 ليس لديك صلاحية الوصول!', 'error')
                return redirect(url_for('login_page'))
            state, _ = subscription_state(session.get('shop_id'))
            if state not in ('active', 'grace'):
                return render_template('subscription_expired.html', state=state)
            return f(*args, **kwargs)
        return decorated
    return decorator

def super_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'super_admin':
            flash('🚫 هذه اللوحة مخصصة لإدارة كيرو فقط!', 'error')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def shop_id():
    sid = session.get('shop_id')
    if not sid:
        abort(403)
    return sid

# ------------------------------ مسارات الدخول والخروج ------------------------------
@app.route('/')
def login_page():
    if session.get('logged_in'):
        if session.get('role') == 'super_admin':
            return redirect(url_for('sa_dashboard'))
        if session.get('role') == 'owner':
            return redirect(url_for('owner_dashboard'))
        if session.get('role') == 'shop_admin':
            return redirect(url_for('shop_admin_dashboard'))
        return redirect(url_for('cashier_dashboard'))
    return render_template('login.html')

@app.route('/auth/login', methods=['POST'])
def auth_login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    sa = SuperAdmin.query.filter_by(username=username).first()
    if sa and check_password_hash(sa.password_hash, password):
        session.clear()
        session.update({'logged_in': True, 'username': username,
                        'full_name': 'إدارة كيرو', 'role': 'super_admin'})
        flash('👋 مرحباً بك في لوحة الإشراف العليا!', 'success')
        return redirect(url_for('sa_dashboard'))

    user = User.query.filter_by(username=username).first()
    if user and user.is_active and check_password_hash(user.password_hash, password):
        shop = db.session.get(PrintShop, user.shop_id)
        if not shop or shop.is_suspended:
            flash('🚫 حساب المطبعة موقوف حالياً.', 'error')
            return redirect(url_for('login_page'))
        state, _ = subscription_state(shop.id)
        if state not in ('active', 'grace'):
            flash('❌ انتهى اشتراك المطبعة. برجاء التجديد.', 'error')
            return redirect(url_for('login_page'))

        session.clear()
        session.update({'logged_in': True, 'username': username,
                        'full_name': user.full_name, 'role': user.role,
                        'shop_id': shop.id, 'shop_name': shop.name, 'user_id': user.id})
        if user.role in ('cashier', 'supervisor'):
            log = ShiftLog(shop_id=shop.id, cashier_username=username, login_time=now_str())
            db.session.add(log)
            db.session.commit()
            session['shift_log_id'] = log.id
        db.session.commit()
        flash(f'✅ أهلاً بك {user.full_name} — {shop.name}', 'success')
        return redirect(url_for({'owner': 'owner_dashboard', 'shop_admin': 'shop_admin_dashboard'}.get(user.role, 'cashier_dashboard')))

    flash('❌ اسم المستخدم أو كلمة المرور غير صحيحة!', 'error')
    return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    if session.get('role') in ('cashier', 'supervisor') and 'shift_log_id' in session:
        log = db.session.get(ShiftLog, session['shift_log_id'])
        if log and log.status == 'مفتوح':
            log.logout_time = now_str()
            log.status = 'مغلق'
            db.session.commit()
    session.clear()
    flash('تم تسجيل الخروج بنجاح.', 'success')
    return redirect(url_for('login_page'))

# ------------------------------ كارت الهوية ------------------------------
@app.route('/sa')
@super_admin_required
def sa_dashboard():
    shops = PrintShop.query.order_by(PrintShop.id.desc()).all()
    plans = Plan.query.order_by(Plan.id).all()
    rows = []
    for s in shops:
        state, sub = subscription_state(s.id)
        users_count = s.users.count()
        rows.append({'shop': s, 'state': state, 'sub': sub, 'users_count': users_count,
                     'branches': PrintShop.query.filter_by(parent_id=s.id).count() if not s.parent_id else 0})

    total_shops = PrintShop.query.count()
    active_shops = sum(1 for r in rows if r['state'] == 'active')
    suspended = sum(1 for r in rows if r['state'] == 'suspended')
    expiring_soon = sum(1 for r in rows if r['sub'] and not r['sub'].is_lifetime
                        and r['sub'].ends_at and now() <= r['sub'].ends_at
                        and r['sub'].ends_at <= now() + timedelta(days=7))
    revenue_total = db.session.query(func.coalesce(func.sum(Subscription.amount_paid), 0)).scalar() or 0.0
    revenue_month = db.session.query(func.coalesce(func.sum(Subscription.amount_paid), 0)).filter(
        Subscription.starts_at >= (now() - timedelta(days=30))).scalar() or 0.0
    lifetime_count = Subscription.query.filter_by(is_lifetime=True).count()
    sa_user = SuperAdmin.query.filter_by(username=session.get('username')).first()
    default_pw = bool(sa_user and check_password_hash(sa_user.password_hash, 'kiro2026'))
    return render_template('sa.html', default_pw=default_pw, rows=rows, plans=plans, presets=preset_choices('ar'),
                           total_shops=total_shops, active_shops=active_shops,
                           suspended=suspended, expiring_soon=expiring_soon,
                           revenue_total=revenue_total, revenue_month=revenue_month,
                           lifetime_count=lifetime_count)

@app.route('/sa/shops/add', methods=['POST'])
@super_admin_required
def sa_add_shop():
    name = request.form.get('name', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    plan_id = to_int(request.form.get('plan_id'))
    if not name or not username or len(password) < 6:
        flash('❌ اسم المطبعة واسم المستخدم وكلمة مرور (6+) مطلوبة.', 'error')
        return redirect(url_for('sa_dashboard'))
    if User.query.filter_by(username=username).first() or SuperAdmin.query.filter_by(username=username).first():
        flash('❌ اسم المستخدم محجوز مسبقاً.', 'error')
        return redirect(url_for('sa_dashboard'))
    plan = db.session.get(Plan, plan_id) if plan_id else None

    max_branches = max(1, min(50, to_int(request.form.get('max_branches'), 1)))
    if plan and (plan.max_branches or 1) > max_branches:
        max_branches = plan.max_branches
    btype = request.form.get('business_type') if request.form.get('business_type') in PRESETS else DEFAULT_PRESET
    shop = PrintShop(name=name,
                     owner_name=request.form.get('owner_name', '').strip(),
                     phone=request.form.get('phone', '').strip(),
                     address=request.form.get('address', '').strip(),
                     max_branches=max_branches, business_type=btype)
    db.session.add(shop)
    db.session.flush()
    apply_preset(shop.id, btype)

    admin_user = User(shop_id=shop.id, full_name=request.form.get('owner_name') or name,
                      username=username, password_hash=generate_password_hash(password),
                      role='owner' if max_branches > 1 else 'shop_admin', barcode_token=None)
    db.session.add(admin_user)

    sub = Subscription(shop_id=shop.id)
    if plan:
        sub.plan_id = plan.id
        sub.is_lifetime = plan.is_lifetime
        sub.ends_at = None if plan.is_lifetime else now() + timedelta(days=plan.duration_days)
        sub.amount_paid = plan.price
        sub.notes = f'تفعيل أولي على خطة: {plan.name}'
    else:
        sub.is_lifetime = True
        sub.notes = 'تفعيل دائم يدوي'
    db.session.add(sub)
    db.session.commit()
    flash(f'✅ تم إنشاء {name} بنجاح' + (f' (حساب سلسلة — حتى {max_branches} فروع).' if max_branches > 1 else ' مع حساب الأدمن.'), 'success')
    return redirect(url_for('sa_dashboard'))

@app.route('/sa/shops/<int:sid>/edit', methods=['POST'])
@super_admin_required
def sa_edit_shop(sid):
    shop = db.session.get(PrintShop, sid) or abort(404)
    shop.name = request.form.get('name', '').strip()
    shop.owner_name = request.form.get('owner_name', '').strip()
    shop.phone = request.form.get('phone', '').strip()
    shop.address = request.form.get('address', '').strip()
    new_pwd = request.form.get('admin_password', '').strip()
    admin_u = User.query.filter(User.shop_id == sid, User.role.in_(('shop_admin', 'owner'))).order_by(User.id).first()
    if new_pwd and len(new_pwd) >= 6 and admin_u:
        admin_u.password_hash = generate_password_hash(new_pwd)
    if not shop.parent_id and request.form.get('max_branches'):
        used = PrintShop.query.filter_by(parent_id=sid).count() + 1
        mb = max(1, min(50, to_int(request.form.get('max_branches'), 1)))
        if mb < used:
            flash(f'⚠️ عدد الفروع الحالي {used} — لا يمكن تقليل الحد عن ذلك.', 'error')
            mb = used
        shop.max_branches = mb
        if admin_u:
            admin_u.role = 'owner' if mb > 1 else 'shop_admin'
    db.session.commit()
    flash(f'✅ تم تحديث بيانات {shop.name} بنجاح.', 'success')
    return redirect(url_for('sa_dashboard'))

@app.route('/sa/shops/<int:sid>/renew', methods=['POST'])
@super_admin_required
def sa_renew_shop(sid):
    shop = db.session.get(PrintShop, sid) or abort(404)
    plan = db.session.get(Plan, to_int(request.form.get('plan_id')))
    paid = to_float(request.form.get('amount_paid'))
    base = now()
    prev = Subscription.query.filter_by(shop_id=sid).order_by(Subscription.id.desc()).first()
    if prev and not prev.is_lifetime and prev.ends_at and prev.ends_at > base:
        base = prev.ends_at
    sub = Subscription(shop_id=sid, plan_id=plan.id if plan else None,
                       starts_at=now(),
                       is_lifetime=bool(plan and plan.is_lifetime),
                       amount_paid=paid,
                       notes=request.form.get('notes', '').strip())
    if plan and not plan.is_lifetime:
        sub.ends_at = base + timedelta(days=plan.duration_days)
    db.session.add(sub)
    db.session.commit()
    flash(f'✅ تم تجديد اشتراك {shop.name}.', 'success')
    return redirect(url_for('sa_dashboard'))

@app.route('/sa/shops/<int:sid>/lifetime', methods=['POST'])
@super_admin_required
def sa_lifetime_shop(sid):
    shop = db.session.get(PrintShop, sid) or abort(404)
    sub = Subscription(shop_id=sid, is_lifetime=True,
                       amount_paid=to_float(request.form.get('amount_paid')),
                       notes='ترقية لنسخة مدى الحياة',
                       starts_at=now())
    db.session.add(sub)
    db.session.commit()
    flash(f'👑 تم ترقية {shop.name} إلى ترخيص مدى الحياة.', 'success')
    return redirect(url_for('sa_dashboard'))

@app.route('/sa/shops/<int:sid>/toggle', methods=['POST'])
@super_admin_required
def sa_toggle_shop(sid):
    shop = db.session.get(PrintShop, sid) or abort(404)
    shop.is_suspended = not shop.is_suspended
    db.session.commit()
    flash(('⛔ تم تعليق ' if shop.is_suspended else '✅ تم تفعيل ') + shop.name, 'success')
    return redirect(url_for('sa_dashboard'))

@app.route('/sa/plans/add', methods=['POST'])
@super_admin_required
def sa_add_plan():
    name = request.form.get('name', '').strip()
    if not name:
        flash('❌ اسم الخطة مطلوب.', 'error')
        return redirect(url_for('sa_dashboard'))
    is_lifetime = request.form.get('is_lifetime') == '1'
    p = Plan(
        name=name,
        price=to_float(request.form.get('price')),
        duration_days=0 if is_lifetime else to_int(request.form.get('duration_days'), 30),
        max_cashiers=to_int(request.form.get('max_cashiers'), 3),
        max_branches=max(1, min(50, to_int(request.form.get('max_branches'), 1))),
        is_lifetime=is_lifetime
    )
    db.session.add(p)
    db.session.commit()
    flash(f'✅ تمت إضافة خطة {name}.', 'success')
    return redirect(url_for('sa_dashboard'))

# ------------------------------ لوحة الأدمن للمطبعة ------------------------------
@app.route('/admin/dashboard')
@app.route('/admin')
@login_required(role='shop_admin')
def shop_admin_dashboard():
    sid = shop_id()
    page = request.args.get('page', 1, type=int)
    q = (request.args.get('q') or '').strip()
    status_f = (request.args.get('status') or '').strip()
    debt_only = request.args.get('debt') == '1'
    inv_query = Invoice.query.filter_by(shop_id=sid)
    if q:
        like = f'%{q}%'
        inv_query = inv_query.filter(or_(Invoice.token.ilike(like), Invoice.customer_name.ilike(like),
                                         Invoice.customer_phone.ilike(like)))
    if status_f in DELIVERY_STATUSES:
        inv_query = inv_query.filter(Invoice.delivery_status == status_f)
    if debt_only:
        inv_query = inv_query.filter(Invoice.remaining > 0)
    invoices_pagination = inv_query.order_by(Invoice.id.desc()).paginate(page=page, per_page=30, error_out=False)

    services = Service.query.filter_by(shop_id=sid).order_by(Service.name).all()
    cashiers = User.query.filter(User.shop_id == sid).order_by(User.id).all()
    expenses = Expense.query.filter_by(shop_id=sid).order_by(Expense.id.desc()).limit(100).all()
    logs = AuditLog.query.filter_by(shop_id=sid).order_by(AuditLog.id.desc()).limit(80).all()
    bindings = Binding.query.filter_by(shop_id=sid).all()
    premium_customers = PremiumCustomer.query.filter_by(shop_id=sid).all()
    b2b_partners = B2BPartner.query.filter_by(shop_id=sid).all()
    shop = db.session.get(PrintShop, sid)

    total_sales = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter_by(shop_id=sid).scalar() or 0.0
    total_deposit = db.session.query(func.coalesce(func.sum(Invoice.deposit), 0)).filter_by(shop_id=sid).scalar() or 0.0
    total_remaining = db.session.query(func.coalesce(func.sum(Invoice.remaining), 0)).filter_by(shop_id=sid).scalar() or 0.0
    total_expenses = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter_by(shop_id=sid).scalar() or 0.0
    net_profit = total_deposit - total_expenses
    invoice_count = Invoice.query.filter_by(shop_id=sid).count()
    avg_invoice_value = total_sales / invoice_count if invoice_count > 0 else 0

    today = today_str()
    today_sales = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter(
        Invoice.shop_id == sid, Invoice.date_str.like(f'{today}%')).scalar() or 0.0
    today_invoices_count = Invoice.query.filter(
        Invoice.shop_id == sid, Invoice.date_str.like(f'{today}%')).count()

    total_cashier_remaining = sum((c.base_salary or 0) + (c.bonus or 0) - (c.advances or 0) - (c.deductions or 0) for c in cashiers)

    top_services_data = db.session.query(
        InvoiceItem.name, func.sum(InvoiceItem.total).label('total_sold')
    ).filter(InvoiceItem.shop_id == sid).group_by(InvoiceItem.name).order_by(
        func.sum(InvoiceItem.total).desc()).limit(5).all()
    top_services = [(n, t) for n, t in top_services_data]

    low_stock_items = [s for s in services if s.stock is not None and s.stock >= 0 and s.stock <= (s.threshold or 0)]
    S = get_invoice_settings(sid)
    cfg = get_config(sid)
    finishing = FinishingService.query.filter_by(shop_id=sid).order_by(FinishingService.name).all()
    customers = Customer.query.filter_by(shop_id=sid).order_by(Customer.total_spent.desc()).limit(300).all()
    tiers_map = {c.id: (customer_tier(cfg, c) or {}).get('name', '') for c in customers}
    quick_total = db.session.query(func.coalesce(func.sum(QuickSale.total), 0)).filter_by(shop_id=sid).scalar() or 0.0
    quick_today = db.session.query(func.coalesce(func.sum(QuickSale.total), 0)).filter(
        QuickSale.shop_id == sid, QuickSale.date_str.like(f'{today}%')).scalar() or 0.0
    old_collected = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.shop_id == sid, Payment.kind == 'old_balance').scalar() or 0.0
    old_balances = db.session.query(func.coalesce(func.sum(Customer.old_balance), 0)).filter_by(shop_id=sid).scalar() or 0.0
    net_profit = total_deposit + quick_total + old_collected - total_expenses
    total_remaining = total_remaining + old_balances
    group = group_shops(sid) if session.get('role') == 'owner' else []

    return render_template(
        'admin.html', cfg=cfg, finishing=finishing, customers=customers, tiers_map=tiers_map,
        quick_total=quick_total, quick_today=quick_today, old_collected=old_collected,
        presets=preset_choices(current_lang()), preset_current=cfg['business_type'], group=group,
        invoices=invoices_pagination.items, pagination=invoices_pagination,
        q=q, status_f=status_f, debt_only=debt_only, statuses=DELIVERY_STATUSES,
        services=services, cashiers=cashiers, expenses=expenses, logs=logs,
        bindings=bindings, premium_customers=premium_customers, b2b_partners=b2b_partners,
        total_sales=total_sales, total_deposit=total_deposit, total_remaining=total_remaining,
        total_expenses=total_expenses, net_profit=net_profit,
        invoice_count=invoice_count, avg_invoice_value=avg_invoice_value,
        today_sales=today_sales, today_invoices_count=today_invoices_count,
        total_cashier_remaining=total_cashier_remaining, top_services=top_services,
        low_stock_count=len(low_stock_items), low_stock_items=low_stock_items,
        shop=shop, shop_name=session.get('shop_name', ''),
        services_json=[{'id': s.id, 'name': s.name, 'price_reg': s.price_reg, 'is_measurement_based': s.is_measurement_based,
                        'price_per_sqm': s.price_per_sqm} for s in services],
        inv_settings=S, papers={k: v['label'] for k, v in PAPERS.items()},
        fonts={k: v[0] for k, v in FONTS.items()},
        last_invoice_token=(Invoice.query.filter_by(shop_id=sid).order_by(Invoice.id.desc()).first() or SimpleNamespace(token='')).token
    )

@app.route('/api/admin/stats')
@login_required(role='shop_admin')
def api_admin_stats():
    sid = shop_id()
    today = now().date()
    start = today - timedelta(days=7)
    daily_data = []
    current = start
    while current <= today:
        ds = current.strftime('%Y-%m-%d')
        day_sales = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter(
            Invoice.shop_id == sid, Invoice.date_str.like(f'{ds}%')).scalar() or 0.0
        day_exp = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
            Expense.shop_id == sid, Expense.date_str.like(f'{ds}%')).scalar() or 0.0
        daily_data.append({'date': ds, 'sales': day_sales, 'expenses': day_exp})
        current += timedelta(days=1)

    return jsonify({'labels': [d['date'] for d in daily_data],
                    'sales': [d['sales'] for d in daily_data],
                    'expenses': [d['expenses'] for d in daily_data]})

# ------------------------------ تقرير الإغلاق المالي ------------------------------
@app.route('/admin/weekly_report')
@login_required(role='shop_admin')
def weekly_report():
    sid = shop_id()
    end_date = now().date()
    start_date = end_date - timedelta(days=7)
    s1, e1 = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    flt = lambda m: m.filter(Invoice.shop_id == sid, Invoice.date_str >= s1, Invoice.date_str <= e1 + 'z')
    total_sales = flt(db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0))).scalar() or 0.0
    total_collected = flt(db.session.query(func.coalesce(func.sum(Invoice.deposit), 0))).scalar() or 0.0
    total_remaining = flt(db.session.query(func.coalesce(func.sum(Invoice.remaining), 0))).scalar() or 0.0
    total_design = flt(db.session.query(func.coalesce(func.sum(Invoice.design_price), 0))).scalar() or 0.0
    total_discounts = flt(db.session.query(func.coalesce(func.sum(Invoice.discount), 0))).scalar() or 0.0
    expenses = Expense.query.filter(Expense.shop_id == sid, Expense.date_str >= s1, Expense.date_str <= e1 + 'z').all()
    total_expenses = sum(e.amount for e in expenses)
    cashiers = User.query.filter(User.shop_id == sid, User.role.in_(('cashier', 'supervisor'))).all()
    cashiers_list, total_remaining_salaries = [], 0.0
    for c in cashiers:
        net = (c.base_salary or 0) + (c.bonus or 0) - (c.advances or 0) - (c.deductions or 0)
        total_remaining_salaries += net
        cashiers_list.append({'full_name': c.full_name, 'base_salary': c.base_salary,
                              'advances': c.advances, 'deductions': c.deductions, 'net': net})

    return render_template('report.html', report_date=now_str(),
                           total_sales=total_sales, total_collected=total_collected,
                           total_remaining=total_remaining, total_design=total_design,
                           total_discounts=total_discounts,
                           total_expenses=total_expenses, cashiers_list=cashiers_list,
                           total_remaining_salaries=total_remaining_salaries,
                           start_date=s1, end_date=e1)

# ------------------------------ شاشة الكاشير (M-POS) ------------------------------
@app.route('/cashier')
@app.route('/cashier/dashboard')
@login_required(role='cashier')
def cashier_dashboard():
    sid = shop_id()
    services = Service.query.filter_by(shop_id=sid).all()
    favorite_services = Service.query.filter_by(shop_id=sid, is_favorite=True).limit(12).all()
    bindings = Binding.query.filter_by(shop_id=sid).all()
    premium_customers = PremiumCustomer.query.filter_by(shop_id=sid).all()
    today_str_ = today_str()
    today_invoices = Invoice.query.filter(
        Invoice.shop_id == sid,
        Invoice.cashier_username == session.get('username'),
        Invoice.date_str.like(f'{today_str_}%')).order_by(Invoice.id.desc()).limit(50).all()

    fav_json = [{'id': s.id, 'name': s.name, 'price_reg': s.price_reg, 'price_bulk': s.price_bulk,
                 'is_banner': s.is_banner, 'bulk_threshold': s.bulk_threshold,
                 'is_measurement_based': s.is_measurement_based,
                 'price_per_sqm': s.price_per_sqm} for s in favorite_services]

    low_stock_count = Service.query.filter(Service.shop_id == sid, Service.stock >= 0, Service.stock <= Service.threshold).count()
    finishing = [{'id': f.id, 'name': f.name, 'price': f.price} for f in
                 FinishingService.query.filter_by(shop_id=sid, is_active=True).order_by(FinishingService.name).all()]
    customer_names = [c.name for c in Customer.query.filter_by(shop_id=sid).order_by(Customer.invoices_count.desc()).limit(400).all()]
    cfg = get_config(sid)
    editable = [i.token for i in today_invoices if _can_cashier_edit(i)]
    quick_today = db.session.query(func.coalesce(func.sum(QuickSale.total), 0)).filter(
        QuickSale.shop_id == sid, QuickSale.created_by == session.get('username'), QuickSale.date_str.like(f'{today_str_}%')).scalar() or 0.0

    return render_template('cashier.html', services=services, finishing=finishing, customer_names=customer_names,
        cfg=cfg, editable_tokens=editable, quick_today=quick_today,
        favorite_services=favorite_services, favorite_services_json=json.dumps(fav_json),
        bindings=bindings, premium_customers=premium_customers,
        today_invoices=today_invoices, low_stock_count=low_stock_count,
        cashier_full_name=session.get('full_name', session.get('username', 'كاشير')))

@app.route('/api/services/all')
@login_required(role='cashier')
def api_services_all():
    sid = shop_id()
    results = [{'id': s.id, 'name': s.name, 'price_reg': s.price_reg,
                'price_bulk': s.price_bulk, 'bulk_threshold': s.bulk_threshold,
                'is_banner': s.is_banner, 'is_measurement_based': s.is_measurement_based,
                'price_per_sqm': s.price_per_sqm}
               for s in Service.query.filter_by(shop_id=sid).all()]
    return jsonify(results)

@app.route('/cashier/invoice/get_customer_discount/<string:name>')
@login_required(role='cashier')
def api_get_customer_discount(name):
    sid = shop_id()
    name = norm_name(name)
    pc = PremiumCustomer.query.filter_by(shop_id=sid, name=name).first()
    c = Customer.query.filter_by(shop_id=sid, name=name).first()
    tier = customer_tier(get_config(sid), c)
    discount = max(pc.discount_percentage if pc else 0.0, tier['discount'] if tier else 0.0)
    inv_debt, old_balance = customer_debt(sid, name)
    return jsonify({
        'discount': discount, 'tier': (tier['name'] if tier else (pc.tier_name if pc else '')),
        'exists': bool(c or pc), 'is_new': not (c or pc) and bool(name),
        'invoices_count': c.invoices_count if c else 0, 'total_spent': c.total_spent if c else 0.0,
        'phone': (c.phone if c and c.phone else (pc.phone if pc else '')),
        'invoice_debt': inv_debt, 'old_balance': old_balance, 'debt': inv_debt + old_balance})


@app.route('/api/customers/search')
@login_required(role='cashier')
def api_customers_search():
    q = (request.args.get('q') or '').strip()
    qs = Customer.query.filter_by(shop_id=shop_id())
    if q:
        qs = qs.filter(or_(Customer.name.ilike(f'%{q}%'), Customer.phone.ilike(f'%{q}%')))
    return jsonify([{'name': c.name, 'phone': c.phone or ''} for c in qs.order_by(Customer.name).limit(30).all()])


def _clip(val, n):
    return (str(val) if val is not None else '').strip()[:n]


def _apply_invoice(sid, data, token=None, actor='', actor_name='', audit_action='تعديل فاتورة', edit_reason=''):
    """منطق حفظ/تعديل الفاتورة المشترك بين الكاشير والأدمن. يُرجع (الفاتورة، قائمة تحذيرات)."""
    warnings = []
    old_total = None
    old_name = ''
    if token:
        inv = Invoice.query.filter_by(token=token, shop_id=sid).first()
        if not inv:
            raise LookupError('كود الفاتورة غير موجود!')
        old_total = inv.grand_total or 0.0
        old_name = norm_name(inv.customer_name)
        # استرجاع المخزون القديم قبل حذف البنود
        for old in InvoiceItem.query.filter_by(invoice_token=token, shop_id=sid).all():
            s_old = db.session.get(Service, old.service_id)
            if s_old and s_old.shop_id == sid and s_old.stock >= 0:
                s_old.stock += old.qty
        InvoiceItem.query.filter_by(invoice_token=token, shop_id=sid).delete()
    else:
        token = secrets.token_hex(4).upper()
        while Invoice.query.filter_by(token=token).first():
            token = secrets.token_hex(4).upper()
        inv = Invoice(token=token, shop_id=sid, date_str=now_str(), cashier_username=actor, cashier_full_name=actor_name)
        db.session.add(inv)

    inv.customer_name = _clip(data.get('customer_name'), 100) or 'عميل نقدي'
    inv.customer_phone = _clip(data.get('customer_phone'), 50)
    inv.payment_method = _clip(data.get('payment_method'), 50) or 'نقدي'
    status = data.get('delivery_status')
    if status in DELIVERY_STATUSES:
        inv.delivery_status = status
    elif not inv.delivery_status:
        inv.delivery_status = DELIVERY_STATUSES[0]
    inv.notes = (data.get('notes') or '').strip()[:1000]
    inv.design_price = max(0.0, to_float(data.get('design_price')))
    inv.discount = max(0.0, to_float(data.get('discount')))
    inv.deposit = max(0.0, to_float(data.get('deposit')))

    for key in ('cutting', 'solofan', 'beshr'):
        if key not in data and (key + '_price') not in data and (key + '_qty') not in data:
            continue          # الواجهة الجديدة لا ترسلها — نحافظ على قيم الفواتير القديمة
        part = data.get(key) if isinstance(data.get(key), dict) else {}
        price = max(0.0, to_float(part.get('price') if part.get('price') not in (None, '') else data.get(key + '_price')))
        qty = max(0, to_int(part.get('qty') if part.get('qty') not in (None, '') else data.get(key + '_qty')))
        setattr(inv, key + '_price', price)
        setattr(inv, key + '_qty', qty)
        setattr(inv, key + '_total', price * qty)

    subtotal = 0.0
    for item in (data.get('cart') or []):
        qty = to_float(item.get('qty'), 1)
        h, w = to_float(item.get('height')), to_float(item.get('width'))
        total = to_float(item.get('total'))
        if total == 0:
            total = qty * h * w if (h > 0 and w > 0) else qty * to_float(item.get('unit_price'))
        subtotal += total
        sid_item = to_int(item.get('id'))
        db.session.add(InvoiceItem(shop_id=sid, invoice_token=token, service_id=sid_item,
                                   name=_clip(item.get('name'), 150) or 'بند', qty=qty, height=h, width=w,
                                   unit_price=to_float(item.get('unit_price')), total=total))
        srv = db.session.get(Service, sid_item) if sid_item else None
        if srv and srv.shop_id == sid and srv.stock >= 0:
            if qty > srv.stock:
                warnings.append(f'رصيد «{srv.name}» ({srv.stock:g}) أقل من الكمية المباعة ({qty:g}) — راجع المخزن.')
            srv.stock = max(0.0, srv.stock - qty)

    extras = []
    for e in (data.get('extras') or [])[:30]:
        nm = _clip(e.get('name'), 100)
        q, pr = max(0.0, to_float(e.get('qty'), 1)), max(0.0, to_float(e.get('price')))
        if nm and q > 0:
            extras.append({'name': nm, 'qty': q, 'price': pr, 'total': round(q * pr, 2)})
    inv.extras_json = json.dumps(extras, ensure_ascii=False)
    inv.extras_total = round(sum(e['total'] for e in extras), 2)

    inv.subtotal = subtotal
    inv.grand_total = max(0.0, (subtotal + inv.design_price + (inv.cutting_total or 0) + (inv.solofan_total or 0) +
                                (inv.beshr_total or 0) + inv.extras_total) - inv.discount)
    inv.remaining = max(0.0, inv.grand_total - inv.deposit)

    # تسجيل العميل تلقائياً وحساب فئته (عدد الفواتير + إجمالي المشتريات)
    db.session.flush()
    cust = recalc_customer(sid, inv.customer_name, inv.customer_phone)
    if old_name and old_name != norm_name(inv.customer_name):
        recalc_customer(sid, old_name)
    tier = customer_tier(get_config(sid), cust)
    pc = PremiumCustomer.query.filter_by(shop_id=sid, name=norm_name(inv.customer_name)).first()
    inv.customer_tier = (tier['name'] if tier else (pc.tier_name if pc and pc.tier_name else ''))[:60]

    if old_total is not None:
        db.session.add(AuditLog(shop_id=sid, action=audit_action, invoice_token=token, action_by=actor_name or actor,
                                reason=_clip(f"{edit_reason or 'تعديل فاتورة'} | الإجمالي {old_total:,.2f} ← {inv.grand_total:,.2f}", 255)))
    return inv, warnings


def _can_cashier_edit(inv):
    """صلاحية تعديل الكاشير للفاتورة حسب إعداد الأدمن (off / own_today / all)."""
    if session.get('role') in ADMIN_ROLES:
        return True
    mode = get_config(inv.shop_id)['cashier_edit']
    if mode == 'all':
        return True
    if mode == 'own_today':
        return inv.cashier_username == session.get('username') and (inv.date_str or '').startswith(today_str())
    return False


def _invoice_json(sid, token):
    inv = Invoice.query.filter_by(token=token, shop_id=sid).first()
    if not inv:
        return None, None
    items = InvoiceItem.query.filter_by(invoice_token=token, shop_id=sid).order_by(InvoiceItem.id).all()
    try:
        extras = json.loads(inv.extras_json or '[]')
    except ValueError:
        extras = []
    return inv, {
        'success': True,
        'invoice': {
            'token': inv.token, 'customer_name': inv.customer_name, 'customer_phone': inv.customer_phone,
            'payment_method': inv.payment_method, 'delivery_status': inv.delivery_status, 'notes': inv.notes or '',
            'design_price': inv.design_price, 'discount': inv.discount, 'deposit': inv.deposit,
            'cutting': {'qty': inv.cutting_qty, 'price': inv.cutting_price},
            'solofan': {'qty': inv.solofan_qty, 'price': inv.solofan_price},
            'beshr': {'qty': inv.beshr_qty, 'price': inv.beshr_price},
            'extras': extras, 'date_str': inv.date_str, 'cashier': inv.cashier_full_name or inv.cashier_username,
        },
        'items': [{'id': i.service_id, 'name': i.name, 'qty': i.qty, 'height': i.height, 'width': i.width,
                   'unit_price': i.unit_price, 'total': i.total} for i in items],
    }


def _refresh_shift_cash(sid):
    shift = db.session.get(ShiftLog, session['shift_log_id']) if 'shift_log_id' in session else None
    if not shift:
        return
    user, today = session.get('username'), today_str()
    inv_cash = db.session.query(func.coalesce(func.sum(Invoice.deposit), 0)).filter(
        Invoice.shop_id == sid, Invoice.cashier_username == user, Invoice.date_str.like(f'{today}%')).scalar() or 0.0
    quick = db.session.query(func.coalesce(func.sum(QuickSale.total), 0)).filter(
        QuickSale.shop_id == sid, QuickSale.created_by == user, QuickSale.date_str.like(f'{today}%')).scalar() or 0.0
    old = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.shop_id == sid, Payment.created_by == user, Payment.kind == 'old_balance',
        Payment.date_str.like(f'{today}%')).scalar() or 0.0
    shift.collected_cash = float(inv_cash) + float(quick) + float(old)


@app.route('/cashier/invoice/<string:token>/data')
@login_required(role='cashier')
def cashier_invoice_data(token):
    sid = shop_id()
    inv, payload = _invoice_json(sid, token)
    if not inv:
        return jsonify({'success': False, 'message': 'الفاتورة غير موجودة!'}), 404
    if not _can_cashier_edit(inv):
        return jsonify({'success': False, 'message': 'مفيش صلاحية تعديل لهذه الفاتورة — اطلب من الأدمن.'}), 403
    return jsonify(payload)


@app.route('/cashier/invoice/save', methods=['POST'])
@login_required(role='cashier')
def cashier_save_invoice():
    sid = shop_id()
    data = request.json or {}
    if not data or not data.get('cart'):
        return jsonify({'success': False, 'message': 'بيانات الفاتورة فارغة!'})
    token = (data.get('token') or '').strip() or None
    reason = _clip(data.get('edit_reason'), 150)
    if token:
        existing = Invoice.query.filter_by(token=token, shop_id=sid).first()
        if not existing:
            return jsonify({'success': False, 'message': 'كود الفاتورة غير موجود!'})
        if not _can_cashier_edit(existing):
            return jsonify({'success': False, 'message': 'مفيش صلاحية تعديل لهذه الفاتورة.'}), 403
        if not reason:
            return jsonify({'success': False, 'message': 'اكتب سبب التعديل ليتم قيده في سجل الرقابة.'})
    try:
        inv, warnings = _apply_invoice(sid, data, token=token, actor=session.get('username', ''),
                                       actor_name=session.get('full_name', ''),
                                       audit_action='تعديل فاتورة (كاشير)', edit_reason=reason)
    except LookupError as ex:
        return jsonify({'success': False, 'message': str(ex)})
    _refresh_shift_cash(sid)
    db.session.commit()
    return jsonify({'success': True, 'token': inv.token, 'warnings': warnings})


@app.route('/admin/invoice/<string:token>/data')
@login_required(role='shop_admin')
def admin_invoice_data(token):
    inv, payload = _invoice_json(shop_id(), token)
    if not inv:
        return jsonify({'success': False, 'message': 'الفاتورة غير موجودة!'}), 404
    return jsonify(payload)


@app.route('/admin/invoice/<string:token>/update', methods=['POST'])
@login_required(role='shop_admin')
def admin_invoice_update(token):
    sid = shop_id()
    data = request.json or {}
    reason = _clip(data.get('reason'), 150)
    if not reason:
        return jsonify({'success': False, 'message': 'اكتب سبب التعديل ليتم قيده في سجل الرقابة.'})
    if not data.get('cart'):
        return jsonify({'success': False, 'message': 'الفاتورة لازم يكون فيها بند واحد على الأقل.'})
    try:
        inv, warnings = _apply_invoice(sid, data, token=token, actor=session.get('username', ''),
                                       actor_name=session.get('full_name', ''),
                                       audit_action='تعديل فاتورة (أدمن)', edit_reason=reason)
    except LookupError as ex:
        return jsonify({'success': False, 'message': str(ex)})
    db.session.commit()
    return jsonify({'success': True, 'token': inv.token, 'warnings': warnings, 'grand_total': inv.grand_total})


@app.route('/cashier/invoice/delete', methods=['POST'])
@login_required(role='cashier')
def cashier_delete_invoice():
    sid = shop_id()
    data = request.json or {}
    token = data.get('token')
    reason = data.get('reason', '').strip()
    if not token or not reason:
        return jsonify({'success': False, 'message': 'يجب توضيح سبب حذف الفاتورة!'})
    if session.get('role') not in ADMIN_ROLES and not get_config(sid)['cashier_delete']:
        return jsonify({'success': False, 'message': 'حذف الفواتير متاح للأدمن فقط.'}), 403

    inv = Invoice.query.filter_by(token=token, shop_id=sid).first()
    if not inv:
        return jsonify({'success': False, 'message': 'الفاتورة غير موجودة!'})

    items = InvoiceItem.query.filter_by(invoice_token=token, shop_id=sid).all()
    for item in items:
        srv = db.session.get(Service, item.service_id)
        if srv and srv.stock >= 0:
            srv.stock += item.qty

    InvoiceItem.query.filter_by(invoice_token=token, shop_id=sid).delete()
    cname = inv.customer_name
    db.session.delete(inv)
    db.session.flush()
    recalc_customer(sid, cname)
    db.session.add(AuditLog(
        shop_id=sid,
        action='حذف فاتورة (كاشير)',
        invoice_token=token,
        action_by=session.get('full_name') or session.get('username'),
        reason=reason
    ))
    db.session.commit()
    return jsonify({'success': True, 'message': f'تم حذف الفاتورة #{token} وقيد سبب الحذف في الرقابة.'})

@app.route('/api/invoice/status/<string:token>', methods=['POST'])
@login_required(role='cashier')
def update_invoice_status(token):
    sid = shop_id()
    data = request.json or {}
    new_status = data.get('status')
    if new_status not in DELIVERY_STATUSES:
        return jsonify({'success': False, 'message': 'حالة الطلب غير معروفة!'})
    inv = Invoice.query.filter_by(token=token, shop_id=sid).first()
    if not inv:
        return jsonify({'success': False, 'message': 'الفاتورة غير موجودة!'})

    inv.delivery_status = new_status
    db.session.commit()

    shop = db.session.get(PrintShop, sid)
    press_title = shop.name if shop else session.get('shop_name', 'المطبعة')
    cashier_title = session.get('full_name') or session.get('username') or 'فريق العمل'
    cust_name = inv.customer_name

    msg = ""
    if new_status == 'دخلت الطباعة':
        msg = f"مرحباً أستاذ {cust_name} 🖨️\nنحيطك علماً بأن طلبك رقم #{inv.token} قد دخل مرحلة الطباعة والإنتاج حالياً لدى {press_title}.\nالمسؤول: {cashier_title}"
    elif new_status == 'في التجهيز':
        msg = f"مرحباً أستاذ {cust_name} ✂️\nطلبك رقم #{inv.token} حالياً في مرحلة التجهيز والتشطيب والتغليف.\n{press_title}"
    elif new_status == 'جاهز للاستلام':
        rem_msg = f"المتبقي طرفكم: {inv.remaining:,.2f} ج.م" if inv.remaining > 0 else "الحساب خالص تماماً ✅"
        msg = f"مرحباً أستاذ {cust_name} 🌟\nطلبك رقم #{inv.token} أصبح جاهزاً للاستلام الآن بمقرنا!\n{rem_msg}\nنسعد بزيارتك — {press_title}"
    elif new_status == 'شكراً لتعاملكم':
        msg = f"شكراً لثقتكم الغالية بنا أستاذ {cust_name} 🌺\nسعدنا بخدمتكم في فاتورة #{inv.token} ونتطلع لتعاملات قادمة مثمرة دائماً بإذن الله.\n{press_title} — الكاشير: {cashier_title}"

    wa_link = None
    clean_phone = sanitize_egyptian_phone(inv.customer_phone)
    if clean_phone:
        # استخدام رابط WhatsApp Web / API المستقر الذي يتفادى خطأ 404
        wa_link = f"https://api.whatsapp.com/send?phone={clean_phone}&text={urllib.parse.quote(msg)}"

    return jsonify({'success': True, 'status': new_status, 'whatsapp_url': wa_link, 'message_text': msg})

# ------------------------------ السداد والمديونيات (بتاريخ ووقت) ------------------------------
def _open_invoices(sid, name):
    return Invoice.query.filter(Invoice.shop_id == sid, Invoice.customer_name == name,
                                Invoice.remaining > 0).order_by(Invoice.id.asc()).all()


def apply_payment(sid, name, amount, target='auto', note='', actor=''):
    """يوزّع مبلغ السداد: target = auto (المديونية القديمة ثم أقدم الفواتير) | old_balance | رقم فاتورة.
    يرجع (ملخص العمليات، المبلغ الزائد اللي مااتطبقش)."""
    rem = round(float(amount), 2)
    summary = []
    c = Customer.query.filter_by(shop_id=sid, name=name).first()
    when = now_str()

    if target in ('auto', 'old_balance') and c and (c.old_balance or 0) > 0 and rem > 0:
        pay = round(min(rem, c.old_balance), 2)
        c.old_balance = round(c.old_balance - pay, 2)
        rem = round(rem - pay, 2)
        db.session.add(Payment(shop_id=sid, customer_name=name, kind='old_balance', amount=pay,
                               date_str=when, created_by=actor, note=note))
        summary.append(f'مديونية قديمة ({pay:,.2f} ج)')

    if target not in ('old_balance',) and rem > 0:
        invs = _open_invoices(sid, name)
        if target not in ('auto', 'old_balance'):
            invs = [i for i in invs if i.token == target]
        for inv in invs:
            if rem <= 0:
                break
            pay = round(min(rem, inv.remaining), 2)
            inv.deposit = round((inv.deposit or 0) + pay, 2)
            inv.remaining = round(max(0.0, inv.remaining - pay), 2)
            rem = round(rem - pay, 2)
            db.session.add(Payment(shop_id=sid, customer_name=name, invoice_token=inv.token, kind='invoice',
                                   amount=pay, date_str=when, created_by=actor, note=note))
            summary.append(f'#{inv.token} ({"كامل" if inv.remaining <= 0 else "جزء"} {pay:,.2f} ج)')
    return summary, max(0.0, rem)


@app.route('/cashier/debts')
@login_required(role='cashier')
def cashier_debts_page():
    return render_template('debts.html', preselect=request.args.get('c', ''),
                           can_admin=session.get('role') in ADMIN_ROLES)


@app.route('/api/debt/customers')
@login_required(role='cashier')
def api_get_debt_customers():
    """ملخص المديونيات: كل عميل عليه فواتير غير مسددة أو مديونية قديمة."""
    sid = shop_id()
    rows = {}
    for name, phone, total, cnt in db.session.query(
            Invoice.customer_name, func.max(Invoice.customer_phone), func.sum(Invoice.remaining),
            func.count(Invoice.id)).filter(Invoice.shop_id == sid, Invoice.remaining > 0).group_by(Invoice.customer_name).all():
        rows[name] = {'name': name, 'phone': phone or '', 'invoice_debt': float(total or 0), 'old_balance': 0.0, 'count': cnt}
    for c in Customer.query.filter(Customer.shop_id == sid, Customer.old_balance > 0).all():
        r = rows.setdefault(c.name, {'name': c.name, 'phone': c.phone or '', 'invoice_debt': 0.0, 'old_balance': 0.0, 'count': 0})
        r['old_balance'] = float(c.old_balance)
        r['phone'] = r['phone'] or c.phone or ''
    out = []
    for r in rows.values():
        r['total_debt'] = round(r['invoice_debt'] + r['old_balance'], 2)
        out.append(r)
    out.sort(key=lambda x: -x['total_debt'])
    return jsonify(out)


@app.route('/api/debt/customer')
@login_required(role='cashier')
def api_debt_customer_detail():
    sid = shop_id()
    name = norm_name(request.args.get('name'))
    c = Customer.query.filter_by(shop_id=sid, name=name).first()
    invs = _open_invoices(sid, name)
    pays = Payment.query.filter_by(shop_id=sid, customer_name=name).order_by(Payment.id.desc()).limit(100).all()
    inv_debt, old_balance = customer_debt(sid, name)
    return jsonify({
        'name': name, 'phone': c.phone if c else '', 'old_balance': old_balance, 'invoice_debt': inv_debt,
        'total_debt': inv_debt + old_balance,
        'invoices': [{'token': i.token, 'date': i.date_str, 'grand_total': i.grand_total, 'deposit': i.deposit,
                      'remaining': i.remaining} for i in invs],
        'payments': [{'id': p.id, 'kind': p.kind, 'invoice': p.invoice_token, 'amount': p.amount, 'date': p.date_str,
                      'by': p.created_by, 'note': p.note} for p in pays]})


@app.route('/api/debt/pay', methods=['POST'])
@login_required(role='cashier')
def api_pay_debt():
    sid = shop_id()
    data = request.json or {}
    name = norm_name(data.get('customer_name'))
    amount = to_float(data.get('amount'))
    target = str(data.get('target') or 'auto')[:50]
    if not name or amount <= 0:
        return jsonify({'success': False, 'message': 'اختر العميل واكتب مبلغاً أكبر من صفر.'})
    inv_debt, old_balance = customer_debt(sid, name)
    if inv_debt + old_balance <= 0:
        return jsonify({'success': False, 'message': 'لا توجد مديونيات مفتوحة لهذا العميل.'})
    actor = session.get('full_name') or session.get('username')
    summary, leftover = apply_payment(sid, name, amount, target, _clip(data.get('note'), 200), session.get('username', ''))
    if not summary:
        return jsonify({'success': False, 'message': 'لا يوجد مبلغ مستحق في الجهة المختارة.'})
    db.session.add(AuditLog(shop_id=sid, action='سداد دين عميل', invoice_token=_clip(', '.join(summary), 50), action_by=actor,
                            reason=_clip(f'سداد {amount - leftover:,.2f} ج.م للعميل {name}: ' + ' ، '.join(summary), 255)))
    _refresh_shift_cash(sid)
    db.session.commit()
    msg = f'تبقّى {leftover:,.2f} ج.م زيادة عن المستحق (لم تُسجَّل).' if leftover > 0 else ''
    return jsonify({'success': True, 'paid_summary': summary, 'remaining_unapplied': leftover, 'message': msg,
                    'applied': round(amount - leftover, 2)})


@app.route('/api/old_balance/add', methods=['POST'])
@login_required(role='cashier')
def api_old_balance_add():
    """إضافة مديونية قديمة على عميل (أخد خدمة من غير فاتورة وفضل عليه فلوس)."""
    sid = shop_id()
    data = request.json or {}
    name = norm_name(data.get('customer_name'))
    amount = to_float(data.get('amount'))
    if not name or name == ANON_CUSTOMER or amount <= 0:
        return jsonify({'success': False, 'message': 'اكتب اسم العميل ومبلغاً أكبر من صفر.'})
    c = Customer.query.filter_by(shop_id=sid, name=name).first()
    if not c:
        c = Customer(shop_id=sid, name=name)
        db.session.add(c)
    if data.get('phone') and not c.phone:
        c.phone = _clip(data.get('phone'), 50)
    c.old_balance = round((c.old_balance or 0) + amount, 2)
    db.session.add(Payment(shop_id=sid, customer_name=name, kind='old_balance_add', amount=amount, date_str=now_str(),
                           created_by=session.get('username', ''), note=_clip(data.get('note'), 200) or 'مديونية قديمة'))
    db.session.add(AuditLog(shop_id=sid, action='إضافة مديونية قديمة', action_by=session.get('full_name') or session.get('username'),
                            reason=_clip(f'{amount:,.2f} ج.م على العميل {name}', 255)))
    db.session.commit()
    return jsonify({'success': True, 'old_balance': c.old_balance})


# ------------------------------ البيع السريع (بدون فاتورة) ------------------------------
def _quick_rows(sid, day=None):
    day = day or today_str()
    return QuickSale.query.filter(QuickSale.shop_id == sid, QuickSale.date_str.like(f'{day}%')).order_by(QuickSale.id.desc()).all()


@app.route('/cashier/quick')
@login_required(role='cashier')
def cashier_quick_page():
    sid = shop_id()
    svc = Service.query.filter_by(shop_id=sid).order_by(Service.is_favorite.desc(), Service.name).all()
    services = [{'id': s.id, 'name': s.name, 'price': s.price_reg, 'price_bulk': s.price_bulk,
                 'bulk_threshold': s.bulk_threshold, 'unit': s.unit_name, 'stock': s.stock,
                 'fav': s.is_favorite, 'sqm': s.is_measurement_based} for s in svc if not s.is_measurement_based]
    return render_template('quick.html', services=services, can_admin=session.get('role') in ADMIN_ROLES)


@app.route('/api/quick/list')
@login_required(role='cashier')
def api_quick_list():
    sid = shop_id()
    rows = _quick_rows(sid)
    by = {}
    for r in rows:
        b = by.setdefault(r.name, {'name': r.name, 'qty': 0.0, 'wasted': 0.0, 'total': 0.0})
        b['qty'] += r.qty; b['wasted'] += r.wasted; b['total'] += r.total
    return jsonify({'total': sum(r.total for r in rows), 'groups': list(by.values()),
                    'rows': [{'id': r.id, 'name': r.name, 'qty': r.qty, 'wasted': r.wasted, 'unit_price': r.unit_price,
                              'total': r.total, 'date': r.date_str, 'by': r.created_by, 'note': r.note} for r in rows[:200]]})


@app.route('/api/quick/add', methods=['POST'])
@login_required(role='cashier')
def api_quick_add():
    sid = shop_id()
    d = request.json or {}
    qty, wasted = max(0.0, to_float(d.get('qty'))), max(0.0, to_float(d.get('wasted')))
    if qty <= 0 and wasted <= 0:
        return jsonify({'success': False, 'message': 'اكتب العدد (أو الهالك).'})
    svc = db.session.get(Service, to_int(d.get('service_id'))) if d.get('service_id') else None
    if svc and svc.shop_id != sid:
        svc = None
    name = svc.name if svc else _clip(d.get('name'), 150)
    if not name:
        return jsonify({'success': False, 'message': 'اختر الخدمة أو اكتب اسمها.'})
    price = to_float(d.get('unit_price'), -1)
    if price < 0:
        price = (svc.price_bulk if svc and svc.bulk_threshold > 0 and svc.price_bulk > 0 and qty >= svc.bulk_threshold else (svc.price_reg if svc else 0.0))
    warnings = []
    if svc and svc.stock >= 0:
        need = qty + wasted
        if need > svc.stock:
            warnings.append(f'رصيد «{svc.name}» ({svc.stock:g}) أقل من المسحوب ({need:g}).')
        svc.stock = max(0.0, svc.stock - need)
    db.session.add(QuickSale(shop_id=sid, service_id=svc.id if svc else 0, name=name, qty=qty, wasted=wasted,
                             unit_price=price, total=round(qty * price, 2), date_str=now_str(),
                             created_by=session.get('username', ''), note=_clip(d.get('note'), 200)))
    _refresh_shift_cash(sid)
    db.session.commit()
    return jsonify({'success': True, 'warnings': warnings})


@app.route('/api/quick/<int:qid>/delete', methods=['POST'])
@login_required(role='cashier')
def api_quick_delete(qid):
    sid = shop_id()
    r = db.session.get(QuickSale, qid)
    if not r or r.shop_id != sid:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    if session.get('role') not in ADMIN_ROLES and not (r.created_by == session.get('username') and r.date_str.startswith(today_str())):
        return jsonify({'success': False, 'message': 'تقدر تحذف عمليات اليوم الخاصة بك فقط.'}), 403
    svc = db.session.get(Service, r.service_id) if r.service_id else None
    if svc and svc.shop_id == sid and svc.stock >= 0:
        svc.stock += (r.qty or 0) + (r.wasted or 0)
    db.session.add(AuditLog(shop_id=sid, action='حذف بيع سريع', action_by=session.get('full_name') or session.get('username'),
                            reason=_clip(f'{r.name} × {r.qty:g} = {r.total:,.2f} ج.م', 255)))
    db.session.delete(r)
    _refresh_shift_cash(sid)
    db.session.commit()
    return jsonify({'success': True})


# ------------------------------ خدمات التشطيب، فئات العملاء، القوالب ------------------------------
@app.route('/admin/finishing/add', methods=['POST'])
@login_required(role='shop_admin')
def admin_add_finishing():
    name = _clip(request.form.get('name'), 100)
    if name:
        db.session.add(FinishingService(shop_id=shop_id(), name=name, price=max(0.0, to_float(request.form.get('price')))))
        db.session.commit()
        flash('✅ تمت إضافة خدمة التشطيب — هتظهر للكاشير فوراً.', 'success')
    else:
        flash('❌ اكتب اسم خدمة التشطيب.', 'error')
    return redirect(url_for('shop_admin_dashboard') + '#bindings')


@app.route('/admin/finishing/<int:id>/edit', methods=['POST'])
@login_required(role='shop_admin')
def admin_edit_finishing(id):
    f = db.session.get(FinishingService, id)
    if not f or f.shop_id != shop_id():
        abort(404)
    name = _clip(request.form.get('name'), 100)
    if name:
        f.name, f.price = name, max(0.0, to_float(request.form.get('price')))
        f.is_active = request.form.get('is_active') in ('1', 'on', 'true')
        db.session.commit()
        flash('✅ تم تحديث خدمة التشطيب.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#bindings')


@app.route('/admin/finishing/<int:id>/delete', methods=['POST'])
@login_required(role='shop_admin')
def admin_delete_finishing(id):
    f = db.session.get(FinishingService, id)
    if f and f.shop_id == shop_id():
        db.session.delete(f)
        db.session.commit()
        flash('تم حذف خدمة التشطيب.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#bindings')


@app.route('/admin/config/save', methods=['POST'])
@login_required(role='shop_admin')
def admin_config_save():
    sid = shop_id()
    cfg = get_config(sid)
    f = request.form
    cfg['cashier_edit'] = f.get('cashier_edit', cfg['cashier_edit'])
    cfg['cashier_delete'] = f.get('cashier_delete') in ('1', 'on', 'true')
    tiers = []
    for n, mi, ms, dc in zip(f.getlist('tier_name'), f.getlist('tier_min_invoices'), f.getlist('tier_min_spent'), f.getlist('tier_discount')):
        if n.strip():
            tiers.append({'name': n, 'min_invoices': mi, 'min_spent': ms, 'discount': dc})
    cfg['tiers'] = tiers
    save_config(sid, cfg)
    db.session.commit()
    flash('✅ تم حفظ إعدادات العملاء والصلاحيات.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#settings')


@app.route('/admin/preset/apply', methods=['POST'])
@login_required(role='shop_admin')
def admin_apply_preset():
    key = request.form.get('preset', '')
    if key not in PRESETS:
        flash('❌ اختر نوع نشاط صحيح.', 'error')
    else:
        n_s, n_f = apply_preset(shop_id(), key)
        db.session.commit()
        flash(f'✅ تم تطبيق قالب «{PRESETS[key]["ar"]}»: أُضيفت {n_s} خدمة و{n_f} خدمة تشطيب (الموجود لم يتكرر). عدّل الأسعار من «الخدمات والمخزون».', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#services')


# ------------------------------ الفروع: لوحة المالك ------------------------------
def _branch_stats(sid):
    today = today_str()
    q = lambda col, *f: db.session.query(func.coalesce(func.sum(col), 0)).filter(*f).scalar() or 0.0
    sales = q(Invoice.grand_total, Invoice.shop_id == sid)
    return {
        'sales': float(sales), 'today': float(q(Invoice.grand_total, Invoice.shop_id == sid, Invoice.date_str.like(f'{today}%'))),
        'collected': float(q(Invoice.deposit, Invoice.shop_id == sid)),
        'quick': float(q(QuickSale.total, QuickSale.shop_id == sid)),
        'old_collected': float(q(Payment.amount, Payment.shop_id == sid, Payment.kind == 'old_balance')),
        'expenses': float(q(Expense.amount, Expense.shop_id == sid)),
        'debts': float(q(Invoice.remaining, Invoice.shop_id == sid)) + float(q(Customer.old_balance, Customer.shop_id == sid)),
        'invoices': Invoice.query.filter_by(shop_id=sid).count(),
        'staff': User.query.filter_by(shop_id=sid).count(),
    }


def owner_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if session.get('role') != 'owner':
            flash('🚫 هذه الصفحة لأصحاب حسابات الفروع فقط.', 'error')
            return redirect(url_for('login_page'))
        return f(*a, **kw)
    return wrapper


@app.route('/owner')
@login_required(role='owner')
@owner_required
def owner_dashboard():
    hq_id = root_shop_id(session.get('home_shop_id') or session.get('shop_id'))
    session['home_shop_id'] = hq_id
    session['shop_id'] = hq_id          # العودة لوضع «كل الفروع» لا تعني أي فرع بعينه
    hq = db.session.get(PrintShop, hq_id)
    branches = []
    for b in group_shops(hq_id):
        st = _branch_stats(b.id)
        st['net'] = st['collected'] + st['quick'] + st['old_collected'] - st['expenses']
        branches.append({'shop': b, 'stats': st, 'is_hq': b.id == hq_id})
    totals = {k: sum(b['stats'][k] for b in branches) for k in branches[0]['stats']} if branches else {}
    totals['net'] = sum(b['stats']['net'] for b in branches)
    return render_template('owner.html', hq=hq, branches=branches, totals=totals,
                           limit=hq.max_branches or 1, used=len(branches), presets=preset_choices(current_lang()),
                           press_name=hq.name)


@app.route('/owner/branch/add', methods=['POST'])
@login_required(role='owner')
@owner_required
def owner_add_branch():
    hq_id = root_shop_id(session.get('home_shop_id') or session.get('shop_id'))
    hq = db.session.get(PrintShop, hq_id)
    if len(group_shops(hq_id)) >= (hq.max_branches or 1):
        flash('⚠️ وصلت للحد الأقصى من الفروع في اشتراكك. تواصل مع الدعم لترقية الخطة.', 'error')
        return redirect(url_for('owner_dashboard'))
    f = request.form
    name = _clip(f.get('name'), 150)
    a_user, a_pass = _clip(f.get('admin_username'), 50), f.get('admin_password', '')
    c_user, c_pass = _clip(f.get('cashier_username'), 50), f.get('cashier_password', '')
    if not name or not a_user or len(a_pass) < 6:
        flash('❌ اسم الفرع ويوزر وباسورد أدمن الفرع (6 أحرف+) مطلوبين.', 'error')
        return redirect(url_for('owner_dashboard'))
    if c_user and len(c_pass) < 6:
        flash('❌ باسورد الكاشير لازم يكون 6 أحرف على الأقل.', 'error')
        return redirect(url_for('owner_dashboard'))
    names = [a_user] + ([c_user] if c_user else [])
    if len(set(names)) != len(names) or any(User.query.filter_by(username=n).first() or SuperAdmin.query.filter_by(username=n).first() for n in names):
        flash('❌ اسم مستخدم محجوز مسبقاً — اختر أسماء أخرى.', 'error')
        return redirect(url_for('owner_dashboard'))
    branch = PrintShop(name=name, owner_name=hq.owner_name, phone=_clip(f.get('phone'), 30), address=_clip(f.get('address'), 255),
                       parent_id=hq_id, max_branches=1, business_type=f.get('business_type') if f.get('business_type') in PRESETS else hq.business_type)
    db.session.add(branch)
    db.session.flush()
    db.session.add(User(shop_id=branch.id, full_name=_clip(f.get('admin_name'), 100) or f'أدمن {name}', username=a_user,
                        password_hash=generate_password_hash(a_pass), role='shop_admin'))
    if c_user:
        db.session.add(User(shop_id=branch.id, full_name=_clip(f.get('cashier_name'), 100) or f'كاشير {name}', username=c_user,
                            password_hash=generate_password_hash(c_pass), role='cashier'))
    if f.get('copy_from_hq') == '1':
        for s in Service.query.filter_by(shop_id=hq_id).all():
            db.session.add(Service(shop_id=branch.id, name=s.name, cost_price=s.cost_price, price_reg=s.price_reg, price_bulk=s.price_bulk,
                                   bulk_threshold=s.bulk_threshold, threshold=s.threshold, stock=-1.0, unit_name=s.unit_name,
                                   is_banner=s.is_banner, is_favorite=s.is_favorite, is_measurement_based=s.is_measurement_based,
                                   price_per_sqm=s.price_per_sqm))
        for fs in FinishingService.query.filter_by(shop_id=hq_id).all():
            db.session.add(FinishingService(shop_id=branch.id, name=fs.name, price=fs.price, is_active=fs.is_active))
        for b in Binding.query.filter_by(shop_id=hq_id).all():
            db.session.add(Binding(shop_id=branch.id, name=b.name, price_per_unit=b.price_per_unit))
        ist = InvoiceSetting.query.filter_by(shop_id=hq_id).first()
        if ist:
            db.session.add(InvoiceSetting(shop_id=branch.id, data=ist.data))
    elif f.get('business_type') in PRESETS:
        apply_preset(branch.id, f.get('business_type'))
    db.session.commit()
    flash(f'✅ تم إنشاء فرع «{name}» مع حساب أدمن' + (' وحساب كاشير.' if c_user else '.'), 'success')
    return redirect(url_for('owner_dashboard'))


@app.route('/owner/switch/<int:sid>')
@login_required(role='owner')
@owner_required
def owner_switch(sid):
    hq_id = session.get('home_shop_id') or root_shop_id(session.get('shop_id'))
    if sid not in [s.id for s in group_shops(hq_id)]:
        abort(403)
    shop = db.session.get(PrintShop, sid)
    session['home_shop_id'] = hq_id
    session['shop_id'] = sid
    session['shop_name'] = shop.name
    return redirect(url_for('shop_admin_dashboard'))


@app.route('/api/stock/trigger_shortage_order', methods=['POST'])
@login_required(role='cashier')
def trigger_shortage_order():
    sid = shop_id()
    shop = db.session.get(PrintShop, sid)
    if not shop or not shop.phone:
        return jsonify({'success': False, 'message': 'رقم هاتف صاحب المطبعة غير مسجل في بيانات المطبعة!'})

    shortages = Service.query.filter(Service.shop_id == sid, Service.stock >= 0, Service.stock <= Service.threshold).all()
    if not shortages:
        return jsonify({'success': False, 'message': 'لا توجد خامات في حد النواقص حالياً! المخزن آمن ✅'})

    items_txt = ""
    for idx, s in enumerate(shortages, 1):
        items_txt += f"{idx}. *{s.name}*: الرصيد المتبقي ({s.stock}) | حد الطلب ({s.threshold})\n"

    msg = f"⚠️ *تقرير وأمر نواقص خامات عاجل*\n🏢 المطبعة: {shop.name}\n👤 المسؤول الراسل: {session.get('full_name') or session.get('username')}\n📅 التاريخ: {now_str()}\n\n*الخامات التي شارفت على النفاد:*\n{items_txt}\nيرجى عمل طلبيات توريد فورية للحفاظ على استمرار خطوط الإنتاج."

    clean_phone = sanitize_egyptian_phone(shop.phone)
    if not clean_phone:
        return jsonify({'success': False, 'message': 'رقم هاتف صاحب المطبعة غير مكتوب بصيغة صحيحة!'})

    wa_url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={urllib.parse.quote(msg)}"

    return jsonify({'success': True, 'whatsapp_url': wa_url, 'count': len(shortages)})

@app.route('/api/b2b/partners', methods=['GET', 'POST'])
@login_required(role='shop_admin')
def b2b_partners_api():
    sid = shop_id()
    if request.method == 'POST':
        data = request.json or {}
        name = data.get('partner_name', '').strip()
        phone = data.get('phone', '').strip()
        if not name:
            return jsonify({'success': False, 'message': 'اسم المطبعة/الوكالة الشريكة مطلوب!'})
        partner = B2BPartner(shop_id=sid, partner_name=name, phone=phone, notes=data.get('notes', ''))
        db.session.add(partner)
        db.session.commit()
        return jsonify({'success': True, 'id': partner.id, 'name': partner.partner_name})

    partners = B2BPartner.query.filter_by(shop_id=sid).all()
    res = []
    for p in partners:
        gives = db.session.query(func.coalesce(func.sum(B2BTransaction.amount), 0)).filter_by(shop_id=sid, partner_id=p.id, trans_type='give').scalar()
        takes = db.session.query(func.coalesce(func.sum(B2BTransaction.amount), 0)).filter_by(shop_id=sid, partner_id=p.id, trans_type='take').scalar()
        settles = db.session.query(func.coalesce(func.sum(B2BTransaction.amount), 0)).filter_by(shop_id=sid, partner_id=p.id, trans_type='settle').scalar()
        balance = takes - gives - settles
        res.append({'id': p.id, 'name': p.partner_name, 'phone': p.phone, 'balance': balance})
    return jsonify(res)

def _partner_balance(sid, pid):
    def total(kind):
        return db.session.query(func.coalesce(func.sum(B2BTransaction.amount), 0)).filter_by(
            shop_id=sid, partner_id=pid, trans_type=kind).scalar() or 0.0
    return total('take') - total('give') - total('settle')


@app.route('/api/b2b/partner/<int:pid>/statement')
@login_required(role='shop_admin')
def b2b_statement(pid):
    sid = shop_id()
    p = db.session.get(B2BPartner, pid)
    if not p or p.shop_id != sid:
        return jsonify({'success': False, 'message': 'الوكالة غير موجودة!'}), 404
    rows = B2BTransaction.query.filter_by(shop_id=sid, partner_id=pid).order_by(B2BTransaction.id.desc()).limit(300).all()
    return jsonify({'success': True, 'name': p.partner_name, 'phone': p.phone, 'balance': _partner_balance(sid, pid),
                    'rows': [{'id': r.id, 'type': r.trans_type, 'amount': r.amount, 'desc': r.description,
                              'date': r.date_str, 'by': r.created_by} for r in rows]})


@app.route('/api/b2b/partner/<int:pid>/delete', methods=['POST'])
@login_required(role='shop_admin')
def b2b_delete_partner(pid):
    sid = shop_id()
    p = db.session.get(B2BPartner, pid)
    if not p or p.shop_id != sid:
        return jsonify({'success': False, 'message': 'الوكالة غير موجودة!'}), 404
    B2BTransaction.query.filter_by(shop_id=sid, partner_id=pid).delete()
    db.session.delete(p)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم حذف الوكالة وكشف حسابها.'})


@app.route('/api/b2b/transaction/<int:tid>/delete', methods=['POST'])
@login_required(role='shop_admin')
def b2b_delete_transaction(tid):
    sid = shop_id()
    t = db.session.get(B2BTransaction, tid)
    if not t or t.shop_id != sid:
        return jsonify({'success': False, 'message': 'الحركة غير موجودة!'}), 404
    db.session.delete(t)
    db.session.commit()
    return jsonify({'success': True, 'balance': _partner_balance(sid, t.partner_id)})


@app.route('/api/b2b/transaction/add', methods=['POST'])
@login_required(role='shop_admin')
def b2b_add_transaction():
    sid = shop_id()
    data = request.json or {}
    partner_id = to_int(data.get('partner_id'))
    amount = to_float(data.get('amount'))
    trans_type = data.get('trans_type')
    desc = data.get('description', '').strip()
    if not partner_id or amount <= 0 or not desc:
        return jsonify({'success': False, 'message': 'بيانات المعاملة غير مكتملة!'})
    partner = db.session.get(B2BPartner, partner_id)
    if not partner or partner.shop_id != sid:
        return jsonify({'success': False, 'message': 'الوكالة الشريكة غير موجودة!'})
    if trans_type not in ('give', 'take', 'settle'):
        return jsonify({'success': False, 'message': 'نوع المعاملة غير صحيح!'})

    trans = B2BTransaction(
        shop_id=sid, partner_id=partner_id, trans_type=trans_type,
        amount=amount, description=desc, date_str=now_str(),
        created_by=session.get('full_name') or session.get('username')
    )
    db.session.add(trans)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم تسجيل المعاملة بنجاح.'})

@app.route('/receipt/<string:token>')
def view_thermal_receipt(token):
    invoice = Invoice.query.filter_by(token=token).first()
    if not invoice:
        return ("<html lang='ar' dir='rtl'><meta charset='utf-8'><body style='font-family:Tahoma;text-align:center;padding:60px'>"
                "<h2>الفاتورة غير موجودة</h2><p>تأكد من رقم الفاتورة أو من الرابط.</p></body></html>"), 404
    shop = db.session.get(PrintShop, invoice.shop_id)
    S = get_invoice_settings(invoice.shop_id)
    items = InvoiceItem.query.filter_by(invoice_token=token, shop_id=invoice.shop_id).order_by(InvoiceItem.id).all()
    return render_receipt(invoice, items, shop, S, qr_url=url_for('view_thermal_receipt', token=token, _external=True))


@app.route('/portal/<string:phone>')
def customer_portal(phone):
    customer = PremiumCustomer.query.filter_by(phone=phone).first()
    invoices = Invoice.query.filter_by(customer_phone=phone).order_by(Invoice.id.desc()).all()
    if not customer and not invoices:
        abort(404)
    sid = customer.shop_id if customer else invoices[0].shop_id
    invoices = [i for i in invoices if i.shop_id == sid]
    shop = db.session.get(PrintShop, sid)
    if not customer:
        customer = type('obj', (object,), {
            'name': invoices[0].customer_name if invoices else 'عميل معتمد',
            'phone': phone, 'tier_name': 'عميل نشط', 'discount_percentage': 0.0
        })
    total_spent = sum(float(i.grand_total or 0) for i in invoices)
    total_remaining = sum(float(i.remaining or 0) for i in invoices)
    return render_template('portal.html', customer=customer, invoices=invoices,
                           total_spent=total_spent, total_remaining=total_remaining,
                           press_name=shop.name if shop else 'المطبعة')


# ---------- تصميم الفاتورة: حفظ / استرجاع الافتراضي / معاينة حية ----------
@app.route('/admin/invoice-settings/save', methods=['POST'])
@login_required(role='shop_admin')
def admin_invoice_settings_save():
    sid = shop_id()
    S = sanitize_invoice_settings(request.json or {})
    row = InvoiceSetting.query.filter_by(shop_id=sid).first()
    if not row:
        row = InvoiceSetting(shop_id=sid)
        db.session.add(row)
    row.data = json.dumps(S, ensure_ascii=False)
    db.session.commit()
    return jsonify({'success': True, 'settings': S, 'message': 'تم حفظ تصميم الفاتورة — هيظهر على كل الفواتير الجاية والقديمة.'})


@app.route('/admin/invoice-settings/reset', methods=['POST'])
@login_required(role='shop_admin')
def admin_invoice_settings_reset():
    sid = shop_id()
    row = InvoiceSetting.query.filter_by(shop_id=sid).first()
    if row:
        db.session.delete(row)
        db.session.commit()
    return jsonify({'success': True, 'settings': sanitize_invoice_settings({}), 'message': 'تمت إعادة التصميم الافتراضي.'})


@app.route('/admin/invoice-settings/preview', methods=['POST'])
@login_required(role='shop_admin')
def admin_invoice_settings_preview():
    sid = shop_id()
    try:
        S = sanitize_invoice_settings(json.loads(request.form.get('settings', '{}')))
    except ValueError:
        S = get_invoice_settings(sid)
    shop = db.session.get(PrintShop, sid)
    token = (request.form.get('token') or '').strip()
    inv = Invoice.query.filter_by(token=token, shop_id=sid).first() if token else None
    if inv:
        items = InvoiceItem.query.filter_by(invoice_token=token, shop_id=sid).order_by(InvoiceItem.id).all()
    else:
        inv, items = sample_invoice()
    return render_receipt(inv, items, shop, S, preview=True,
                          qr_url=url_for('view_thermal_receipt', token=inv.token, _external=True))


@app.route('/admin/export/excel')
@login_required(role='shop_admin')
def admin_export_excel():
    sid = shop_id()
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "الفواتير"
    ws1.sheet_view.rightToLeft = True
    ws1.append(["الكود", "العميل", "الهاتف", "الكاشير", "التاريخ", "الإجمالي", "المدفوع", "الباقي", "الحالة"])
    for inv in Invoice.query.filter_by(shop_id=sid).order_by(Invoice.id.desc()).all():
        ws1.append([inv.token, inv.customer_name, inv.customer_phone,
                    inv.cashier_full_name, inv.date_str, inv.grand_total,
                    inv.deposit, inv.remaining, inv.delivery_status])
    ws2 = wb.create_sheet("البنود")
    ws2.sheet_view.rightToLeft = True
    ws2.append(["كود الفاتورة", "البند", "الكمية", "الطول", "العرض", "سعر الوحدة", "الإجمالي"])
    for it in InvoiceItem.query.filter_by(shop_id=sid).order_by(InvoiceItem.id.desc()).all():
        ws2.append([it.invoice_token, it.name, it.qty, it.height, it.width, it.unit_price, it.total])
    for ws in (ws1, ws2):
        for col in ws.columns:
            width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(40, width + 4)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"invoices_{today_str()}.xlsx")


# ---------- الخدمات والمخزون ----------
def _service_fields(form):
    stock_raw = (form.get('stock') or '').strip()
    return dict(
        name=_clip(form.get('name'), 150),
        cost_price=max(0.0, to_float(form.get('cost_price'))),
        price_reg=max(0.0, to_float(form.get('price_reg'))),
        price_bulk=max(0.0, to_float(form.get('price_bulk'))),
        bulk_threshold=max(0.0, to_float(form.get('bulk_threshold'))),
        threshold=max(0.0, to_float(form.get('threshold'), 10)),
        stock=to_float(stock_raw, -1.0) if stock_raw else -1.0,
        unit_name=_clip(form.get('unit_name'), 50) or 'بالقطعة',
        is_banner=form.get('is_banner') in ('1', 'true', 'on'),
        is_favorite=form.get('is_favorite') in ('1', 'true', 'on'),
        is_measurement_based=form.get('is_measurement_based') in ('1', 'true', 'on'),
        price_per_sqm=max(0.0, to_float(form.get('price_per_sqm'))))


@app.route('/admin/service/add', methods=['POST'])
@login_required(role='shop_admin')
def admin_add_service():
    f = _service_fields(request.form)
    if not f['name']:
        flash('❌ اسم الخدمة مطلوب.', 'error')
        return redirect(url_for('shop_admin_dashboard') + '#services')
    db.session.add(Service(shop_id=shop_id(), **f))
    db.session.commit()
    flash(f'✅ تمت إضافة «{f["name"]}».', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#services')


@app.route('/admin/service/<int:id>/edit', methods=['POST'])
@login_required(role='shop_admin')
def admin_edit_service(id):
    s = db.session.get(Service, id)
    if not s or s.shop_id != shop_id():
        abort(404)
    f = _service_fields(request.form)
    if not f['name']:
        flash('❌ اسم الخدمة مطلوب.', 'error')
    else:
        for k, v in f.items():
            setattr(s, k, v)
        db.session.commit()
        flash(f'✅ تم حفظ تعديلات «{s.name}».', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#services')


@app.route('/admin/service/delete/<int:id>', methods=['POST'])
@login_required(role='shop_admin')
def admin_delete_service(id):
    s = db.session.get(Service, id)
    if s and s.shop_id == shop_id():
        name = s.name
        db.session.delete(s)
        db.session.commit()
        flash(f'تم حذف «{name}». الفواتير القديمة لم تتأثر.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#services')


# ---------- التجليد ----------
@app.route('/admin/binding/add', methods=['POST'])
@login_required(role='shop_admin')
def admin_add_binding():
    name = _clip(request.form.get('name'), 100)
    if name:
        db.session.add(Binding(shop_id=shop_id(), name=name,
                               price_per_unit=max(0.0, to_float(request.form.get('price_per_unit')))))
        db.session.commit()
        flash('✅ تمت إضافة أسلوب التجليد.', 'success')
    else:
        flash('❌ اكتب اسم أسلوب التجليد.', 'error')
    return redirect(url_for('shop_admin_dashboard') + '#bindings')


@app.route('/admin/binding/<int:id>/edit', methods=['POST'])
@login_required(role='shop_admin')
def admin_edit_binding(id):
    b = db.session.get(Binding, id)
    if not b or b.shop_id != shop_id():
        abort(404)
    name = _clip(request.form.get('name'), 100)
    if name:
        b.name = name
        b.price_per_unit = max(0.0, to_float(request.form.get('price_per_unit')))
        db.session.commit()
        flash('✅ تم تحديث أسلوب التجليد.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#bindings')


@app.route('/admin/binding/<int:id>/delete', methods=['POST'])
@login_required(role='shop_admin')
def admin_delete_binding(id):
    b = db.session.get(Binding, id)
    if b and b.shop_id == shop_id():
        db.session.delete(b)
        db.session.commit()
        flash('تم حذف أسلوب التجليد.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#bindings')


# ---------- العملاء المتميزون ----------
@app.route('/admin/customer/add', methods=['POST'])
@login_required(role='shop_admin')
def admin_add_customer():
    name = _clip(request.form.get('name'), 100)
    if not name:
        flash('❌ اسم العميل مطلوب.', 'error')
        return redirect(url_for('shop_admin_dashboard') + '#debts')
    db.session.add(PremiumCustomer(shop_id=shop_id(), name=name,
        phone=_clip(request.form.get('phone'), 50),
        discount_percentage=min(100.0, max(0.0, to_float(request.form.get('discount_percentage')))),
        tier_name=_clip(request.form.get('tier_name'), 50)))
    db.session.commit()
    flash('✅ تم تسجيل العميل المتميز.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#debts')


@app.route('/admin/customer/<int:id>/edit', methods=['POST'])
@login_required(role='shop_admin')
def admin_edit_customer(id):
    c = db.session.get(PremiumCustomer, id)
    if not c or c.shop_id != shop_id():
        abort(404)
    name = _clip(request.form.get('name'), 100)
    if name:
        c.name = name
        c.phone = _clip(request.form.get('phone'), 50)
        c.discount_percentage = min(100.0, max(0.0, to_float(request.form.get('discount_percentage'))))
        c.tier_name = _clip(request.form.get('tier_name'), 50)
        db.session.commit()
        flash('✅ تم تحديث بيانات العميل.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#debts')


@app.route('/admin/customer/<int:id>/delete', methods=['POST'])
@login_required(role='shop_admin')
def admin_delete_customer(id):
    c = db.session.get(PremiumCustomer, id)
    if c and c.shop_id == shop_id():
        db.session.delete(c)
        db.session.commit()
        flash('تم حذف العميل المتميز.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#debts')


# ---------- الموظفون ----------
@app.route('/admin/cashier/add', methods=['POST'])
@login_required(role='shop_admin')
def admin_add_cashier():
    sid = shop_id()
    username = _clip(request.form.get('username'), 50)
    password = request.form.get('password', '')
    full_name = _clip(request.form.get('full_name'), 100)
    role = request.form.get('role', 'cashier')
    if role not in ('cashier', 'supervisor'):
        role = 'cashier'
    back = url_for('shop_admin_dashboard') + '#cashiers'
    if not full_name or not username:
        flash('❌ الاسم الكامل واسم المستخدم مطلوبين.', 'error')
        return redirect(back)
    if User.query.filter_by(username=username).first() or SuperAdmin.query.filter_by(username=username).first():
        flash('❌ اسم المستخدم محجوز مسبقاً — جرّب اسماً آخر.', 'error')
        return redirect(back)
    if len(password) < 6:
        flash('❌ كلمة المرور يجب أن تكون 6 أحرف على الأقل!', 'error')
        return redirect(back)
    db.session.add(User(shop_id=sid, full_name=full_name, username=username,
                        password_hash=generate_password_hash(password),
                        base_salary=max(0.0, to_float(request.form.get('base_salary'))),
                        role=role))
    db.session.commit()
    flash('✅ تم إنشاء حساب الموظف وتوليد كارت الدخول (ID).', 'success')
    return redirect(back)


@app.route('/admin/cashier/<int:id>/edit', methods=['POST'])
@login_required(role='shop_admin')
def admin_edit_cashier(id):
    c = db.session.get(User, id)
    if not c or c.shop_id != shop_id():
        abort(404)
    back = url_for('shop_admin_dashboard') + '#cashiers'
    name = _clip(request.form.get('full_name'), 100)
    if name:
        c.full_name = name
    c.base_salary = max(0.0, to_float(request.form.get('base_salary')))
    if c.role != 'shop_admin':
        role = request.form.get('role', c.role)
        if role in ('cashier', 'supervisor'):
            c.role = role
        c.is_active = request.form.get('is_active') in ('1', 'on', 'true')
    new_pwd = request.form.get('new_password', '')
    if new_pwd:
        if len(new_pwd) < 6:
            flash('❌ كلمة المرور الجديدة قصيرة (6 أحرف على الأقل). لم يتم حفظ التعديلات.', 'error')
            db.session.rollback()
            return redirect(back)
        c.password_hash = generate_password_hash(new_pwd)
    db.session.commit()
    flash(f'✅ تم حفظ بيانات {c.full_name}.', 'success')
    return redirect(back)


@app.route('/admin/cashier/<int:id>/reset_payroll', methods=['POST'])
@login_required(role='shop_admin')
def admin_reset_payroll(id):
    c = db.session.get(User, id)
    if c and c.shop_id == shop_id():
        c.bonus = c.advances = c.deductions = 0.0
        db.session.add(AuditLog(shop_id=c.shop_id, action='تصفير حركات راتب', action_by=session.get('username', ''),
                                reason=f'إغلاق شهر الموظف {c.full_name}'))
        db.session.commit()
        flash(f'✅ تم تصفير المكافآت والسلف والخصومات لـ {c.full_name}.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#cashiers')


@app.route('/admin/cashier/delete/<int:id>', methods=['POST'])
@login_required(role='shop_admin')
def admin_delete_cashier(id):
    c = db.session.get(User, id)
    if c and c.shop_id == shop_id() and c.role != 'shop_admin':
        db.session.delete(c)
        db.session.commit()
        flash('تم حذف حساب الموظف.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#cashiers')


@app.route('/admin/cashier/log_action', methods=['POST'])
@login_required(role='shop_admin')
def admin_cashier_log_action():
    sid = shop_id()
    c = db.session.get(User, to_int(request.form.get('cashier_id')))
    action_type = request.form.get('action_type', '')
    amount = to_float(request.form.get('amount'))
    if c and c.shop_id == sid and amount > 0 and action_type in ('مكافأة', 'سلفة', 'خصم'):
        if action_type == 'مكافأة':
            c.bonus = (c.bonus or 0) + amount
        elif action_type == 'سلفة':
            c.advances = (c.advances or 0) + amount
            db.session.add(Expense(shop_id=sid, title=f"سلفة للكاشير {c.full_name}",
                amount=amount, cashier_name=c.full_name,
                created_by=session.get('username', ''), date_str=now_str(),
                notes="سلفة آلية من حساب الكاشير"))
        else:
            c.deductions = (c.deductions or 0) + amount
        db.session.add(CashierLog(shop_id=sid, cashier_username=c.username,
            action_type=action_type, amount=amount, date_str=now_str(), reason=action_type))
        db.session.commit()
        flash(f'✅ تم قيد ({action_type}) {amount:,.2f} ج.م لـ {c.full_name}.', 'success')
    else:
        flash('❌ اختر النوع واكتب مبلغاً أكبر من صفر.', 'error')
    return redirect(url_for('shop_admin_dashboard') + '#cashiers')


# ---------- المصاريف ----------
@app.route('/admin/expense/add', methods=['POST'])
@login_required(role='shop_admin')
def admin_add_expense():
    title = _clip(request.form.get('title'), 255)
    amount = to_float(request.form.get('amount'))
    if title and amount > 0:
        db.session.add(Expense(shop_id=shop_id(), title=title, amount=amount,
            cashier_name=session.get('full_name', 'الإدارة'),
            created_by=session.get('username', ''),
            date_str=now_str(), notes=(request.form.get('notes') or '').strip()[:500]))
        db.session.commit()
        flash('✅ تم قيد المصروف في الخزينة.', 'success')
    else:
        flash('❌ اكتب بيان المصروف ومبلغاً أكبر من صفر.', 'error')
    return redirect(url_for('shop_admin_dashboard') + '#expenses')


@app.route('/admin/expense/delete/<int:id>', methods=['POST'])
@login_required(role='shop_admin')
def admin_delete_expense(id):
    e = db.session.get(Expense, id)
    if e and e.shop_id == shop_id():
        db.session.delete(e)
        db.session.commit()
        flash('تم حذف المصروف.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#expenses')


# ---------- الفواتير ----------
@app.route('/admin/invoice/delete/<string:token>', methods=['POST'])
@login_required(role='shop_admin')
def admin_delete_invoice(token):
    sid = shop_id()
    inv = Invoice.query.filter_by(token=token, shop_id=sid).first()
    back = request.form.get('back') or ''
    back = back if back.startswith('/admin') else url_for('shop_admin_dashboard') + '#invoices'
    if inv:
        for item in InvoiceItem.query.filter_by(invoice_token=token, shop_id=sid).all():
            srv = db.session.get(Service, item.service_id)
            if srv and srv.shop_id == sid and srv.stock >= 0:
                srv.stock += item.qty
        InvoiceItem.query.filter_by(invoice_token=token, shop_id=sid).delete()
        cname = inv.customer_name
        db.session.delete(inv)
        db.session.flush()
        recalc_customer(sid, cname)
        db.session.add(AuditLog(shop_id=sid, action='حذف فاتورة (أدمن)', invoice_token=token,
            action_by=session.get('username', ''), reason=_clip(request.form.get('reason'), 200) or 'حذف مباشر من لوحة الأدمن'))
        db.session.commit()
        flash(f'تم حذف الفاتورة #{token} وإرجاع الكميات للمخزن.', 'success')
    return redirect(back)


# ---------- بيانات المطبعة وحساب المستخدم ----------
@app.route('/admin/shop/update', methods=['POST'])
@login_required(role='shop_admin')
def admin_update_shop():
    shop = db.session.get(PrintShop, shop_id())
    name = _clip(request.form.get('name'), 150)
    if not shop or not name:
        flash('❌ اسم المطبعة مطلوب.', 'error')
    else:
        shop.name = name
        shop.owner_name = _clip(request.form.get('owner_name'), 120)
        shop.phone = _clip(request.form.get('phone'), 30)
        shop.address = _clip(request.form.get('address'), 255)
        db.session.commit()
        session['shop_name'] = shop.name
        flash('✅ تم حفظ بيانات المطبعة.', 'success')
    return redirect(url_for('shop_admin_dashboard') + '#settings')


@app.route('/account/password', methods=['POST'])
@login_required()
def account_password():
    current = request.form.get('current_password', '')
    new = request.form.get('new_password', '')
    role = session.get('role')
    acct = (SuperAdmin.query.filter_by(username=session.get('username')).first() if role == 'super_admin'
            else db.session.get(User, session.get('user_id')))
    if role == 'super_admin':
        back = url_for('sa_dashboard')
    elif role == 'shop_admin':
        back = url_for('shop_admin_dashboard') + '#settings'
    else:
        back = url_for('cashier_dashboard')
    if not acct or not check_password_hash(acct.password_hash, current):
        flash('❌ كلمة المرور الحالية غير صحيحة.', 'error')
    elif len(new) < 6:
        flash('❌ كلمة المرور الجديدة لازم تكون 6 أحرف على الأقل.', 'error')
    else:
        acct.password_hash = generate_password_hash(new)
        db.session.commit()
        flash('✅ تم تغيير كلمة المرور بنجاح.', 'success')
    return redirect(back)


# ------------------------------ الترحيل وبناء الجداول ------------------------------
_NEW_COLUMNS = {
    'users': [('barcode_token', 'VARCHAR(64)')],
    'plans': [('max_branches', 'INTEGER DEFAULT 1')],
    'print_shops': [('parent_id', 'INTEGER'), ('max_branches', 'INTEGER DEFAULT 1'), ('business_type', "VARCHAR(30) DEFAULT 'general'")],
    'invoices': [('extras_json', "TEXT DEFAULT '[]'"), ('extras_total', 'FLOAT DEFAULT 0'), ('customer_tier', "VARCHAR(60) DEFAULT ''")],
}


def _auto_migrate():
    """يضيف الأعمدة الجديدة لقاعدة بيانات قديمة بدون ما يمسح أي بيانات."""
    if not os.path.exists(DB_PATH):
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for table, cols in _NEW_COLUMNS.items():
            cur.execute(f"PRAGMA table_info({table})")
            have = [row[1] for row in cur.fetchall()]
            if not have:
                continue
            for name, ddl in cols:
                if name not in have:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        conn.commit()
        conn.close()
    except Exception as ex:
        print("Auto migration notice:", ex, file=sys.stderr)

def _seed():
    if not SuperAdmin.query.first():
        # أول تشغيل: بيانات السوبر أدمن من متغيرات البيئة، أو كلمة مرور عشوائية تُطبع مرة واحدة وتُحفظ في initial_credentials.txt
        sa_user = os.environ.get('SA_USERNAME', 'sa')
        sa_pass = os.environ.get('SA_PASSWORD')
        generated = not sa_pass
        sa_pass = sa_pass or secrets.token_urlsafe(9)
        db.session.add(SuperAdmin(username=sa_user, password_hash=generate_password_hash(sa_pass)))
        if generated:
            try:
                path = os.path.join(BASE_DIR, 'initial_credentials.txt')
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(f'Super admin login (change it after first sign-in)\nusername: {sa_user}\npassword: {sa_pass}\n')
                os.chmod(path, 0o600)
            except OSError:
                pass
            print(f'[KIRO] Super admin created — username: {sa_user}  password: {sa_pass}  (saved in initial_credentials.txt)', file=sys.stderr)

    if Plan.query.count() == 0:
        for name, price, days, lifetime, branches in [
            ('تجريبي 14 يوم', 0, 14, False, 1),
            ('شهرية', 300, 30, False, 1),
            ('سنوية', 2700, 365, False, 1),
            ('مدى الحياة', 8000, 0, True, 1),
            ('سلسلة فروع (5 فروع) — سنوية', 9000, 365, False, 5),
        ]:
            db.session.add(Plan(name=name, price=price, duration_days=days, is_lifetime=lifetime, max_branches=branches))
    db.session.commit()

_UI_VER = hashlib.md5(b''.join(open(os.path.join(BASE_DIR, 'static', f), 'rb').read() for f in ('ui.css', 'ui.js'))).hexdigest()[:8]

with app.app_context():
    db.create_all()
    _auto_migrate()
    _seed()

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)