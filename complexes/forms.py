from django import forms


class ComplexPhotoUploadForm(forms.Form):
    complex_name = forms.CharField(widget=forms.HiddenInput)
    main_index = forms.IntegerField(widget=forms.HiddenInput, min_value=0, required=False)
