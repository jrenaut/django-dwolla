# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.generic.base import TemplateView
from django.views import generic
from .mixins import LoginRequiredMixin
from .forms import PinForm
from .models import Customer


class MyTemplateView(TemplateView):

    template_name = "generic.html"
    message = None

    def get_context_data(self, **kwargs):
        data = super(MyTemplateView, self).get_context_data(**kwargs)
        data['message'] = self.message
        return data


class PinConfirmedView(MyTemplateView):

    message = "PIN Confirmed"


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
        # redirect_uri = ""
        # dwolla_resp = DWOLLA_APP.get_oauth_token(code) #, redirect_uri=redirect_uri)
        # if type(dwolla_resp) is str: # old dwolla api
        #     token = dwolla_resp
        # else: # new dwolla api as of Oct 2014
        #     token = dwolla_resp['refresh_token']
        # self.object.token = token
        # self.object.save(update_fields=['token'])
        return response

    def get_initial(self):
        return {"pin": ""}
