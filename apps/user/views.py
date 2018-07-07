from django.contrib.auth import login,authenticate,logout
from django.views.generic import View
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import render,redirect
import re

from django_redis import get_redis_connection

from apps.goods.models import GoodsSKU
from util.mixin import LoginRequiredMixin
from django.conf import settings
from celery_tasks.tasks import send_register_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired

from apps.user.models import User,Address


class RegisterView(View):
    def get(self,request):
        return render(request, 'register.html')

    def post(self,request):
        username=request.POST.get("user_name")
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        if not all([username,password,email]):
            return render(request,'register.html', {'errmsg': '数据不完整'})

        if not re.match(r"^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$",email):
            return render(request,'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != "on":
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        try:
            user=User.objects.get(username=username)
        except:
            user=None

        if user:
            return render(request,"register.html",{"errmsg":"用户名已存在"})

        user=User.objects.create_user(username,email,password)
        user.is_active=0
        user.save()

        serializer=Serializer(settings.SECRET_KEY, 3600)
        info={'confirm':user.id}
        token=serializer.dumps(info)
        token=token.decode()

        send_register_active_email.delay(email,username,token)
        return redirect(reverse("goods:index"))


class ActiveView(View):
    def get(self,request,token):
        serializer=Serializer(settings.SECRET_KEY,3600)
        try:
            info=serializer.loads(token)
            user_id=info['confirm']
            user=User.objects.get(id=user_id)
            user.is_active=1
            user.save()
            return redirect(reverse("user:login"))
        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')


class LoginView(View):
    def get(self,request):
        if "username" in request.COOKIES:
            username=request.COOKIES.get("username")

            checked="checked"
        else:
            username=""
            checked=""
        return render(request,"login.html",{"username":username,"checked":checked})

    def post(self,request):
        # 接受数据
        username = request.POST.get("username")
        password = request.POST.get('pwd')

        # 验证
        if not all([username,password]):
            return render(request,"login.html",{"errmsg":"信息不完整"})

        user=authenticate(username=username,password=password)
        if user is not None:
            if user.is_active:
                login(request,user)
                url=request.GET.get("next",reverse("goods:index"))
                response=redirect(url)

                remember=request.POST.get("remember")
                if remember=="on":
                    response.set_cookie('username',username,max_age=7*24*3600)
                else:
                    response.delete_cookie("username")

                return response

            else:
                return render(request,'login.html',{"errmsg":"账户未激活"})

        else:
            return render(request,'login.html',{"errmsg":"用户名或密码错误"})


class LogoutView(View):
    def get(self,request):
        # 清除session
        logout(request)
        return redirect(reverse("goods:index"))



class UserInfoView(LoginRequiredMixin,View):
    def get(self, request):
        '''显示'''
        # Django会给request对象添加一个属性request.user
        # 如果用户未登录->user是AnonymousUser类的一个实例对象
        # 如果用户登录->user是User类的一个实例对象
        # request.user.is_authenticated()

        # 获取用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user)

        # 获取用户的历史浏览记录
        # from redis import StrictRedis
        # sr = StrictRedis(host='172.16.179.130', port='6379', db=9)
        con = get_redis_connection('default')

        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的5个商品的id
        sku_ids = con.lrange(history_key, 0, 4)  # [2,3,1]

        # 从数据库中查询用户浏览的商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        #
        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)

        # 遍历获取用户浏览的商品信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {'page': 'user',
                   'address': address,
                   'goods_li': goods_li}

        # 除了你给模板文件传递的模板变量之外，django框架会把request.user也传给模板文件
        return render(request, 'user_center_info.html', context)



class UserOrderView(LoginRequiredMixin,View):
    def get(self,request):
        return render(request,'user_center_order.html',{'page':'order'})


class AddressView(LoginRequiredMixin,View):
    def get(self,request):
        user=request.user

        try:
            address = Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            address=None
        return render(request,'user_center_site.html',{'page':'address','address':address})

    def post(self,request):
        receiver=request.POST.get('receiver')
        addr=request.POST.get('addr')
        zip_code=request.POST.get('zip_code')
        phone=request.POST.get('phone')

        if not all([receiver,addr,phone]):
            return render(request,'user_center_site.html',{"errmsg":"数据不完整"})

        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request,'user_center_site.html',{"errmsg":"手机格式不正确"})

        user=request.user
        try:
            address = Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            address=None
        if address:
            is_default=False
        else:
            is_default=True


        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)


        return redirect(reverse("user:address"))




