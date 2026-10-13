from decimal import Decimal as D
from types import SimpleNamespace as NS

from django.test import SimpleTestCase

from . import pricing


class PricingTests(SimpleTestCase):
    setting = NS(free_shipping_threshold=D("2000"), b2b_free_shipping_threshold=D("15000"), flat_shipping_charge=D("80"),
                 outstation_surcharge=D("40"), shipping_gst_rate=D("18"), cod_fee=D("50"), seller_state="Uttar Pradesh")

    def line(self, price, qty):
        return {"product": NS(gst_rate=D("18")), "qty": qty, "unit_price": D(price), "line_total": D(price) * qty}

    def test_in_state_splits_cgst_sgst(self):
        t = pricing.compute([self.line("1099", 1)], "Uttar Pradesh", self.setting, False, "razorpay")
        self.assertEqual(t["total"], D("1179.00"))
        self.assertEqual(t["igst"], 0)
        self.assertEqual(t["taxable"] + t["tax"], t["total"])

    def test_out_of_state_igst_and_cod(self):
        t = pricing.compute([self.line("1099", 1)], "Maharashtra", self.setting, False, "cod")
        self.assertEqual(t["shipping"], D("120.00"))
        self.assertEqual(t["total"], D("1269.00"))
        self.assertEqual(t["cgst"], 0)

    def test_free_shipping_thresholds(self):
        self.assertEqual(pricing.compute([self.line("1100", 2)], "Delhi", self.setting)["shipping"], 0)
        self.assertEqual(pricing.compute([self.line("800", 12)], "Delhi", self.setting, True)["shipping"], D("120.00"))
        self.assertEqual(pricing.compute([self.line("800", 20)], "Delhi", self.setting, True)["shipping"], 0)
