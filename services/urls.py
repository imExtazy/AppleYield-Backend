from django.urls import path
from .views import list_view, detail_view, application_view, add_to_application_view, delete_application_view

urlpatterns = [
    path('', list_view, name='services_list'),
    path('service/<int:id>/', detail_view, name='service_detail'),
    path('application/<int:id>/', application_view, name='application_detail'),
    path('service/<int:id>/add/', add_to_application_view, name='service_add'),
    path('application/<int:id>/delete/', delete_application_view, name='application_delete'),
]


