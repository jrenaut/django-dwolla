# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from .models import CurrentSubscription


def monthly_subscription_charges():
    active_subs = CurrentSubscription.objects.exclude(status='canceled')
    for sub in active_subs:
        sub.charge_subscription.delay()

