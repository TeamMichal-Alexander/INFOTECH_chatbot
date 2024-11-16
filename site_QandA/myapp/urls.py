from django.urls import path
from . import views

urlpatterns = [
    path('', views.page_for_ask, name='page_for_ask'),
    path('query/', views.handle_query, name='handle_query'),
]