from conftest import Client
import json
from werkzeug.security import generate_password_hash


def setup_shop(mod, name='مطبعة', max_branches=1, owner=False, prefix='a'):
    with mod.app.app_context():
        shop = mod.PrintShop(name=name, max_branches=max_branches)
        mod.db.session.add(shop); mod.db.session.flush()
        role = 'owner' if owner else 'shop_admin'
        mod.db.session.add(mod.User(shop_id=shop.id, full_name='مدير', username=f'{prefix}_admin',
                                    password_hash=generate_password_hash('secret1'), role=role))
        mod.db.session.add(mod.User(shop_id=shop.id, full_name='كاشير', username=f'{prefix}_cash',
                                    password_hash=generate_password_hash('secret1'), role='cashier'))
        mod.db.session.add(mod.Subscription(shop_id=shop.id, is_lifetime=True))
        mod.db.session.add(mod.Service(shop_id=shop.id, name='تصوير A4', price_reg=1, stock=100, threshold=10))
        mod.db.session.commit()
        return shop.id


def invoice(client, name='سارة', total=100, deposit=0, extras=None, token=None, reason=None):
    body = {'customer_name': name, 'cart': [{'id': 0, 'name': 'بنر', 'qty': 1, 'unit_price': total, 'total': total}],
            'deposit': deposit, 'extras': extras or []}
    if token:
        body['token'] = token; body['edit_reason'] = reason
    return client.post('/cashier/invoice/save', json=body).get_json()


def test_login_has_no_card_login(client):
    html = client.get('/').get_data(as_text=True)
    assert 'barcode' not in html.lower() and 'username' in html
    assert client.get('/auth/barcode_login/xyz').status_code == 404


def test_extras_customer_tier_and_payments(appmod, client):
    sid = setup_shop(appmod, prefix='t1')
    with appmod.app.app_context():
        appmod.save_config(sid, {'tiers': [{'name': 'مميز', 'min_invoices': 3, 'min_spent': 300, 'discount': 10}]})
        appmod.db.session.commit()
    client.login('t1_cash', 'secret1')
    d = invoice(client, 'منى', 100, 0, extras=[{'name': 'سولفان', 'qty': 2, 'price': 10}])
    assert d['success']
    d2 = client.get('/cashier/invoice/get_customer_discount/منى').get_json()
    assert d2['exists'] and d2['invoices_count'] == 1
    invoice(client, 'منى', 100); last = invoice(client, 'منى', 100)
    r = client.get(f"/receipt/{last['token']}").get_data(as_text=True)
    assert 'مميز' in r
    assert client.get('/cashier/invoice/get_customer_discount/منى').get_json()['discount'] == 10
    # سداد جزئي على فاتورة محددة ثم عام
    det = client.get('/api/debt/customer?name=منى').get_json()
    assert det['total_debt'] == 320
    tok = det['invoices'][0]['token']
    p = client.post('/api/debt/pay', json={'customer_name': 'منى', 'amount': 50, 'target': tok}).get_json()
    assert p['success'] and p['applied'] == 50
    p = client.post('/api/debt/pay', json={'customer_name': 'منى', 'amount': 1000}).get_json()
    assert p['success'] and p['remaining_unapplied'] == 730
    det = client.get('/api/debt/customer?name=منى').get_json()
    assert det['total_debt'] == 0 and len(det['payments']) >= 2 and det['payments'][0]['date']


def test_old_balance_and_quick_sales(appmod, client):
    sid = setup_shop(appmod, prefix='t2')
    client.login('t2_cash', 'secret1')
    assert client.post('/api/old_balance/add', json={'customer_name': 'علي', 'amount': 80, 'note': 'قديم'}).get_json()['success']
    summary = client.get('/api/debt/customers').get_json()
    assert summary[0]['name'] == 'علي' and summary[0]['total_debt'] == 80
    p = client.post('/api/debt/pay', json={'customer_name': 'علي', 'amount': 30}).get_json()
    assert p['success']
    with appmod.app.app_context():
        svc = appmod.Service.query.filter_by(shop_id=sid).first(); svc_id = svc.id
    q = client.post('/api/quick/add', json={'service_id': svc_id, 'qty': 20, 'wasted': 2}).get_json()
    assert q['success']
    lst = client.get('/api/quick/list').get_json()
    assert lst['total'] == 20 and lst['groups'][0]['wasted'] == 2
    with appmod.app.app_context():
        assert appmod.db.session.get(appmod.Service, svc_id).stock == 78
    assert client.post(f"/api/quick/{lst['rows'][0]['id']}/delete").get_json()['success']
    with appmod.app.app_context():
        assert appmod.db.session.get(appmod.Service, svc_id).stock == 100


def test_cashier_edit_permissions(appmod, client):
    sid = setup_shop(appmod, prefix='t3')
    client.login('t3_cash', 'secret1')
    d = invoice(client, 'نور', 100)
    tok = d['token']
    assert client.get(f'/cashier/invoice/{tok}/data').get_json()['success']
    assert not invoice(client, 'نور', 150, token=tok, reason='')['success']           # السبب مطلوب
    assert invoice(client, 'نور', 150, token=tok, reason='تغيير السعر')['success']
    with appmod.app.app_context():
        appmod.save_config(sid, {'cashier_edit': 'off'}); appmod.db.session.commit()
    assert client.get(f'/cashier/invoice/{tok}/data').status_code == 403
    assert invoice(client, 'نور', 90, token=tok, reason='x').get('success') is not True


def test_owner_branches_isolation_and_limit(appmod, client):
    hq = setup_shop(appmod, 'السلسلة', max_branches=2, owner=True, prefix='o')
    client.login('o_admin', 'secret1')
    assert client.get('/owner').status_code == 200
    r = client.post('/owner/branch/add', data={'name': 'فرع 1', 'admin_username': 'b1_admin', 'admin_password': 'secret1',
                                               'cashier_username': 'b1_cash', 'cashier_password': 'secret1', 'business_type': 'gifts'})
    assert r.status_code == 302
    r = client.post('/owner/branch/add', data={'name': 'فرع 2', 'admin_username': 'b2_admin', 'admin_password': 'secret1'})
    with appmod.app.app_context():
        assert appmod.PrintShop.query.filter_by(parent_id=hq).count() == 1       # الحد = 2 (الرئيسي + فرع)
        b1 = appmod.PrintShop.query.filter_by(parent_id=hq).first().id
        assert appmod.Service.query.filter_by(shop_id=b1).count() > 3             # قالب الهدايا اتطبّق
    # الأدمن يتنقل بين الفروع ويشوف بيانات كل فرع لوحده
    assert client.get(f'/owner/switch/{b1}').status_code == 302
    invoice(client, 'عميل فرع', 500)
    other = Client(appmod); other.login('b1_admin', 'secret1')
    assert 'عميل فرع' in other.get('/admin').get_data(as_text=True)
    hq_admin = Client(appmod); hq_admin.login('o_cash', 'secret1')
    assert 'عميل فرع' not in hq_admin.get('/cashier').get_data(as_text=True)
    assert other.get('/owner').status_code == 302                                   # أدمن الفرع مش مالك


def test_preset_language_and_pages(appmod, client):
    sid = setup_shop(appmod, prefix='t5')
    client.login('t5_admin', 'secret1')
    assert client.post('/admin/preset/apply', data={'preset': 'copy_center'}).status_code == 302
    with appmod.app.app_context():
        assert appmod.Service.query.filter_by(shop_id=sid).count() > 5
        assert appmod.FinishingService.query.filter_by(shop_id=sid).count() >= 3
    for path in ['/admin', '/cashier', '/cashier/debts', '/cashier/quick']:
        assert client.get(path).status_code == 200, path
    r = client.get('/lang/en'); assert r.status_code == 302
    assert 'lang="en"' in client.get('/admin').get_data(as_text=True)
