from django import forms

class QueryForm(forms.Form):
    CHOICES = [
        ('polski', 'Język polski'),
        ('lekcji', 'Plan lekcji'),
    ]
    choice_field = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect, label="Wybieżcie plik")
    query = forms.CharField(label='Wprowadźcie prośbę do modelej AI', max_length=100)