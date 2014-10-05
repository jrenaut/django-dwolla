# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.views.generic.base import TemplateView
from django.views import generic
from django.http import HttpResponse
from django.contrib.sites.models import Site
from braces.views import CsrfExemptMixin
from dwolla import DwollaUser
from .auth import DWOLLA_APP, DWOLLA_ACCOUNT

from .mixins import LoginRequiredMixin
from .forms import PinForm
from .models import Customer, TransactionStatus  # , RequestFulfilled, EventProcessingException
from .settings import PY3
from djstripe.models import Event, EventProcessingException
import urllib
from django.contrib import messages


class MyTemplateView(TemplateView):

    template_name = "generic.html"
    message = None

    def get_context_data(self, **kwargs):
        data = super(MyTemplateView, self).get_context_data(**kwargs)
        data['message'] = self.message
        return data


class PinConfirmedView(MyTemplateView):

    message = "PIN Confirmed"


class OAuthRedirectView(MyTemplateView):

    message = "Redirecting for Dwolla OAuth"


class OAuthView(LoginRequiredMixin, generic.TemplateView):

    template_name = "oauth_modal.html"

    def get_context_data(self, **kwargs):
        data = super(OAuthView, self).get_context_data(**kwargs)
        redirect_uri = DWOLLA_ACCOUNT['oauth_uri']
        self.request.session['dwolla_oauth_next'] = self.request.GET['next']
        print self.request.session.items()
        scope = "send|balance|funding|transactions|accountinfofull"
        auth_url = DWOLLA_APP.init_oauth_url(redirect_uri, scope)
        data['auth_url'] = auth_url
        data['site_name'] = Site.objects.get().name
        return data


class OAuthConfirmationView(LoginRequiredMixin, generic.UpdateView):

    model = Customer
    template_name = "pin_form.html"
    form_class = PinForm
    # success_url = "/dwolla/pin_confirmed/"

    def get_object(self):
        if hasattr(self.request.user, "dwolla_customer"):
            customer = self.request.user.dwolla_customer
        else:
            customer = Customer.create(self.request.user)
        return customer

    def get_token(self):
        code = self.request.GET['code']
        dwolla_resp = DWOLLA_APP.get_oauth_token(code)
        return dwolla_resp

    def form_valid(self, form):
        messages.info(self.request,
                      "Your pin is confirmed, and your Dwolla account is now authorized.")
        return super(OAuthConfirmationView, self).form_valid(form)

    def get_initial(self):
        if self.request.method == "GET":
            tokens = self.get_token()
            access_token = tokens['access_token']
            refresh_token = tokens['refresh_token']
            dwolla_id = DwollaUser(access_token).get_account_info()['Id']
            return {"pin": "", "token": access_token, "refresh_token": refresh_token, "dwolla_id": dwolla_id}
        else:
            return super(OAuthConfirmationView, self).get_initial()

    def get_success_url(self):
        return self.request.session['dwolla_oauth_next']


class WebhookView(CsrfExemptMixin, generic.View):

    def record_transaction(self, data):
        # value = data["Value"]
        source_id = data["Transaction"]["Source"]["Id"]
        destination_id = data["Transaction"]["Destination"]["Id"]
        kind = "dwolla.%s.%s" % (data["Type"], data["Subtype"])
        data_dict = {
            "kind": kind,
            "webhook_message": data["Transaction"],
            "stripe_id": data["Id"],
        }
        try:
            c = Customer.objects.get(dwolla_id=source_id)
            user = c.user
        except Customer.DoesNotExist:
            c = Customer.objects.get(dwolla_id=destination_id)
            user = c.user
        except Customer.DoesNotExist:
            c = user = None
        data_dict.update({"dwolla_customer": c, "user": user})

        if Event.objects.filter(stripe_id=data['Id']).exists():
            EventProcessingException.objects.create(
                data=data,
                message="Duplicate event record",
                traceback=""
            )
        else:
            event = Event.objects.create(**data_dict)
            # See djstripe Event model for next couple methods
            # event.validate()
            # event.process()

        # t, created = TransactionStatus.objects.get_or_create(
        #     dwolla_id=data_dict['dwolla_id'],
        #     defaults=data_dict
        # )
        # if not created:
        #     t.value = data_dict['value']
        #     t.save(update_fields=['value'])

    def post(self, request, *args, **kwargs):
        if PY3:
            # Handles Python 3 conversion of bytes to str
            body = request.body.decode(encoding="UTF-8")
        else:
            # Handles Python 2
            body = request.body
        data = json.loads(body)
        if data['Type'] == "Transaction":
            self.record_transaction(data)
        # if RequestFulfilled.objects.filter(dwolla_id=data["Id"]).exists():
        #     EventProcessingException.objects.create(
        #         data=data,
        #         message="Duplicate event record",
        #         traceback=""
        #     )
        # else:
        #     RequestFulfilled.objects.create(
        #         dwolla_id=data["Id"],
        #         source_id=data["Source"],
        #         destination_id=data["Destination"],
        #         transaction=data["Transaction"],
        #         amount=data['Amount']
        #     )
        return HttpResponse()

