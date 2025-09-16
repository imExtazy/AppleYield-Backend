from django.urls import path
from .views import list_view, detail_view, application_view

urlpatterns = [
    path('', list_view, name='services_list'),
    path('service/<int:id>/', detail_view, name='service_detail'),
    path('application/<int:id>/', application_view, name='application_detail'),
]


