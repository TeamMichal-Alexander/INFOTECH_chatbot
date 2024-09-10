from django import forms

class QueryForm(forms.Form):
    query = forms.CharField(label='Введите запрос', max_length=100)