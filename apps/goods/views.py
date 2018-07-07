from django.shortcuts import render,redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django_redis import get_redis_connection
from apps.order.models import OrderGoods
from apps.goods.models import GoodsType,GoodsSKU,IndexGoodsBanner,IndexTypeGoodsBanner,IndexPromotionBanner
from django.core.cache import cache
from django.core.paginator import Paginator

# Create your views here.

# http://127.0.0.1:8000
class IndexView(View):
    def get(self,request):
        '''首页'''
        # 尝试从缓存中获取数据
        context=cache.get('index_page_data')
        if context is None:
            types=GoodsType.objects.all()
            goods_banners=IndexGoodsBanner.objects.all().order_by("index")
            promotion_banners=IndexPromotionBanner.objects.all().order_by("index")

            for type in types:
                image_banners=IndexTypeGoodsBanner.objects.filter(type=type,display_type=1).order_by("index")
                title_banners=IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by("index")
                type.image_banners=image_banners
                type.title_banners=title_banners



            context = {"types": types,
                       "goods_banners": goods_banners,
                       "promotion_banners": promotion_banners,}
            # 设置缓存
            cache.set('index_page_data',context,3600)

        user=request.user
        cart_count = 0
        if user.is_authenticated():
            conn=get_redis_connection('default')
            cart_key='cart_%d'%user.id
            cart_count=conn.hlen(cart_key)

        context.update(cart_count=cart_count)

        return render(request, 'index.html',context)


class DetailView(View):
    def get(self,request,goods_id):
        try:
            sku=GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return  redirect(reverse("goods:index"))
        types=GoodsType.objects.all()
        sku_orders=OrderGoods.objects.filter(sku=sku).exclude(comment="")

        new_skus=GoodsSKU.objects.filter(type=sku.type).order_by("-create_time")[:2]
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            conn=get_redis_connection('default')
            history_key='history_%d' % user.id
            conn.lrem(history_key,0,goods_id)
            conn.lpush(history_key,goods_id)
            conn.ltrim(history_key,0,6)

        context={"sku":sku,"types":types,"sku_orders":sku_orders,
                 "new_skus":new_skus,"cart_count":cart_count,
                 'same_spu_skus':same_spu_skus}
        return render(request,"detail.html",context)


# 种类id 页码 排序方式
# list?type_id=种类id&page=页码&sort=排序方式
# /list/种类id/页码/排序方式
# /list/种类id/页码?sort=排序方式

class ListView(View):
    def get(self,request,type_id,page):
        # 获取种类信息
        try:
            type=GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return  redirect(reverse('goods:index'))
        types=GoodsType.objects.all()
        sort=request.GET.get('sort')
        if sort=='price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort=='hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort='default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')
        paginator=Paginator(skus,1)
        try:
            page=int(page)
        except Exception as e:
            page=1

        if page>paginator.num_pages:
            page=1

        skus_page=paginator.page(page)
        new_skus = GoodsSKU.objects.filter(type=type).order_by("-create_time")[:2]
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        context = {"type": type, "types": types, "skus_page": skus_page,
                   "new_skus": new_skus, "cart_count": cart_count,'sort':sort}

        return render(request,"list.html",context)