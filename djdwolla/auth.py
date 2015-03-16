# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .settings import set_dwolla_env
set_dwolla_env()

from django.conf import settings
from dwolla import constants

if settings.DWOLLA_SANDBOX:
    KEY = 'sandbox'
    constants.client_id = settings.DWOLLA_ACCOUNTS[KEY]['key']
    constants.client_secret = settings.DWOLLA_ACCOUNTS[KEY]['secret']
    admin_constants = constants
    DWOLLA_ADMIN_ID = settings.DWOLLA_ACCOUNTS['sandbox']['user_id']
    DWOLLA_ADMIN_APP = None
else:
    KEY = 'production'
    constants.client_id = settings.DWOLLA_ACCOUNTS[KEY]['key']
    constants.client_secret = settings.DWOLLA_ACCOUNTS[KEY]['secret']
    admin_constants = constants
    DWOLLA_ADMIN_ACCOUNT = settings.DWOLLA_ACCOUNTS['admin']
    DWOLLA_ADMIN_ID = DWOLLA_ADMIN_ACCOUNT['user_id']
    admin_constants.client_id = DWOLLA_ADMIN_ACCOUNT['key']
    admin_constants.client_secret = DWOLLA_ADMIN_ACCOUNT['secret']

constants.sandbox = settings.DWOLLA_SANDBOX

    
DWOLLA_ACCOUNT = settings.DWOLLA_ACCOUNTS[KEY]
# DWOLLA_APP = DwollaClientApp(DWOLLA_ACCOUNT['key'], DWOLLA_ACCOUNT['secret'])
# if DWOLLA_ADMIN_APP is None:
#     DWOLLA_ADMIN_APP = DWOLLA_APP
# DWOLLA_GATE = DwollaGateway(DWOLLA_ACCOUNT['key'], DWOLLA_ACCOUNT['secret'])
