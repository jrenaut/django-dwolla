from __future__ import absolute_import

from celery import shared_task
from dwolla import DwollaUser


@shared_task
def send_funds(token, dwolla_account, amount, pin, notes=None, funds_source=None):
    dwolla_user = DwollaUser(token)
    dwolla_user.send_funds(amount, dwolla_account, pin, notes=notes, funds_source=funds_source)
    return True


@shared_task(name="foo")
def add(x, y):
    return x + y
