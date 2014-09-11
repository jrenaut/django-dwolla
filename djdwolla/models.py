# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .settings import set_dwolla_env
from .managers import CustomerManager
set_dwolla_env()

from model_utils.models import TimeStampedModel

from django.conf import settings
from django.utils.encoding import python_2_unicode_compatible
from django.utils import timezone
from django.db import models
from django_extensions.db.fields.encrypted import EncryptedCharField

from dwolla import DwollaUser, DwollaClientApp, DwollaAPIError, DwollaGateway

KEY = 'sandbox' if settings.DWOLLA_SANDBOX else 'production'
DWOLLA_ACCOUNT = settings.DWOLLA_ACCOUNTS[KEY]

dwolla_app = DwollaClientApp(DWOLLA_ACCOUNT['key'], DWOLLA_ACCOUNT['secret'])

dwolla_user = DwollaUser(DWOLLA_ACCOUNT['token'])

def dwolla_charge(sub):
    # Instantiate DwollaGateway with API creds and redirect URL
    # dwolla_gate = DwollaGateway(settings.DWOLLA_API_KEY, settings.DWOLLA_API_SECRET, 'http://localhost:5000/redirect')
    dwolla_gate = DwollaGateway(DWOLLA_ACCOUNT['key'], DWOLLA_ACCOUNT['secret'], 'http://google.com')

    # Clear out any previous session
    dwolla_gate.start_gateway_session()

    # Add a product to the purchase order
    # dwolla_gate.add_gateway_product(str(sub.customer), float(sub.amount))
    dwolla_gate.add_gateway_product('Devote.io subscription', 21.00)

    # Generate a checkout URL; pass in the recipient's Dwolla ID
    # url = dwolla_gate.get_gateway_URL(str(sub.customer))
    url = dwolla_gate.get_gateway_URL(DWOLLA_ACCOUNT['user_id'])

    print url

class DwollaObject(TimeStampedModel):

    class Meta:
        abstract = True

@python_2_unicode_compatible
class Customer(DwollaObject):

    user = models.OneToOneField(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), null=True, related_name='dwolla_customer')
    token = models.CharField(max_length=100, null=True, blank=True)
    pin = EncryptedCharField(max_length=100, null=True, blank=True)
    card_fingerprint = models.CharField(max_length=200, blank=True)
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    date_purged = models.DateTimeField(null=True, editable=False)

    objects = CustomerManager()

    def __str__(self):
        return unicode(self.user)


class CurrentSubscription(TimeStampedModel):

    STATUS_TRIALING = "trialing"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELLED = "canceled"
    STATUS_UNPAID = "unpaid"

    customer = models.OneToOneField(
        Customer,
        related_name="current_subscription",
        null=True
    )
    plan = models.CharField(max_length=100)
    quantity = models.IntegerField()
    start = models.DateTimeField()
    # trialing, active, past_due, canceled, or unpaid
    # In progress of moving it to choices field
    status = models.CharField(max_length=25)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True)
    current_period_start = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    trial_start = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7)

    def status_display(self):
        return self.status.replace("_", " ").title()

    def is_period_current(self):
        if self.current_period_end is None:
            return False
        return self.current_period_end > timezone.now()

    def is_status_current(self):
        return self.status in [self.STATUS_TRIALING, self.STATUS_ACTIVE]

    """
    Status when customer canceled their latest subscription, one that does not prorate,
    and therefore has a temporary active subscription until period end.
    """
    def is_status_temporarily_current(self):
        return self.canceled_at and self.start < self.canceled_at and self.cancel_at_period_end

    def is_valid(self):
        if not self.is_status_current():
            return False

        if self.cancel_at_period_end and not self.is_period_current():
            return False

        return True

    def create_charge(self):
        url = dwolla_charge(self)
        return url

    def get_plan(self):
        return Plan.objects.get(name=str(self.customer.user))


CURRENCIES = (
    ('usd', 'U.S. Dollars',),
    ('gbp', 'Pounds (GBP)',),
    ('eur', 'Euros',))

INTERVALS = (
    ('week', 'Week',),
    ('month', 'Month',),
    ('year', 'Year',))


@python_2_unicode_compatible
class Plan(DwollaObject):
    """A Dwolla Plan."""

    name = models.CharField(max_length=100, null=False)
    currency = models.CharField(
        choices=CURRENCIES,
        max_length=10,
        null=False)
    interval = models.CharField(
        max_length=10,
        choices=INTERVALS,
        verbose_name="Interval type",
        null=False)
    interval_count = models.IntegerField(
        verbose_name="Intervals between charges",
        default=1,
        null=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7,
                                 verbose_name="Amount (per period)",
                                 null=False)
    trial_period_days = models.IntegerField(null=True)

    def __str__(self):
        return self.name

    # @classmethod
    # def create(cls, metadata={}, **kwargs):
    #     """Create and then return a Plan (both in Stripe, and in our db)."""
    #     stripe.Plan.create(
    #         id=kwargs['stripe_id'],
    #         amount=int(kwargs['amount'] * 100),
    #         currency=kwargs['currency'],
    #         interval=kwargs['interval'],
    #         interval_count=kwargs.get('interval_count', None),
    #         name=kwargs['name'],
    #         trial_period_days=kwargs.get('trial_period_days'),
    #         metadata=metadata)

    #     plan = Plan.objects.create(
    #         stripe_id=kwargs['stripe_id'],
    #         amount=kwargs['amount'],
    #         currency=kwargs['currency'],
    #         interval=kwargs['interval'],
    #         interval_count=kwargs.get('interval_count', None),
    #         name=kwargs['name'],
    #         trial_period_days=kwargs.get('trial_period_days'),
    #     )

    #     return plan

    # @classmethod
    # def get_or_create(cls, **kwargs):
    #     try:
    #         return Plan.objects.get(stripe_id=kwargs['stripe_id']), False
    #     except Plan.DoesNotExist:
    #         return cls.create(**kwargs), True

    # def update_name(self):
    #     """Update the name of the Plan in Stripe and in the db.
    #     - Assumes the object being called has the name attribute already
    #       reset, but has not been saved.
    #     - Stripe does not allow for update of any other Plan attributes besides
    #       name.

    #     """

    #     p = stripe.Plan.retrieve(self.stripe_id)
    #     p.name = self.name
    #     p.save()

    #     self.save()

    # @property
    # def stripe_plan(self):
    #     """Return the plan data from Stripe."""
    #     return stripe.Plan.retrieve(self.stripe_id)
