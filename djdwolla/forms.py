from django import forms
from django.contrib import messages
from .models import Customer

from .auth import DWOLLA_ACCOUNT
from .tasks import send_funds
from dwolla import constants, fundingsources


class PinForm(forms.ModelForm):

    pin_auth = forms.BooleanField()

    class Meta:
        model = Customer
        fields = ['pin', 'dwolla_id', 'token', 'refresh_token', 'funds_source']
        widgets = {
            "pin": forms.PasswordInput(attrs={"class": "form-control"}),
            "dwolla_id": forms.HiddenInput(),
            "token": forms.HiddenInput(),
            "refresh_token": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.funds_choices = kwargs.pop("choices", ())
        self.request = kwargs.pop("request")
        super(PinForm, self).__init__(*args, **kwargs)
        self.fields['funds_source'].widget = forms.Select(choices=self.funds_choices,
                                                          attrs={"class": "form-control"})

    def clean_pin_auth(self):
        data = self.cleaned_data['pin_auth']
        if data is not True:
            raise forms.ValidationError("You must accept the PIN agreement.")
        return data

    def clean(self):
        warning_message = ('You have chosen your Dwolla balance for you funding '
                           'source and the balance is less than $1.00.  Be sure '
                           'to fund the account balance immediately so we can '
                           'process payment for your subscriptions on the first '
                           'of next month.')
        cleaned_data = super(PinForm, self).clean()
        data = cleaned_data['pin']
        token = cleaned_data['token']
        funds_source = cleaned_data['funds_source']
        if not data.isdigit():
            self.add_error('pin', "The PIN must only contain numbers")
        else:
            bogus_funds_source = "Devote.IO bogus funds source request to verify user pin"
            notes = "Verifying PIN via invalid funds source"
            try:
                send_funds(token, DWOLLA_ACCOUNT['user_id'],
                           0.01, data, notes, funds_source=bogus_funds_source)
            except Exception as e:
                """ If error is invalid funding, then the PIN verified
                This is a hack because Dwolla doesn't have
                an API call to verify a PIN
                """
                if e.message == 'Invalid account PIN':
                    self.add_error('pin', e.message)
                elif "Invalid funding source provided" in e.message:
                    if funds_source == "Balance" and \
                       fundingsources.get("Balance", alternate_token=token)["Balance"] < 1:
                        messages.warning(self.request, warning_message, extra_tags='sticky')
                else:
                    raise
