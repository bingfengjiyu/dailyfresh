from django.conf.urls import url
from apps.user.views import RegisterView,LoginView,ActiveView,LogoutView,UserInfoView,UserOrderView,AddressView
from django.contrib.auth.decorators import login_required



urlpatterns = [
    # url(r'^register$', views.register, name='register'), # 注册
    # url(r'^register_handle$', views.register_handle, name='register_handle'), # 注册处理

    url(r'^register$', RegisterView.as_view(), name='register'), # 注册
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'), # 用户激活
    url(r'^login$', LoginView.as_view(), name='login'), # 登录

    url(r'^logout$',LogoutView.as_view(),name="logout"),
    url(r'^$',UserInfoView.as_view(),name="user"),
    url(r'^order$',UserOrderView.as_view(),name="order"),
    url(r'^address$',AddressView.as_view(),name="address"),


]
