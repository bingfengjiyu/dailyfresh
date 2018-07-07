from django.conf.urls import url
from apps.cart.views import CartInfoView,CartAddView

urlpatterns = [
    url(r'^$',CartInfoView.as_view(),name="show"),
    url(r'^add$',CartAddView.as_view(),name="add"),
]
