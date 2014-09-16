# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns("",

    # HTML views
    # url(
    #     r"^$",
    #     views.AccountView.as_view(),
    #     name="account"
    # ),

    url(
        r"^oauth/$",
        views.OAuthConfirmationView.as_view(),
        name="ouath_conf"
    ),
    url(
        r"^pin_confirmed/$",
        views.PinConfirmedView.as_view(),
        name="pin_confirmed"
    ),

    url(
        r"^payment_posted/$",
        views.MyTemplateView.as_view(),
        name="payment_posted"
    ),

    url(
        r"^payment_callback/$",
        views.MyTemplateView.as_view(),
        name="payment_callback"
    ),

    # url(
    #     r"^a/check/available/(?P<attr_name>(username|email))/$",
    #     views.CheckAvailableUserAttributeView.as_view(),
    #     name="check_available_user_attr"
    # ),

    # # Webhook
    # url(
    #     app_settings.DJSTRIPE_WEBHOOK_URL,
    #     views.WebHook.as_view(),
    #     name="webhook"
    # ),

)