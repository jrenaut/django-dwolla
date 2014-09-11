# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings

DWOLLA_SANDBOX = getattr(settings, "DWOLLA_SANDBOX", False)

KEY = 'sandbox' if DWOLLA_SANDBOX else 'production'

DWOLLA_API_KEY = settings.DWOLLA_ACCOUNTS[KEY]['key']
