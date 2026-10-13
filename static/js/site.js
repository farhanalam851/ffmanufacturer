(function () {
  var toggle = document.querySelector('.nav-toggle'), nav = document.getElementById('site-nav');
  if (toggle && nav) toggle.addEventListener('click', function () {
    var open = nav.classList.toggle('open'); toggle.setAttribute('aria-expanded', open);
  });
  var ft = document.querySelector('.filter-toggle'), fb = document.getElementById('filters');
  if (ft && fb) ft.addEventListener('click', function () { var o = fb.classList.toggle('open'); ft.setAttribute('aria-expanded', o); });
  document.querySelectorAll('.msg button').forEach(function (b) { b.addEventListener('click', function () { b.closest('li').remove(); }); });

  // Product gallery
  var main = document.getElementById('gallery-main');
  document.querySelectorAll('.thumbs button').forEach(function (b) {
    b.addEventListener('click', function () {
      main.src = b.dataset.src;
      document.querySelectorAll('.thumbs button').forEach(function (x) { x.removeAttribute('aria-current'); });
      b.setAttribute('aria-current', 'true');
    });
  });

  // Quantity steppers
  document.querySelectorAll('.qty').forEach(function (q) {
    var input = q.querySelector('input'), max = parseInt(input.max || '5000', 10);
    q.querySelectorAll('button').forEach(function (b) {
      b.addEventListener('click', function () {
        var v = (parseInt(input.value, 10) || 1) + (b.dataset.step === '+' ? 1 : -1);
        input.value = Math.max(parseInt(input.min || '1', 10), Math.min(max, v));
        input.dispatchEvent(new Event('input', { bubbles: true }));
      });
    });
  });

  // Wholesale tier highlight on product page
  var qtyInput = document.getElementById('pdp-qty'), rows = document.querySelectorAll('.tier-box tr[data-min]');
  if (qtyInput && rows.length) {
    var mark = function () {
      var q = parseInt(qtyInput.value, 10) || 1, hit = null;
      rows.forEach(function (r) { r.classList.remove('hit'); if (q >= parseInt(r.dataset.min, 10)) hit = r; });
      if (hit) hit.classList.add('hit');
    };
    qtyInput.addEventListener('input', mark); mark();
  }

  // Checkout: toggle new address form + live totals
  var form = document.getElementById('checkout-form');
  if (form) {
    var newBox = document.getElementById('new-address');
    var stateOf = function () {
      var sel = form.querySelector('input[name=address_id]:checked');
      if (!sel || sel.value === 'new') { var s = form.querySelector('#id_state'); return s ? s.value : ''; }
      return sel.dataset.state;
    };
    var refresh = function () {
      var sel = form.querySelector('input[name=address_id]:checked');
      if (newBox) newBox.hidden = !(sel && sel.value === 'new');
      var m = form.querySelector('input[name=payment_method]:checked');
      var url = form.dataset.quote + '?state=' + encodeURIComponent(stateOf()) + '&method=' + (m ? m.value : '');
      fetch(url, { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (d) {
        var set = function (id, v) { var el = document.getElementById(id); if (el) el.textContent = v; };
        set('q-subtotal', d.subtotal); set('q-shipping', d.shipping); set('q-cod', d.cod_fee); set('q-total', d.total);
        set('q-tax', d.tax); set('q-taxlabel', d.tax_label);
        var cod = document.getElementById('q-cod-row'); if (cod) cod.hidden = !d.has_cod;
      }).catch(function () {});
    };
    form.addEventListener('change', refresh); refresh();
  }

// ---- Loading states: disable submit buttons and show a spinner while the page posts
document.querySelectorAll('form[method="post"], form[method="POST"]').forEach(function (f) {
  f.addEventListener('submit', function (e) {
    if (e.defaultPrevented) return;
    var b = e.submitter || f.querySelector('button[type=submit]');
    if (!b || b.classList.contains('is-loading')) { if (b) e.preventDefault(); return; }
    var label = b.dataset.loading || 'Please wait';
    b.dataset.label = b.innerHTML;
    // defer disabling so the button's own name/value (e.g. buy_now) is still submitted
    setTimeout(function () { b.classList.add('is-loading'); b.setAttribute('aria-busy', 'true'); b.innerHTML = '<span class="spin" aria-hidden="true"></span>' + label + '…'; b.style.pointerEvents = 'none'; }, 0);
  });
});
window.addEventListener('pageshow', function (e) {
  if (!e.persisted) return;
  document.querySelectorAll('.is-loading').forEach(function (b) { b.classList.remove('is-loading'); b.removeAttribute('aria-busy'); b.style.pointerEvents = ''; if (b.dataset.label) b.innerHTML = b.dataset.label; });
});

// ---- Form error states: mark invalid inputs for assistive tech and bring the first error into view
document.querySelectorAll('.field.has-error').forEach(function (fld) {
  var list = fld.querySelector('.errorlist');
  fld.querySelectorAll('input, select, textarea').forEach(function (i) {
    i.setAttribute('aria-invalid', 'true'); if (list && list.id) i.setAttribute('aria-describedby', list.id);
  });
});
var summary = document.querySelector('[data-error-summary]');
if (summary) { summary.scrollIntoView({ block: 'center' }); summary.focus({ preventScroll: true }); }
// clear the error look as soon as the visitor edits the field
document.addEventListener('input', function (e) {
  var fld = e.target.closest && e.target.closest('.field.has-error');
  if (fld) { fld.classList.remove('has-error'); e.target.removeAttribute('aria-invalid'); }
});
// client-side check for required fields on forms that opt out of native bubbles (novalidate)
document.querySelectorAll('form[novalidate]').forEach(function (f) {
  f.addEventListener('submit', function (e) {
    var bad = null;
    f.querySelectorAll('input[required], select[required], textarea[required]').forEach(function (i) {
      if (i.type === 'radio' || i.type === 'checkbox' || i.type === 'hidden' || i.closest('[hidden]')) return;
      var fld = i.closest('.field'); if (!fld) return;
      var old = fld.querySelector('.js-err'); if (old) old.remove();
      if (!i.value.trim()) {
        fld.classList.add('has-error'); i.setAttribute('aria-invalid', 'true');
        var u = document.createElement('ul'); u.className = 'errorlist js-err'; u.innerHTML = '<li>This field is required.</li>'; fld.appendChild(u);
        bad = bad || i;
      }
    });
    if (bad) { e.preventDefault(); e.stopImmediatePropagation(); bad.focus(); }
  }, true);
});

// ---- Cookie banner and analytics (Google Analytics 4 loads only after consent)
var KEY = 'ff_cookie_consent';
function getConsent() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
function loadAnalytics() {
  if (!window.FF || !FF.gaId || window.__gaLoaded) return; window.__gaLoaded = true;
  var s = document.createElement('script'); s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(FF.gaId); document.head.appendChild(s);
  window.dataLayer = window.dataLayer || []; window.gtag = function () { dataLayer.push(arguments); };
  gtag('js', new Date()); gtag('config', FF.gaId, { anonymize_ip: true });
  if (FF.conversion) gtag('event', 'generate_lead', { lead_type: FF.conversion });
}
var banner = document.getElementById('cookie-banner');
var consent = getConsent();
if (consent === 'yes') loadAnalytics();
else if (!consent && banner) banner.hidden = false;
if (banner) banner.addEventListener('click', function (e) {
  var b = e.target.closest('[data-consent]'); if (!b) return;
  try { localStorage.setItem(KEY, b.dataset.consent); } catch (er) {}
  banner.hidden = true; if (b.dataset.consent === 'yes') loadAnalytics();
});
document.querySelectorAll('[data-cookie-settings]').forEach(function (a) {
  a.addEventListener('click', function (e) { e.preventDefault(); try { localStorage.removeItem(KEY); } catch (er) {} if (banner) banner.hidden = false; });
});
document.body.classList.toggle('has-banner', !!(banner && !banner.hidden));

// ---- CSP-safe replacements for inline handlers
document.addEventListener('submit', function (e) {
  var m = e.target.getAttribute && e.target.getAttribute('data-confirm');
  if (m && !window.confirm(m)) { e.preventDefault(); e.stopImmediatePropagation(); }
}, true);
document.querySelectorAll('[data-print]').forEach(function (b) { b.addEventListener('click', function () { window.print(); }); });
})();
