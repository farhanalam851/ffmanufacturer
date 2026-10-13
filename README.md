# F.F Manufacturer: leather belts store (Django)

Retail and B2B e-commerce site for F.F Manufacturer, Jajmau, Kanpur 208010.

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations core accounts store orders
python manage.py migrate
python manage.py seed_demo          # loads demo catalogue using the client's photos
python manage.py createsuperuser    # email + first name + password
python manage.py runserver
```

Open http://127.0.0.1:8000 (shop), /manage/ (store dashboard), /admin/ (full admin).
Online payment runs in **demo mode** until Razorpay keys are set (only while DEBUG=1).

Run the tests with `python manage.py test`.

## What is included

| Area | Details |
|---|---|
| Storefront | Home, catalogue with search, filters and sorting, category pages, product pages with gallery, size picker, ratings and photo reviews, wishlist |
| B2B | Business registration with GSTIN, admin verification, wholesale tier pricing (per product, from N pieces), bulk enquiry form, higher free-shipping threshold for verified businesses |
| Accounts | Register, login (email), logout, forgot password, profile, saved addresses, customer dashboard |
| Checkout | Session cart, address book, live totals, Razorpay, cash on delivery (fee and cap), bank transfer / UPI |
| GST | Prices include GST. Invoices split taxable value and CGST+SGST (same state as seller) or IGST (other states). HSN code and GST rate per product. Printable GST invoice |
| Shipping | Flat charge, extra outside seller state, free above a threshold (retail and wholesale). All editable in admin under Site settings |
| Orders | Stock reserved at order time and restored on cancel, status flow, courier and tracking number, tracking page for guests, emails |
| Staff dashboard | /manage/: sales, 14-day chart, orders to process, best sellers, low stock, GSTIN verification queue, enquiries, order updates |
| Admin | Django admin for products (with tiers and gallery), categories, reviews, orders (CSV export), users, site settings |
| Mobile | Responsive layout, 44px touch targets, installable on Android and iOS home screens (web manifest, icons, safe-area handling), WhatsApp button |

## Before going live (important)

1. **Replace the demo catalogue.** Names, SKUs, prices, wholesale tiers and stock from `seed_demo` are placeholders.
2. **Site settings** (/admin/core/sitesetting/): enter the real GSTIN, email, bank details, shipping and COD rules.
3. **GST rate.** Each product defaults to 18%. Confirm the correct rate for HSN 4203 and your price bands with your CA.
4. **Policies.** Shipping, returns, terms and privacy text is a draft. Have it reviewed.
5. **Photos.** The braided-belt image carries a stock-photo watermark and the tan belt close-up looks AI-generated. Replace them with the client's own product photos in the admin before launch.
6. **Razorpay.** Create keys at dashboard.razorpay.com and set `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`. Add a webhook to `https://yourdomain.com/payment/webhook/` for events `payment.captured`, `order.paid` and `payment.failed`, with the secret in `RAZORPAY_WEBHOOK_SECRET`.
7. **Email.** Set the SMTP variables; otherwise emails print to the console.

## Deploying

Copy `.env.example` to `.env` values as environment variables, set `DJANGO_DEBUG=0`, use Postgres for production, then:

```bash
python manage.py collectstatic --noinput
gunicorn config.wsgi
```

Put Nginx (or similar) in front with HTTPS, and serve `/media/` (uploaded photos) from the `media/` folder. Django does not serve media when DEBUG is off.

## Business flow

1. A business registers with company name and GSTIN.
2. Staff open /manage/customers/?pending=1 and click **Verify GSTIN**.
3. Wholesale tier prices then apply automatically on product pages and in the cart.

## Launch checklist notes
- Analytics: set `GA_MEASUREMENT_ID` (Google Analytics 4). It loads only after a visitor accepts the cookie banner.
- Favicons, OG image (`static/img/og-image.jpg`), robots.txt, sitemap.xml, thank-you page (`/thank-you/`) and custom 404 are included.
- Policy pages are draft text. Have them reviewed before launch.

## Deploying on Vercel

Vercel detects Django from `manage.py`, runs `collectstatic` and serves `/static/` from its CDN. It has no persistent disk, so you need a database and an image store.

1. **Database:** easiest free option with no card is Supabase (one project gives you Postgres and the image bucket). Use its **Transaction pooler** string as `DATABASE_URL` (Session pooler for the one-off `migrate`). `vercel.json` runs a daily `/healthz/` check so the free project never pauses for inactivity. Neon works too.
2. **Image storage:** create an S3-compatible bucket (Cloudflare R2 is cheap) with public read, and set the `AWS_*` variables from `.env.example`. Uploads through Vercel are limited to about 4.5 MB per request, so keep product photos small.
3. **Environment variables** (Project Settings > Environment Variables): `DJANGO_SECRET_KEY` (40+ random characters, required), `DATABASE_URL`, the `AWS_*` set, `DJANGO_ADMIN_URL` (a private path such as `ff-office-7k2/`), `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` (your custom domain), `RAZORPAY_*`, `EMAIL_*`, `DEFAULT_FROM_EMAIL`, optional `GA_MEASUREMENT_ID`.
4. **Create the tables once**, from your computer, pointing at the production database:
   ```
   export DATABASE_URL="postgres://..."   # production URL
   export DJANGO_SECRET_KEY="any-long-random-string-for-this-one-off-run-0123456789"
   export DJANGO_DEBUG=0 DJANGO_SSL_REDIRECT=0
   export AWS_STORAGE_BUCKET_NAME=your-bucket   # same bucket settings as production
   python manage.py migrate
   python manage.py createcachetable
   python manage.py createsuperuser
   ```
   (The cache table makes login and form rate limits work across serverless instances.)
5. **Deploy:** push to GitHub and import the repo in Vercel (root directory = this folder), or run `vercel deploy`. `vercel.json` pins the function to Seoul (`icn1`) to sit next to a Supabase Seoul database; if your database is in another region, change it to the nearest Vercel region.
6. **After the first deploy:** in Razorpay add the webhook `https://yourdomain/payment/webhook/`, then add the domain to Google Search Console and submit `/sitemap.xml`.

## Security built in
- Content-Security-Policy with per-request nonces, clickjacking block, MIME-sniff block, referrer and permissions policies, HSTS and HTTPS-only cookies in production.
- The app refuses to start in production without a strong `DJANGO_SECRET_KEY`. Debug is off by default on Vercel.
- Brute-force limits on site and admin login, order tracking, sign-up, password reset and enquiry forms; honeypot field against form bots.
- Configurable private admin URL, `noindex` on private areas, `no-store` caching on cart, checkout and account pages.
- Razorpay payments are verified by HMAC signature and webhook; order pages check ownership.
- Still recommended: a long unique password for every staff account, keeping Django updated, and two-factor login on your Vercel, GitHub and database accounts.
