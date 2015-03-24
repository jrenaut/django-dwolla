# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .settings import set_dwolla_env
set_dwolla_env()

from django.conf import settings
from dwolla import constants

if settings.DWOLLA_SANDBOX:
    KEY = 'sandbox'
    DWOLLA_ADMIN_ACCOUNT = settings.DWOLLA_ACCOUNTS[KEY]
    DWOLLA_ADMIN_ID = settings.DWOLLA_ACCOUNTS['sandbox']['user_id']
else:
    KEY = 'production'
    DWOLLA_ADMIN_ACCOUNT = settings.DWOLLA_ACCOUNTS['admin']
    DWOLLA_ADMIN_ID = DWOLLA_ADMIN_ACCOUNT['user_id']

constants.client_id = settings.DWOLLA_ACCOUNTS[KEY]['key']
constants.client_secret = settings.DWOLLA_ACCOUNTS[KEY]['secret']
constants.sandbox = settings.DWOLLA_SANDBOX

    
DWOLLA_ACCOUNT = settings.DWOLLA_ACCOUNTS[KEY]


def set_constants(admin=False):
    if admin is False:
        constants.client_id = settings.DWOLLA_ACCOUNTS[KEY]['key']
        constants.client_secret = settings.DWOLLA_ACCOUNTS[KEY]['secret']
    else:
        constants.client_id = DWOLLA_ADMIN_ACCOUNT['key']
        constants.client_secret = DWOLLA_ADMIN_ACCOUNT['secret']
    return constants
