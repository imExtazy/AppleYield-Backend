from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MonthsViewSet,
    MonthsCalculationCartView,
    MonthsCalculationViewSet,
    MonthsCalculationSubmitView,
    MonthsCalculationFinishView,
    MonthsCalculationRejectView,
    MonthIndicatorsUpdateView,
    MonthIndicatorsDeleteView,
    login_view,
    logout_view,
    MeView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"months", MonthsViewSet, basename="months")
router.register(r"months_calculation", MonthsCalculationViewSet, basename="months_calculation")
router.register(r"user", UserViewSet, basename="user")

urlpatterns = [
    # сначала специфичные пути, чтобы не перехватывались роутером как pk
    path("months_calculation/cart/", MonthsCalculationCartView.as_view(), name="months_calculation_cart"),
    path("months_calculation/<int:id>/submit/", MonthsCalculationSubmitView.as_view(), name="months_calculation_submit"),
    path("months_calculation/<int:id>/finish/", MonthsCalculationFinishView.as_view(), name="months_calculation_finish"),
    path("months_calculation/<int:id>/reject/", MonthsCalculationRejectView.as_view(), name="months_calculation_reject"),
    path("months_calculation/<int:order_id>/month_indicators/<int:service_id>/", MonthIndicatorsUpdateView.as_view(), name="month_indicators_update"),
    path("months_calculation/<int:order_id>/month_indicators/<int:service_id>/delete/", MonthIndicatorsDeleteView.as_view(), name="month_indicators_delete"),
    # пользователи
    path("login", login_view, name="auth_login"),
    path("logout", logout_view, name="auth_logout"),
    path("users/me/", MeView.as_view(), name="users_me"),
    # в конце — роутер
    path("", include(router.urls)),
]


