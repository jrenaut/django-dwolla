# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .settings import set_dwolla_env
set_dwolla_env()

from django.conf import settings
from dwolla import DwollaUser, DwollaClientApp, DwollaGateway

KEY = 'sandbox' if settings.DWOLLA_SANDBOX else 'production'
DWOLLA_ACCOUNT = settings.DWOLLA_ACCOUNTS[KEY]

DWOLLA_APP = DwollaClientApp(DWOLLA_ACCOUNT['key'], DWOLLA_ACCOUNT['secret'])
DWOLLA_USER = DwollaUser(DWOLLA_ACCOUNT['token'])
DWOLLA_GATE = DwollaGateway(DWOLLA_ACCOUNT['key'], DWOLLA_ACCOUNT['secret'])
