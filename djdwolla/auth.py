# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .settings import set_dwolla_env
set_dwolla_env()

from django.conf import settings
from dwolla import DwollaClientApp, DwollaGateway


if settings.DWOLLA_SANDBOX:
    KEY = 'sandbox'
    DWOLLA_ADMIN_ID = settings.DWOLLA_ACCOUNTS[KEY]['user_id']
    DWOLLA_ADMIN_APP = None
else:
    KEY = 'production'
    DWOLLA_ADMIN_ACCOUNT = settings.DWOLLA_ACCOUNTS['admin']
    DWOLLA_ADMIN_ID = DWOLLA_ADMIN_ACCOUNT['user_id']
    DWOLLA_ADMIN_APP = DwollaClientApp(DWOLLA_ADMIN_ACCOUNT['key'],
                                       DWOLLA_ADMIN_ACCOUNT['secret'])
    
DWOLLA_ACCOUNT = settings.DWOLLA_ACCOUNTS[KEY]

DWOLLA_APP = DwollaClientApp(DWOLLA_ACCOUNT['key'], DWOLLA_ACCOUNT['secret'])
DWOLLA_GATE = DwollaGateway(DWOLLA_ACCOUNT['key'], DWOLLA_ACCOUNT['secret'])
