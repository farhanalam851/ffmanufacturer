"""python manage.py seed_demo  -> loads categories and sample products using the client's photos.

Names, SKUs and prices are PLACEHOLDERS. Replace them in the admin before going live.
"""
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from core.models import SiteSetting
from store.models import Category, Product, WholesaleTier

SEED = Path(settings.BASE_DIR) / "static" / "seed"

CATEGORIES = [
    ("Formal Leather Belts", "men", "formal-classic.webp", "Clean, flat-stitched belts for the office and occasions."),
    ("Textured & Stitched", "men", "textured-stitched.webp", "Crocodile-embossed and pebble-grain leather with contrast stitching."),
    ("Casual Vintage", "men", "casual-vintage.webp", "Distressed-finish belts in tan, olive, slate and black."),
    ("Braided & Elastic", "unisex", "braided.webp", "Woven stretch belts with a leather tip. Easy on, easy fit."),
    ("Women's Python Print", "women", "python-print.webp", "Slim snake-embossed belts with gold buckles."),
    ("Women's Stretch & Waist", "women", "stretch-waist.webp", "Wide elastic waist belts with statement gold clasps."),
    ("Women's Colour Belts", "women", "colour-wall.webp", "Slim leather belts in tan, navy, mustard, white and more."),
]

M = "30,32,34,36,38,40,42"
# name, category, gender, color, price, sale, sizes, image, featured, short description
PRODUCTS = [
    ("Executive Tan Dress Belt", 0, "men", "Tan", 1299, 1099, M, "tan-executive.webp", True, "Double-keeper tan belt with cream saddle stitching and a polished steel buckle."),
    ("Classic Formal Belt, Black", 0, "men", "Black", 899, None, M, "formal-classic.webp", True, "Plain black leather, edge-stitched, with a brushed steel pin buckle."),
    ("Classic Formal Belt, Brown", 0, "men", "Brown", 899, None, M, "formal-classic.webp", False, "Dark brown leather for suits and chinos."),
    ("Croc-Embossed Stitch Belt", 1, "men", "Black", 1499, 1299, M, "textured-stitched.webp", True, "Crocodile-grain leather with contrast stitching and a gunmetal buckle."),
    ("Pebble Grain Stitch Belt", 1, "men", "Black", 1399, None, M, "textured-stitched.webp", False, "Soft pebble-grain finish that hides everyday scuffs."),
    ("Vintage Tan Casual Belt", 2, "men", "Tan", 1199, None, M, "casual-vintage.webp", True, "Distressed tan leather with matching tonal stitching."),
    ("Olive Vintage Casual Belt", 2, "men", "Olive", 1199, None, M, "casual-vintage.webp", False, "Washed olive leather with an antique-finish buckle."),
    ("Woven Elastic Belt, Brown", 3, "unisex", "Brown", 699, 599, "", "braided.webp", True, "Braided stretch weave with leather tip and antique-silver buckle."),
    ("Python-Print Belt, Red", 4, "women", "Red", 1099, None, "26,28,30,32,34", "python-print.webp", True, "Glossy red snake-embossed leather with a gold double-pin buckle."),
    ("Python-Print Belt, Copper", 4, "women", "Copper", 1099, None, "26,28,30,32,34", "python-print.webp", False, "Copper-bronze snake emboss with a gold buckle."),
    ("Python-Print Belt, Grey", 4, "women", "Grey", 1099, None, "26,28,30,32,34", "python-print.webp", False, "Smoky grey snake emboss with a gold buckle."),
    ("Gold Coil Stretch Waist Belt", 5, "women", "Black / Gold", 799, None, "", "stretch-waist.webp", True, "Wide black elastic with a layered gold coil clasp."),
    ("Gold Ring Stretch Waist Belt", 5, "women", "Black / Gold", 799, None, "", "stretch-waist.webp", False, "Black elastic with an interlocking gold ring clasp."),
    ("Slim Leather Belt, Assorted Colours", 6, "women", "Assorted", 599, None, "26,28,30,32,34", "colour-wall.webp", False, "Slim belts in tan, navy, mustard, white and black with gold or silver buckles."),
]


def round5(x):
    return int(round(x / 5.0) * 5)


class Command(BaseCommand):
    help = "Load demo categories and products (placeholder prices)."

    def handle(self, *args, **opts):
        SiteSetting.load()
        cats = []
        for i, (name, gender, img, desc) in enumerate(CATEGORIES):
            cat, created = Category.objects.get_or_create(name=name, defaults={"gender": gender, "description": desc, "sort_order": i})
            if created:
                with open(SEED / img, "rb") as f:
                    cat.image.save(img, File(f), save=True)
            cats.append(cat)
        for n, (name, ci, gender, color, price, sale, sizes, img, featured, short) in enumerate(PRODUCTS, start=1):
            if Product.objects.filter(name=name).exists():
                continue
            p = Product(
                category=cats[ci], name=name, sku=f"FF-{n:03d}", gender=gender, color=color, sizes=sizes,
                price=Decimal(price), sale_price=Decimal(sale) if sale else None, stock=60 + n * 7,
                is_featured=featured, short_description=short, buckle="Steel" if ci < 4 else "Gold",
                description=short + "\n\nMade at our workshop in Jajmau, Kanpur. Available in bulk for retailers, corporate gifting and uniform orders.",
            )
            with open(SEED / img, "rb") as f:
                p.image.save(img, File(f), save=False)
            p.save()
            base = Decimal(sale or price)
            for qty, factor in ((12, 0.82), (50, 0.72), (100, 0.65)):
                WholesaleTier.objects.create(product=p, min_qty=qty, price=Decimal(round5(float(base) * factor)))
        self.stdout.write(self.style.SUCCESS("Demo catalogue loaded. Replace placeholder names and prices in /admin/."))
