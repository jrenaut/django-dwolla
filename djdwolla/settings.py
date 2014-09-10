# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib
from django.utils.functional import SimpleLazyObject

from . import safe_settings

PY3 = sys.version > "3"


def get_user_model():
    """ Place this in a function to avoid circular imports """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
    except ImportError:
        from django.contrib.auth.models import User
    return User

User = SimpleLazyObject(get_user_model)

def load_path_attr(path):
    i = path.rfind(".")
    module, attr = path[:i], path[i + 1:]
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured("Error importing %s: '%s'" % (module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured("Module '%s' does not define a '%s'" % (
            module, attr)
        )
    return attr

DWOLLA_API_KEY = safe_settings.DWOLLA_API_KEY
