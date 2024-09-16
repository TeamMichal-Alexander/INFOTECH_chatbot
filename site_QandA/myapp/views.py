from django.shortcuts import render
import requests
from django.http import JsonResponse

# Create your views here.
from django.shortcuts import render
from .forms import QueryForm

def query_view(request):
    result = None
    if request.method == 'POST':
        form = QueryForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            selected_option = form.cleaned_data['choice_field']
            response = requests.post('http://127.0.0.1:5000/api/model/ask', json={'question': query, 'file': selected_option})
            if response.status_code == 200:
                data = response.json()
                result = data.get('answer')
            else:
                result = 'failed'

    else:
        form = QueryForm()

    return render(request, 'myapp/page_for_ask.html', {'form': form, 'result': result})