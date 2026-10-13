"""All prices in the shop include GST. This module splits tax out for invoices and adds shipping."""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def split_inclusive(amount, rate):
    """Return (taxable_value, tax) for a GST-inclusive amount."""
    amount, rate = Decimal(amount), Decimal(rate)
    taxable = money(amount / (1 + rate / 100))
    return taxable, money(amount - taxable)


def compute(lines, state, setting, wholesale=False, method=None):
    subtotal = money(sum((l["line_total"] for l in lines), ZERO))
    taxable_total, tax_total = ZERO, ZERO
    for l in lines:
        l["taxable"], l["tax"] = split_inclusive(l["line_total"], l["product"].gst_rate)
        taxable_total += l["taxable"]
        tax_total += l["tax"]

    shipping = ZERO
    threshold = setting.b2b_free_shipping_threshold if wholesale else setting.free_shipping_threshold
    if lines and subtotal < threshold:
        shipping = setting.flat_shipping_charge
        if state and state != setting.seller_state:
            shipping += setting.outstation_surcharge
    cod_fee = setting.cod_fee if (method == "cod" and lines) else ZERO

    for charge in (shipping, cod_fee):
        if charge:
            t, x = split_inclusive(charge, setting.shipping_gst_rate)
            taxable_total += t
            tax_total += x

    intra = (not state) or state == setting.seller_state
    if intra:
        cgst = money(tax_total / 2)
        sgst, igst = tax_total - cgst, ZERO
    else:
        cgst = sgst = ZERO
        igst = tax_total
    return {
        "subtotal": subtotal, "shipping": money(shipping), "cod_fee": money(cod_fee),
        "taxable": taxable_total, "cgst": cgst, "sgst": sgst, "igst": igst, "tax": tax_total,
        "total": money(subtotal + shipping + cod_fee), "intra_state": intra,
        "free_shipping_threshold": threshold, "to_free_shipping": max(ZERO, threshold - subtotal) if lines else ZERO,
    }
