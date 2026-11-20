import os, re, sys, tempfile, importlib
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


@pytest.fixture(scope='session')
def appmod():
    tmp = tempfile.mkdtemp()
    os.environ['DATABASE_PATH'] = os.path.join(tmp, 'test.db')
    os.environ['SECRET_KEY'] = 'test-secret'
    mod = importlib.import_module('app')
    mod.app.config['TESTING'] = True
    return mod


def csrf_of(html):
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


class Client:
    def __init__(self, mod):
        self.c = mod.app.test_client()
        self.token = csrf_of(self.c.get('/').get_data(as_text=True))

    def login(self, user, pwd):
        r = self.c.post('/auth/login', data={'username': user, 'password': pwd, 'csrf_token': self.token})
        self.refresh()
        return r

    def refresh(self):
        r = self.c.get('/', follow_redirects=True)
        html = r.get_data(as_text=True)
        if 'csrf-token' in html:
            self.token = csrf_of(html)

    def get(self, *a, **k):
        return self.c.get(*a, **k)

    def post(self, url, data=None, json=None):
        if json is not None:
            return self.c.post(url, json=json, headers={'X-CSRF-Token': self.token})
        d = dict(data or {}); d['csrf_token'] = self.token
        return self.c.post(url, data=d)


@pytest.fixture()
def client(appmod):
    return Client(appmod)
