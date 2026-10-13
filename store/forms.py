from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(5, "5"), (4, "4"), (3, "3"), (2, "2"), (1, "1")], coerce=int, widget=forms.RadioSelect, label="Your rating"
    )

    class Meta:
        model = Review
        fields = ["rating", "title", "comment", "photo"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 4})}
        labels = {"photo": "Add a photo (optional)"}

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "size") and photo.size > 4 * 1024 * 1024:
            raise forms.ValidationError("Photo must be under 4 MB.")
        return photo
