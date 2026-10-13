import re

from django import forms

from .constants import GSTIN_REGEX
from .models import Enquiry


class EnquiryForm(forms.ModelForm):
    # Honeypot: hidden from people, bots fill it in.
    website = forms.CharField(required=False, label="Leave this empty", widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = Enquiry
        fields = ["name", "company", "gstin", "phone", "email", "product_interest", "quantity", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, kind="contact", **kwargs):
        super().__init__(*args, **kwargs)
        self.kind = kind
        if kind == "contact":
            for f in ("company", "gstin", "product_interest", "quantity"):
                del self.fields[f]
        else:
            self.fields["company"].required = True
            self.fields["quantity"].required = True
            self.fields["quantity"].widget.attrs["min"] = 1
            self.fields["gstin"].label = "GSTIN (optional)"

    def clean_phone(self):
        phone = re.sub(r"[\s\-+]", "", self.cleaned_data["phone"])
        if not re.fullmatch(r"(91)?[6-9][0-9]{9}", phone):
            raise forms.ValidationError("Enter a valid 10-digit Indian mobile number.")
        return phone[-10:]

    def clean_gstin(self):
        g = self.cleaned_data.get("gstin", "").strip().upper()
        if g and not re.fullmatch(GSTIN_REGEX, g):
            raise forms.ValidationError("Enter a valid 15-character GSTIN.")
        return g

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.kind = self.kind
        if commit:
            obj.save()
        return obj
