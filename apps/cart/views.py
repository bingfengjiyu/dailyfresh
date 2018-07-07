from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from apps.goods.models import GoodsSKU
from util.mixin import LoginRequiredMixin
from django_redis import get_redis_connection

# Create your views here.

class CartInfoView(LoginRequiredMixin,View):
    # 购物车页面
    def get(self,request):
        user=request.user
        conn=get_redis_connection('default')
        cart_key='cart_%d'%user.id
        cart_dict=conn.hgetall(cart_key)
        skus=[]
        total_count=0
        total_price=0
        for sku_id,count in cart_dict.items():
            sku=GoodsSKU.objects.get(id=sku_id)
            amount=sku.price*int(count)
            # 保存商品的小计
            sku.amount=amount
            # 保存商品的数量
            sku.count=count
            skus.append(sku)

            total_count+=int(count)
            total_price+=amount

        context={'total_count':total_count,
                 'total_price':total_price,
                 'skus':skus}
        return  render(request,'cart.html',context)


class CartAddView(View):
    def post(self,request):
        user=request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0,"errmsg":"请先登陆"})
        sku_id=request.POST.get('sku_id')
        count=request.POST.get('count')
        if not all([sku_id,count]):
            return JsonResponse({'res':1,"errmsg":"数据不完整"})
        try:
            count=int(count)
        except Exception as e:
            return JsonResponse({'res':2,"errmsg":"商品数目出错"})
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except Exception as e:
            return JsonResponse({'res':3,"errmsg":"商品不存在"})
        conn=get_redis_connection('default')
        cart_key='cart_%d'%user.id
        # 如果没有返回none
        cart_count=conn.hget(cart_key,sku_id)
        if cart_count:
            count+=int(cart_count)
        if count>sku.stock:
            return JsonResponse({'res':4,"errmsg":"商品库存不足"})
        conn.hset(cart_key,sku_id,count)
        total_count=conn.hlen(cart_key)
        return JsonResponse({'res':5,"total_count":total_count,"errmsg":"添加成功"})
