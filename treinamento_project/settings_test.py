# settings_test.py
from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # banco em memória, rápido para testes
    }
}