"""
نقطة التشغيل لـ PythonAnywhere / gunicorn / uWSGI.

PythonAnywhere: في تبويب Web افتح ملف WSGI configuration file وخلّي محتواه:

    import sys, os
    path = '/home/YOURUSER/kiro-print-os'
    if path not in sys.path:
        sys.path.insert(0, path)
    # os.environ['SECRET_KEY'] = '...'      # اختياري
    from wsgi import application

وفي Static files ضيف:  URL = /static/   →   Directory = /home/YOURUSER/kiro-print-os/static
(Flask بيخدم /static لوحده، لكن ده أسرع.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as application  # noqa: E402,F401
