from django import forms

class QueryForm(forms.Form):
    CHOICES = [
        ('pdfs', 'Pliki pdf'),
        ('lekcji', 'Plan lekcji'),
    ]
    choice_field = forms.ChoiceField(choices=CHOICES, label="Wybieżcie plik")
    query = forms.CharField(label='Wprowadźcie prośbę do modelej AI', max_length=300)

class ImproveForm(forms.Form):
    text_field = forms.CharField(max_length=300, widget=forms.TextInput(attrs={'id': 'improve_textfield', 'placeholder': 'Wprowadź prompt'}))