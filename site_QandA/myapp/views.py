import json

from django.shortcuts import render
import requests
from django.http import JsonResponse
import markdown


# Create your views here.
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .forms import QueryForm, ImproveForm

@csrf_exempt
def page_for_ask(request):
    form = QueryForm()
    form_improve = ImproveForm()
    result = None
    return render(request, 'myapp/page_for_ask.html', {
        'form': form,
        'form_improve': form_improve,
        'result': result,
    })

@csrf_exempt
def handle_query(request):
    result = None
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Обработка данных из формы
        data = json.loads(request.body)
        query = data.get('query')
        selected_option = data.get('choice_field')
        quotation_text = data.get('quotation_text')

        print(request.POST)
        print(query)
        print(selected_option)
        print(True if quotation_text else False)

        # Запрос к внешнему API
        response = requests.post('http://127.0.0.1:5000/api/model/ask', json={'question': query, 'file': selected_option})

        if response.status_code == 200:
            data = response.json()
            result = markdown.markdown(data.get('answer', ''))
        else:
            result = 'failed'

        # Возвращаем результат в формате JSON
        return JsonResponse({'success': True, 'result': result})

    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@csrf_exempt  # Если вы используете POST-запросы, этот декоратор может понадобиться
def process_selected_text(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        selected_text = data.get('selected_text')

        # Здесь можно сделать что-то с выделенным текстом
        print("Выделенный текст:", selected_text)

        return JsonResponse({"status": "success"})