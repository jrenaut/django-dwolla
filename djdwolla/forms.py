from django import forms
from .models import Customer

from .auth import DWOLLA_ACCOUNT
from .tasks import send_funds
from dwolla import DwollaAPIError, DwollaUser


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
        choices = kwargs.pop("choices", ())
        super(PinForm, self).__init__(*args, **kwargs)
        self.fields['funds_source'].widget = forms.Select(choices=choices, attrs={"class": "form-control"})

    def clean_pin_auth(self):
        data = self.cleaned_data['pin_auth']
        if data is not True:
            raise forms.ValidationError("You must accept the PIN agreement.")
        return data

    def clean(self):
        cleaned_data = super(PinForm, self).clean()
        data = cleaned_data['pin']
        token = cleaned_data['token']
        if not data.isdigit():
            self.add_error('pin', "The PIN must only contain numbers")
        else:
            funds_source = "Devote.IO bogus funds source request to verify user pin"
            notes = "Verifying PIN via invalid funds source"
            try:
                send_funds(token, DWOLLA_ACCOUNT['user_id'],
                           0.01, data, notes, funds_source=funds_source)
            except DwollaAPIError as e:
                """ If error is invalid funding, then the PIN verified
                This is a hack because Dwolla doesn't have
                an API call to verify a PIN
                """
                if e.message == 'Invalid account PIN':
                    self.add_error('pin', e.message)
                elif "Invalid funding source provided" in e.message:
                    pass
                else:
                    raise
