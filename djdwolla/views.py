# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
from django.views.generic.base import TemplateView
from django.views import generic
from django.http import HttpResponse
from django.contrib.sites.models import Site
from braces.views import CsrfExemptMixin
from .auth import set_constants
from .auth import DWOLLA_ACCOUNT

from .mixins import LoginRequiredMixin
from .forms import PinForm
from .models import Customer
from .settings import PY3
from djstripe.models import Event, EventProcessingException
from django.contrib import messages
from delorean import Delorean
from datetime import timedelta


logger = logging.getLogger("devote.debug")


class MyTemplateView(TemplateView):

    template_name = "generic.html"
    message = None

    def get_context_data(self, **kwargs):
        data = super(MyTemplateView, self).get_context_data(**kwargs)
        data['message'] = self.message
        return data


class PinConfirmedView(LoginRequiredMixin, generic.TemplateView):

    template_name = "pin_confirmed.html"


class OAuthRedirectView(MyTemplateView):

    message = "Redirecting for Dwolla OAuth"


class OAuthView(LoginRequiredMixin, generic.TemplateView):

    template_name = "oauth_modal.html"

    def get_context_data(self, **kwargs):
        data = super(OAuthView, self).get_context_data(**kwargs)
        redirect_uri = DWOLLA_ACCOUNT['oauth_uri']
        self.request.session['dwolla_oauth_next'] = self.request.GET['next']
        # scope = "send|balance|funding|transactions|accountinfofull"
        scope = "send|accountinfofull|funding"
        constants = set_constants()
        from dwolla import oauth
        auth_url = oauth.genauthurl(redirect=redirect_uri, scope=scope)
        data['auth_url'] = auth_url
        data['site_name'] = Site.objects.get().name
        data['terms'] = self.request.GET.get("terms")
        return data


class OAuthConfirmationView(LoginRequiredMixin, generic.UpdateView):

    model = Customer
    template_name = "pin_form.html"
    form_class = PinForm
    success_url = "/dwolla/pin_confirmed/"

    def get_object(self):
        if hasattr(self.request.user, "dwolla_customer"):
            customer = self.request.user.dwolla_customer
        else:
            customer = Customer.create(self.request.user)
        return customer

    def get_token(self):
        code = self.request.GET['code']
        constants = set_constants()
        from dwolla import oauth
        dwolla_resp = oauth.get(code)
        return dwolla_resp

    def form_valid(self, form):
        messages.info(self.request,
                      "Your pin is confirmed, and your Dwolla account is now authorized.")
        del self.request.session['dwolla_funds_source_choices']
        form.instance.token_expiration = Delorean().datetime + timedelta(minutes=55)
        form.instance.refresh_token_expiration = Delorean().datetime + timedelta(days=30)
        return super(OAuthConfirmationView, self).form_valid(form)

    def get_form_kwargs(self):
        kwargs = super(OAuthConfirmationView, self).get_form_kwargs()
        choices = self.request.session['dwolla_funds_source_choices']
        kwargs.update({'choices': choices, 'request': self.request})
        return kwargs

    def get_initial(self):
        if self.request.method == "GET":
            tokens = self.get_token()
            access_token = tokens['access_token']
            refresh_token = tokens['refresh_token']
            constants = set_constants()
            from dwolla import accounts, fundingsources
            dwolla_id = accounts.full(alternate_token=access_token)['Id']
            funding_sources = fundingsources.get(alternate_token=access_token)
            choices = [(source['Id'], source['Name']) for source in funding_sources]
            # choices.extend([('', 'Dwolla Account Balance')])
            self.request.session['dwolla_funds_source_choices'] = choices
            return {"pin": "", "token": access_token,
                    "refresh_token": refresh_token, "dwolla_id": dwolla_id}
        else:
            return super(OAuthConfirmationView, self).get_initial()

    # def get_success_url(self):
    #     return self.request.session['dwolla_oauth_next']


class WebhookView(CsrfExemptMixin, generic.View):

    def record_transaction(self, data):
        subtype = data["Subtype"]
        kind = "dwolla.%s.%s" % (data["Type"], subtype)
        data_dict = {
            "kind": kind,
            "webhook_message": data,
            "valid": True
        }
        if subtype == "Status":
            stripe_id = data["Id"]
        elif subtype == "Returned":
            stripe_id = "%s_returned" % data["SenderTransactionId"]
        else:
            stripe_id = "dwolla_%f" % Delorean().epoch()
            logger.info("Dwolla webhook subtype unrecognized, check event \
            with stripe_id '%s'" % stripe_id)
        data_dict['stripe_id'] = stripe_id
        try:
            c = Customer.objects.get(pk=data['Metadata']['customer'])
            user = c.user
        except KeyError:
            c = user = None
        data_dict.update({"dwolla_customer": c, "user": user})

        existing_events = Event.objects.filter(stripe_id=stripe_id)
        if existing_events:
            EventProcessingException.objects.create(
                event=existing_events[0],
                data=data,
                message="Duplicate event record",
                traceback=""
            )
        else:
            Event.objects.create(**data_dict)
            # See djstripe Event model for next couple methods
            # event.validate()
            # event.process()

    def post(self, request, *args, **kwargs):
        constants = set_constants()
        from dwolla import webhooks
        signature = request.META['HTTP_X_DWOLLA_SIGNATURE']
        if PY3:
            # Handles Python 3 conversion of bytes to str
            body = request.body.decode(encoding="UTF-8")
        else:
            # Handles Python 2
            body = request.body

        if webhooks.verify(signature, body):
            data = json.loads(body)
            if data['Type'] == "Transaction":
                self.record_transaction(data)
        else:
            logger.warning("Dwolla signature mismatch")
        return HttpResponse()
