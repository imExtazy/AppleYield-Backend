from django.urls import path
from .views import months_list_view, month_detail_view, months_calculation_view

urlpatterns = [
    path('', months_list_view, name='months_list'),
    path('month/<int:id>/', month_detail_view, name='month_detail'),
    path('months_calculation/<int:id>/', months_calculation_view, name='calculation_detail'),
]


