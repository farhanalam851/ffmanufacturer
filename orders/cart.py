from store.models import Product


class Cart:
    """Session cart: {"<product_id>|<size>": {"p": id, "s": size, "q": qty}}"""

    KEY = "cart"

    def __init__(self, request):
        self.session = request.session
        self.user = request.user
        self.data = self.session.get(self.KEY) or {}

    def _save(self):
        self.session[self.KEY] = self.data
        self.session.modified = True

    def add(self, product, size, qty):
        key = f"{product.pk}|{size}"
        item = self.data.get(key, {"p": product.pk, "s": size, "q": 0})
        item["q"] = max(1, min(item["q"] + qty, product.stock, 5000))
        self.data[key] = item
        self._save()

    def set_qty(self, key, qty):
        if key in self.data:
            if qty <= 0:
                del self.data[key]
            else:
                self.data[key]["q"] = min(qty, 5000)
            self._save()

    def remove(self, key):
        if self.data.pop(key, None) is not None:
            self._save()

    def clear(self):
        self.data = {}
        self._save()

    def lines(self):
        ids = {i["p"] for i in self.data.values()}
        products = {p.pk: p for p in Product.objects.active().filter(pk__in=ids).prefetch_related("tiers")}
        lines, dirty = [], False
        for key, item in list(self.data.items()):
            product = products.get(item["p"])
            if not product or product.stock <= 0:
                del self.data[key]
                dirty = True
                continue
            qty = min(item["q"], product.stock)
            if qty != item["q"]:
                item["q"], dirty = qty, True
            unit = product.unit_price(qty, self.user)
            lines.append({
                "key": key, "product": product, "size": item["s"], "qty": qty, "unit_price": unit,
                "line_total": unit * qty, "tier_applied": unit < product.retail_price,
            })
        if dirty:
            self._save()
        return lines

    def __len__(self):
        return sum(i["q"] for i in self.data.values())
