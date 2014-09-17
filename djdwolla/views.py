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
from .models import Customer, RequestFulfilled, EventProcessingException
from .settings import PY3


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
        scope = "send|balance|funding|transactions|accountinfofull"
        auth_url = DWOLLA_APP.init_oauth_url(redirect_uri, scope)
        data['auth_url'] = auth_url
        data['site_name'] = Site.objects.get().name
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

    def get(self, request, *args, **kwargs):
        response = super(OAuthConfirmationView, self).get(request, *args, **kwargs)
        code = self.request.GET['code']
        dwolla_resp = DWOLLA_APP.get_oauth_token(code)
        if type(dwolla_resp) is unicode:  # old dwolla api
            token = dwolla_resp
        else:  # new dwolla api as of Oct 2014
            token = json.loads(dwolla_resp)['refresh_token']
        self.object.token = token
        self.object.dwolla_id = DwollaUser(token).get_account_info()['Id']
        self.object.save(update_fields=['token', 'dwolla_id'])
        return response

    def get_initial(self):
        return {"pin": ""}


class PaymentPostedView(CsrfExemptMixin, generic.View):

    def post(self, request, *args, **kwargs):
        if PY3:
            # Handles Python 3 conversion of bytes to str
            body = request.body.decode(encoding="UTF-8")
        else:
            # Handles Python 2
            body = request.body
        data = json.loads(body)
        if RequestFulfilled.objects.filter(dwolla_id=data["Id"]).exists():
            EventProcessingException.objects.create(
                data=data,
                message="Duplicate event record",
                traceback=""
            )
        else:
            RequestFulfilled.objects.create(
                dwolla_id=data["Id"],
                source_id=data["Source"],
                destination_id=data["Destination"],
                transaction=data["Transaction"],
                amount=data['Amount']
            )
        return HttpResponse()
