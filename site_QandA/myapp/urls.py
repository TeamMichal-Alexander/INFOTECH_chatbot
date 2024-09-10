from django.urls import path
from . import views

urlpatterns = [
    path('', views.query_view, name='page_for_ask'),
]