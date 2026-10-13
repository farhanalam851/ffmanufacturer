from django.core.cache import cache
from django.test import TestCase, override_settings


class SecurityTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_security_headers_and_csp_nonce(self):
        r = self.client.get("/")
        csp = r["Content-Security-Policy"]
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("object-src 'none'", csp)
        nonce = csp.split("'nonce-")[1].split("'")[0]
        self.assertIn(f'nonce="{nonce}"', r.content.decode())
        self.assertEqual(r["X-Frame-Options"], "DENY")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_private_pages_not_cached_or_indexed(self):
        r = self.client.get("/cart/")
        self.assertIn("no-store", r["Cache-Control"])
        self.assertIn("noindex", r["X-Robots-Tag"])

    def test_login_bruteforce_is_blocked(self):
        for _ in range(8):
            self.client.post("/account/login/", {"username": "a@b.com", "password": "wrong"})
        r = self.client.post("/account/login/", {"username": "a@b.com", "password": "wrong"})
        self.assertEqual(r.status_code, 429)

    def test_order_tracking_is_throttled(self):
        for _ in range(10):
            self.client.post("/orders/track/", {"order_number": "FF1", "phone": "9999999999"})
        self.assertEqual(self.client.post("/orders/track/", {"order_number": "FF1", "phone": "9999999999"}).status_code, 429)

    def test_honeypot_blocks_bots_silently(self):
        from core.models import Enquiry
        data = {"name": "Bot", "phone": "9889030693", "email": "b@b.com", "message": "spam", "website": "http://spam"}
        r = self.client.post("/contact/", data)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_private_areas_require_login(self):
        for url in ["/manage/", "/orders/", "/checkout/", "/account/dashboard/"]:
            self.assertEqual(self.client.get(url).status_code, 302, url)

    def test_healthz_checks_database(self):
        r = self.client.get("/healthz/")
        self.assertEqual((r.status_code, r.content), (200, b"ok"))


class DatabaseUrlTests(TestCase):
    def test_special_characters_in_password(self):
        from config.dburl import parse_database_url
        d = parse_database_url("postgresql://postgres.abc:pa@ss#w/rd%21@aws-0.pooler.supabase.com:6543/postgres")
        self.assertEqual((d["USER"], d["PASSWORD"], d["HOST"], d["PORT"], d["NAME"]),
                         ("postgres.abc", "pa@ss#w/rd!", "aws-0.pooler.supabase.com", 6543, "postgres"))

    def test_placeholder_is_rejected_with_clear_message(self):
        from django.core.exceptions import ImproperlyConfigured
        from config.dburl import parse_database_url
        with self.assertRaisesMessage(ImproperlyConfigured, "placeholder"):
            parse_database_url("postgresql://u:[YOUR-PASSWORD]@h:6543/postgres")
