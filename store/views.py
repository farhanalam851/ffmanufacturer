from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import OrderItem

from .forms import ReviewForm
from .models import Category, Product, Review, Wishlist

SORTS = {
    "new": (F("created").desc(), "Newest"),
    "price_asc": (F("price").asc(), "Price: low to high"),
    "price_desc": (F("price").desc(), "Price: high to low"),
    "rating": (F("avg_rating").desc(nulls_last=True), "Top rated"),
    "popular": (F("sold").desc(), "Best selling"),
}


def catalog(request, slug=None):
    category = get_object_or_404(Category, slug=slug, is_active=True) if slug else None
    sold_sq = (
        OrderItem.objects.filter(product=OuterRef("pk")).exclude(order__status="cancelled")
        .values("product").annotate(s=Sum("quantity")).values("s")
    )
    qs = Product.objects.active().with_rating().select_related("category").annotate(
        sold=Coalesce(Subquery(sold_sq, output_field=IntegerField()), 0)
    )
    if category:
        qs = qs.filter(category=category)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(color__icontains=q) | Q(category__name__icontains=q))
    gender = request.GET.get("gender", "")
    if gender in ("men", "women", "unisex"):
        qs = qs.filter(Q(gender=gender) | Q(gender="unisex"))
    for key, op in (("min", "gte"), ("max", "lte")):
        val = request.GET.get(key, "")
        if val.isdigit():
            qs = qs.filter(**{f"price__{op}": int(val)})
    if request.GET.get("in_stock") == "1":
        qs = qs.filter(stock__gt=0)
    sort = request.GET.get("sort", "new")
    if sort not in SORTS:
        sort = "new"
    qs = qs.order_by(SORTS[sort][0], "-created")

    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    wished = set()
    if request.user.is_authenticated:
        wished = set(Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True))
    return render(request, "store/catalog.html", {
        "category": category, "page": page, "q": q, "gender": gender, "sort": sort,
        "sorts": [(k, v[1]) for k, v in SORTS.items()],
        "categories": Category.objects.filter(is_active=True).annotate(n=Count("products", filter=Q(products__is_active=True))),
        "querystring": params.urlencode(), "wished": wished, "total": page.paginator.count,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.active().with_rating().prefetch_related("gallery", "tiers"), slug=slug)
    reviews = product.reviews.filter(is_approved=True).select_related("user")
    dist = {i: 0 for i in range(1, 6)}
    for r in reviews:
        dist[r.rating] += 1
    verified_ids = set(
        OrderItem.objects.filter(product=product, order__payment_status="paid").values_list("order__user_id", flat=True)
    ) | set(OrderItem.objects.filter(product=product, order__status="delivered").values_list("order__user_id", flat=True))
    existing = None
    form = None
    if request.user.is_authenticated:
        existing = Review.objects.filter(product=product, user=request.user).first()
        form = ReviewForm(instance=existing)
    related = Product.objects.active().with_rating().filter(category=product.category).exclude(pk=product.pk)[:4]
    return render(request, "store/product_detail.html", {
        "product": product, "reviews": reviews, "dist": dist, "verified_ids": verified_ids, "form": form,
        "existing": existing, "related": related, "images": [product.image] + [g.image for g in product.gallery.all()],
        "in_wishlist": request.user.is_authenticated and Wishlist.objects.filter(user=request.user, product=product).exists(),
        "sizes": product.size_list,
    })


@login_required
@require_POST
def review_add(request, slug):
    product = get_object_or_404(Product, slug=slug)
    existing = Review.objects.filter(product=product, user=request.user).first()
    form = ReviewForm(request.POST, request.FILES, instance=existing)
    if form.is_valid():
        review = form.save(commit=False)
        review.product, review.user = product, request.user
        review.save()
        messages.success(request, "Thanks. Your review is published.")
    else:
        messages.error(request, "Review not saved: " + "; ".join(e for errs in form.errors.values() for e in errs))
    return redirect(product.get_absolute_url() + "#reviews")


@login_required
def wishlist(request):
    items = Wishlist.objects.filter(user=request.user, product__is_active=True).select_related("product__category")
    return render(request, "store/wishlist.html", {"items": items, "wished_ids": {i.product_id for i in items}})


@login_required
@require_POST
def wishlist_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    obj, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        obj.delete()
        messages.info(request, "Removed from wishlist.")
    else:
        messages.success(request, "Saved to wishlist.")
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else product.get_absolute_url())
