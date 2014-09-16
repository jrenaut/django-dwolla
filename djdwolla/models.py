# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .auth import DWOLLA_ACCOUNT, DWOLLA_APP, DWOLLA_GATE
from .managers import CustomerManager
from .tasks import send_funds
from model_utils.models import TimeStampedModel
from delorean import Delorean
from jsonfield.fields import JSONField

from django.conf import settings
from django.utils.encoding import python_2_unicode_compatible
from django.utils import timezone
from django.db import models
from django_extensions.db.fields.encrypted import EncryptedCharField


def dwolla_charge(sub):
    # Clear out any previous session
    DWOLLA_GATE.start_gateway_session()

    # Add a product to the purchase order
    # DWOLLA_GATE.add_gateway_product(str(sub.customer), float(sub.amount))
    DWOLLA_GATE.add_gateway_product('Devote.io subscription', 21.00)

    # Generate a checkout URL; pass in the recipient's Dwolla ID
    # url = DWOLLA_GATE.get_gateway_URL(str(sub.customer))
    url = DWOLLA_GATE.get_gateway_URL(DWOLLA_ACCOUNT['user_id'])
    return url


def create_oauth_request_url():
    """ Send users to this url to authorize us """
    redirect_uri = "https://www.back2ursite.com/return"
    scope = "send|balance|funding|transactions|accountinfofull"
    authUrl = DWOLLA_APP.init_oauth_url(redirect_uri, scope)
    return authUrl


class DwollaObject(TimeStampedModel):

    dwolla_id = models.CharField(max_length=50, unique=True)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class Event(DwollaObject):

    """
    kinds: Transaction.Status, Transaction.Returned,
           Request.Fulfilled, Request.Cancelled
    
    """
    kind = models.CharField(max_length=250)
    livemode = models.BooleanField(default=False)
    customer = models.ForeignKey("Customer", null=True)
    webhook_message = JSONField()
    validated_message = JSONField(null=True)
    valid = models.NullBooleanField(null=True)
    processed = models.BooleanField(default=False)

    @property
    def message(self):
        return self.validated_message

    def __str__(self):
        return "%s - %s" % (self.kind, self.stripe_id)

    def link_customer(self):
        cus_id = None
        customer_crud_events = [
            "customer.created",
            "customer.updated",
            "customer.deleted"
        ]
        if self.kind in customer_crud_events:
            cus_id = self.message["data"]["object"]["id"]
        else:
            cus_id = self.message["data"]["object"].get("customer", None)

        if cus_id is not None:
            try:
                self.customer = Customer.objects.get(stripe_id=cus_id)
                self.save()
            except Customer.DoesNotExist:
                pass

    def validate(self):
        evt = stripe.Event.retrieve(self.stripe_id)
        self.validated_message = json.loads(
            json.dumps(
                evt.to_dict(),
                sort_keys=True,
                cls=stripe.StripeObjectEncoder
            )
        )
        if self.webhook_message["data"] == self.validated_message["data"]:
            self.valid = True
        else:
            self.valid = False
        self.save()

    def process(self):
        """
            "account.updated",
            "account.application.deauthorized",
            "charge.succeeded",
            "charge.failed",
            "charge.refunded",
            "charge.dispute.created",
            "charge.dispute.updated",
            "chagne.dispute.closed",
            "customer.created",
            "customer.updated",
            "customer.deleted",
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.subscription.trial_will_end",
            "customer.discount.created",
            "customer.discount.updated",
            "customer.discount.deleted",
            "invoice.created",
            "invoice.updated",
            "invoice.payment_succeeded",
            "invoice.payment_failed",
            "invoiceitem.created",
            "invoiceitem.updated",
            "invoiceitem.deleted",
            "plan.created",
            "plan.updated",
            "plan.deleted",
            "coupon.created",
            "coupon.updated",
            "coupon.deleted",
            "transfer.created",
            "transfer.updated",
            "transfer.failed",
            "ping"
        """
        if self.valid and not self.processed:
            try:
                if not self.kind.startswith("plan.") and \
                        not self.kind.startswith("transfer."):
                    self.link_customer()
                if self.kind.startswith("invoice."):
                    Invoice.handle_event(self)
                elif self.kind.startswith("charge."):
                    if not self.customer:
                        self.link_customer()
                    self.customer.record_charge(
                        self.message["data"]["object"]["id"]
                    )
                elif self.kind.startswith("transfer."):
                    Transfer.process_transfer(
                        self,
                        self.message["data"]["object"]
                    )
                elif self.kind.startswith("customer.subscription."):
                    if not self.customer:
                        self.link_customer()
                    if self.customer:
                        self.customer.sync_current_subscription()
                elif self.kind == "customer.deleted":
                    if not self.customer:
                        self.link_customer()
                    self.customer.purge()
                self.send_signal()
                self.processed = True
                self.save()
            except stripe.StripeError as e:
                EventProcessingException.log(
                    data=e.http_body,
                    exception=e,
                    event=self
                )
                webhook_processing_error.send(
                    sender=Event,
                    data=e.http_body,
                    exception=e
                )

    def send_signal(self):
        signal = WEBHOOK_SIGNALS.get(self.kind)
        if signal:
            return signal.send(sender=Event, event=self)


@python_2_unicode_compatible
class Customer(DwollaObject):

    user = models.OneToOneField(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
                                null=True, related_name='dwolla_customer')
    token = models.CharField(max_length=100, null=True, blank=True)
    pin = EncryptedCharField(max_length=100, null=True, blank=True)
    card_fingerprint = models.CharField(max_length=200, blank=True)
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    date_purged = models.DateTimeField(null=True, editable=False)

    objects = CustomerManager()

    def __str__(self):
        return unicode(self.user)

    @classmethod
    def get_or_create(cls, user):
        try:
            return Customer.objects.get(user=user), False
        except Customer.DoesNotExist:
            return cls.create(user), True

    @classmethod
    def create(cls, user):
        cus = Customer.objects.create(user=user)
        return cus

    def refresh_token(self):
        resp = DWOLLA_APP.refresh_auth(self.token)
        self.token = resp['refresh_token']
        self.save(update_fields=['token'])
        return True

    # def send_funds(self, amount, notes, pin=None, funds_source=None):
    #     pin = pin or self.pin
    #     dwolla_user = DwollaUser(self.token)
    #     dwolla_user.send_funds(token, amount, DWOLLA_ACCOUNT['user_id'],
    #                            pin, notes=notes, funds_source=funds_source)
    #     return True


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

    def charge_subscription(self):
        if DWOLLA_ACCOUNT['refresh_token']:
            self.customer.refresh_token()
        cus = self.customer
        send_funds.delay(cus.token, DWOLLA_ACCOUNT['user_id'],
                         self.amount, cus.pin,
                         "Devote.IO monthly subscription")

    @classmethod
    def get_or_create(cls, customer, amount=None):
        try:
            return CurrentSubscription.objects.get(customer=customer), False
        except CurrentSubscription.DoesNotExist:
            return cls.create(customer, amount), True

    @classmethod
    def create(cls, customer):
        end = Delorean().next_month().truncate("month").datetime
        current_sub = CurrentSubscription.objects.create(customer=customer, quantity=1,
                                                         start=timezone.now(), status="active",
                                                         current_period_end=end, amount=0,
                                                         current_period_start=timezone.now())
        return current_sub

    def update(self, amount):
        self.amount = amount
        self.save(update_fields=['amount'])

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

