from __future__ import absolute_import

from celery import shared_task
from djdwolla.auth import constants
from dwolla import transactions


@shared_task
def send_funds(token, dwolla_account, amount, pin, notes=None, funds_source=None, metadata={}):
    tid = transactions.send(dwolla_account, amount, alternate_pin=pin,
                            alternate_token=token,
                            params={"notes": notes, "fundsSource": funds_source,
                                    "metadata": metadata})
    return tid
