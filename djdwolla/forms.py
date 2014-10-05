from django import forms
from .models import Customer

from .auth import DWOLLA_ACCOUNT
from .tasks import send_funds
from dwolla import DwollaAPIError


class PinForm(forms.ModelForm):

    pin_auth = forms.BooleanField()

    class Meta:
        model = Customer
        fields = ['pin', 'dwolla_id', 'token', 'refresh_token']
        widgets = {
            "pin": forms.PasswordInput(attrs={"class": "form-control"}),
            "dwolla_id": forms.HiddenInput(),
            "token": forms.HiddenInput(),
            "refresh_token": forms.HiddenInput(),
        }

    def clean_pin_auth(self):
        data = self.cleaned_data['pin_auth']
        if data is not True:
            raise forms.ValidationError("You must accept the PIN agreement.")

    def clean(self):
        cleaned_data = super(PinForm, self).clean()
        data = cleaned_data['pin']
        token = cleaned_data['token']
        if not data.isdigit():
            raise forms.ValidationError("The PIN must only contain numbers")
        funds_source = "Devote.IO bogus funds source request to verify user pin"
        notes = "Verifying PIN via invalid funds source"
        try:
            send_funds(token, DWOLLA_ACCOUNT['user_id'],
                       0.01, data, notes, funds_source=funds_source)

            # self.instance.send_funds(0.01, "Verifying PIN with via invalid funds source", pin=data, funds_source="Devote.IO bogus funds source request to verify user pin")
        # dwolla_user = DwollaUser(self.instance.token)
        # try:
        #     dwolla_user.send_funds(0.01, DWOLLA_ACCOUNT['user_id'], data, notes="Verifying PIN with via invalid funds source", funds_source="Devote.IO bogus funds source request to verify user pin")
        except DwollaAPIError as e:
            if e.message == 'Invalid account PIN':
                raise forms.ValidationError(e.message)
            # If error is invalid funding, then the PIN verified
            # This is a hack because Dwolla doesn't have 
            # an API call to verify PIN's
            elif "Invalid funding source provided" in e.message:
                pass
            else:
                raise
        # return data
