/* ===== واجهة مشتركة: CSRF + إشعارات + نوافذ تأكيد + ملاحظات + جولة تعريفية ===== */
(function () {
  'use strict';
  var meta = document.querySelector('meta[name="csrf-token"]');
  var CSRF = meta ? meta.content : '';

  /* ---------- الترجمة (قاموس من /i18n/<lang>.js) ---------- */
  var DICT = window.I18N || {}, LANG = window.I18N_LANG || 'ar';
  function tr(s) {
    if (LANG === 'ar' || s == null) return s;
    var k = String(s).replace(/\s+/g, ' ').trim();
    return DICT[k] !== undefined ? DICT[k] : s;
  }
  var ATTRS = ['placeholder', 'title', 'aria-label', 'data-tip', 'data-confirm', 'data-confirm-title', 'data-confirm-ok'];
  function trNode(root) {
    if (LANG === 'ar' || !root) return;
    if (root.nodeType === 3) { fixText(root); return; }
    if (root.nodeType !== 1) return;
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, null), n = root;
    do {
      if (n.nodeType === 3) fixText(n);
      else if (n.nodeType === 1) {
        if (/^(SCRIPT|STYLE|TEXTAREA)$/.test(n.tagName)) continue;
        ATTRS.forEach(function (a) { if (n.hasAttribute(a)) { var v = tr(n.getAttribute(a)); if (v !== n.getAttribute(a)) n.setAttribute(a, v); } });
        if (n.tagName === 'INPUT' && /^(submit|button)$/.test(n.type)) n.value = tr(n.value);
      }
    } while ((n = w.nextNode()));
  }
  function fixText(node) {
    var raw = node.nodeValue; if (!raw || !/[\u0600-\u06FF]/.test(raw)) return;
    var k = raw.replace(/\s+/g, ' ').trim(), v = DICT[k];
    if (v !== undefined) { node.nodeValue = raw.replace(raw.trim(), v); return; }
    var out = raw, hit = false;
    (window.I18N_PATTERNS || []).forEach(function (p) { var r = new RegExp(p[0], 'g'); if (r.test(out)) { out = out.replace(new RegExp(p[0], 'g'), p[1]); hit = true; } });
    if (hit) node.nodeValue = out;
  }

  /* ---------- أدوات ---------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  /* ---------- CSRF: كل طلب POST يحمل التوكن تلقائياً ---------- */
  var _fetch = window.fetch ? window.fetch.bind(window) : null;
  if (_fetch) {
    window.fetch = function (input, init) {
      init = init || {};
      var method = String(init.method || (input && input.method) || 'GET').toUpperCase();
      if (method !== 'GET' && method !== 'HEAD' && CSRF) {
        var url = typeof input === 'string' ? input : (input && input.url) || '';
        var same = url.charAt(0) === '/' || url.indexOf(location.origin) === 0;
        if (same) {
          var h = new Headers(init.headers || {});
          h.set('X-CSRF-Token', CSRF);
          init.headers = h;
        }
      }
      return _fetch(input, init).then(function (res) {
        if (res.status === 401) {
          res.clone().json().then(function (j) {
            if (j && j.auth) { UI.toast(j.message, 'error', 6000); setTimeout(function () { location.href = '/'; }, 2200); }
          }).catch(function () {});
        }
        if (res.status === 400 && method !== 'GET') {
          var c = res.clone();
          c.json().then(function (j) {
            if (j && j.csrf) UI.toast(j.message, 'error', 7000);
          }).catch(function () {});
        }
        return res;
      });
    };
  }
  function addCsrfInput(form) {
    if (!CSRF || (form.method || '').toLowerCase() !== 'post') return;
    if (form.querySelector('input[name="csrf_token"]')) return;
    var i = document.createElement('input');
    i.type = 'hidden'; i.name = 'csrf_token'; i.value = CSRF;
    form.appendChild(i);
  }

  /* ---------- Toasts ---------- */
  var toastBox = null;
  var ICONS = { success: 'fa-circle-check', error: 'fa-circle-exclamation', warn: 'fa-triangle-exclamation', info: 'fa-circle-info' };
  function toast(msg, type, ms) {
    type = ICONS[type] ? type : (type === 'danger' ? 'error' : 'info');
    if (!toastBox) { toastBox = el('div'); toastBox.id = 'ui-toasts'; toastBox.setAttribute('role', 'status'); toastBox.setAttribute('aria-live', 'polite'); document.body.appendChild(toastBox); }
    var t = el('div', 'ui-toast ' + type, '<i class="fa-solid ' + ICONS[type] + '"></i><div class="t-body"></div><button class="t-x" aria-label="إغلاق">×</button>');
    t.querySelector('.t-body').textContent = tr(msg);
    function close() { if (!t.parentNode) return; t.classList.add('out'); setTimeout(function () { t.remove(); }, 180); }
    t.querySelector('.t-x').onclick = close;
    toastBox.appendChild(t);
    while (toastBox.children.length > 4) toastBox.firstChild.remove();
    setTimeout(close, ms || (type === 'error' ? 6500 : 4200));
    return t;
  }

  /* ---------- نوافذ التأكيد والإدخال ---------- */
  var lastFocus = null;
  function dialog(opts) {
    return new Promise(function (resolve) {
      lastFocus = document.activeElement;
      var bd = el('div', 'ui-backdrop');
      var dlg = el('div', 'ui-dialog' + (opts.danger ? ' danger' : ''));
      dlg.setAttribute('role', 'dialog'); dlg.setAttribute('aria-modal', 'true');
      var icon = opts.icon || (opts.danger ? 'fa-trash-can' : (opts.input ? 'fa-pen' : 'fa-circle-question'));
      dlg.innerHTML = '<div class="d-icon"><i class="fa-solid ' + icon + '"></i></div><h3></h3><p></p>' +
        (opts.input ? (opts.multiline ? '<textarea rows="3"></textarea>' : '<input type="text">') + '<div class="d-err"></div>' : '') +
        '<div class="ui-actions"><button class="ui-btn ' + (opts.danger ? 'danger' : 'primary') + '" data-ok></button><button class="ui-btn" data-no></button></div>';
      dlg.querySelector('h3').textContent = tr(opts.title || 'تأكيد');
      var p = dlg.querySelector('p'); if (opts.message) p.textContent = tr(opts.message); else p.remove();
      var ok = dlg.querySelector('[data-ok]'), no = dlg.querySelector('[data-no]');
      ok.textContent = tr(opts.okText || 'تأكيد'); no.textContent = tr(opts.cancelText || 'إلغاء');
      var inp = dlg.querySelector('textarea,input');
      if (inp) { inp.placeholder = tr(opts.placeholder || ''); inp.value = opts.value || ''; }
      var err = dlg.querySelector('.d-err');
      function done(v) { document.removeEventListener('keydown', onKey, true); bd.remove(); if (lastFocus && lastFocus.focus) try { lastFocus.focus(); } catch (e) {} resolve(v); }
      function submit() {
        if (inp) {
          var v = inp.value.trim();
          if (opts.required && !v) { err.textContent = opts.requiredMsg || 'هذا الحقل مطلوب'; err.style.display = 'block'; inp.focus(); return; }
          done(v);
        } else done(true);
      }
      function onKey(e) {
        if (e.key === 'Escape') { e.stopPropagation(); done(inp ? null : false); }
        else if (e.key === 'Enter' && !(inp && inp.tagName === 'TEXTAREA' && !e.ctrlKey)) { e.preventDefault(); submit(); }
        else if (e.key === 'Tab') {
          var f = dlg.querySelectorAll('button,input,textarea'); if (!f.length) return;
          var first = f[0], last = f[f.length - 1];
          if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
          else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
        }
      }
      ok.onclick = submit; no.onclick = function () { done(inp ? null : false); };
      bd.addEventListener('mousedown', function (e) { if (e.target === bd) done(inp ? null : false); });
      document.addEventListener('keydown', onKey, true);
      bd.appendChild(dlg); document.body.appendChild(bd);
      (inp || (opts.danger ? no : ok)).focus();
    });
  }
  function confirmBox(a, b) {
    var o = typeof a === 'object' ? a : { title: 'تأكيد', message: a };
    if (b) for (var k in b) o[k] = b[k];
    return dialog(o);
  }
  function promptBox(o) { o = o || {}; o.input = true; o.okText = o.okText || 'حفظ'; return dialog(o); }
  function alertBox(msg, type) { return dialog({ title: type === 'error' ? 'تعذر إتمام العملية' : 'تنبيه', message: msg, okText: 'حسناً', cancelText: 'إغلاق', icon: type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info', danger: type === 'error' }); }

  /* ---------- data-confirm على الفورمات والأزرار ---------- */
  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (!(f instanceof HTMLFormElement)) return;
    if (f.dataset.confirmed === '1') { f.dataset.confirmed = ''; finishSubmit(f, e.submitter); return; }
    var msg = f.getAttribute('data-confirm');
    if (msg) {
      e.preventDefault();
      var sub = e.submitter;
      confirmBox({ title: f.getAttribute('data-confirm-title') || 'تأكيد الإجراء', message: msg, danger: f.hasAttribute('data-danger'), okText: f.getAttribute('data-confirm-ok') || 'نعم، متأكد' }).then(function (ok) {
        if (!ok) return;
        f.dataset.confirmed = '1';
        if (f.requestSubmit) f.requestSubmit(sub || undefined); else { addCsrfInput(f); f.submit(); }
      });
      return;
    }
    finishSubmit(f, e.submitter);
  }, true);
  function finishSubmit(f, sub) {
    addCsrfInput(f);
    if (f.hasAttribute('data-no-busy')) return;
    var btns = f.querySelectorAll('button[type=submit],button:not([type])');
    setTimeout(function () { btns.forEach(function (b) { b.disabled = true; b.classList.add('ui-busy'); }); }, 0);
  }
  window.addEventListener('pageshow', function () {
    document.querySelectorAll('button.ui-busy').forEach(function (b) { b.disabled = false; b.classList.remove('ui-busy'); });
  });

  /* ---------- ملاحظات إرشادية قابلة للإخفاء ---------- */
  function initNotes() {
    document.querySelectorAll('.ui-note[data-note-id]').forEach(function (n) {
      var id = 'ui_note_' + n.getAttribute('data-note-id');
      try { if (localStorage.getItem(id)) { n.style.display = 'none'; return; } } catch (e) {}
      if (n.querySelector('.n-x')) return;
      var x = el('button', 'n-x', '×'); x.setAttribute('aria-label', 'إخفاء الملاحظة'); x.type = 'button';
      x.onclick = function () { n.style.display = 'none'; try { localStorage.setItem(id, '1'); } catch (e) {} };
      n.appendChild(x);
    });
  }
  function resetNotes() {
    try { Object.keys(localStorage).forEach(function (k) { if (k.indexOf('ui_note_') === 0) localStorage.removeItem(k); }); } catch (e) {}
    document.querySelectorAll('.ui-note[data-note-id]').forEach(function (n) { n.style.display = ''; });
  }

  /* ---------- علامات الاستفهام (تلميحات) ---------- */
  document.addEventListener('click', function (e) {
    var q = e.target.closest ? e.target.closest('.ui-q') : null;
    document.querySelectorAll('.ui-q.show').forEach(function (x) { if (x !== q) x.classList.remove('show'); });
    if (q) { q.classList.toggle('show'); e.preventDefault(); }
  });

  /* ---------- جولة تعريفية ---------- */
  var tourState = null;
  function endTour(key, mark) {
    if (!tourState) return;
    tourState.layer.remove(); window.removeEventListener('resize', tourState.onResize);
    document.removeEventListener('keydown', tourState.onKey, true);
    if (key && mark) try { localStorage.setItem('ui_tour_' + key, '1'); } catch (e) {}
    tourState = null;
  }
  function tour(steps, opts) {
    opts = opts || {};
    if (tourState) endTour();
    var i = 0, layer = el('div', 'ui-tour-layer'), hole = el('div', 'ui-tour-hole'), card = el('div', 'ui-tour-card');
    layer.appendChild(hole); layer.appendChild(card); document.body.appendChild(layer);
    function visible(n) { return n && n.getClientRects().length > 0; }
    function place() {
      var s = steps[i], t = s.sel ? document.querySelector(s.sel) : null;
      if (!visible(t)) t = null;
      var vw = window.innerWidth, vh = window.innerHeight, cw = card.offsetWidth, ch = card.offsetHeight;
      if (t) {
        t.scrollIntoView({ block: 'center', inline: 'nearest' });
        var r = t.getBoundingClientRect(), pad = 6;
        hole.style.display = 'block';
        hole.style.top = (r.top - pad) + 'px'; hole.style.left = (r.left - pad) + 'px';
        hole.style.width = (r.width + pad * 2) + 'px'; hole.style.height = (r.height + pad * 2) + 'px';
        var top = r.bottom + 14; if (top + ch > vh - 10) top = Math.max(10, r.top - ch - 14);
        var left = r.left + r.width / 2 - cw / 2; left = Math.min(Math.max(12, left), vw - cw - 12);
        if (r.width < vw * 0.4 && (vw - r.right > cw + 20 || r.left > cw + 20)) {
          top = Math.min(Math.max(12, r.top + r.height / 2 - ch / 2), vh - ch - 12);
          left = (r.left > cw + 20) ? r.left - cw - 18 : r.right + 18;
        }
        card.style.top = top + 'px'; card.style.left = left + 'px';
      } else {
        hole.style.display = 'block'; hole.style.top = (vh / 2) + 'px'; hole.style.left = (vw / 2) + 'px'; hole.style.width = '0'; hole.style.height = '0';
        card.style.top = Math.max(12, (vh - ch) / 2) + 'px'; card.style.left = Math.max(12, (vw - cw) / 2) + 'px';
      }
    }
    function render() {
      var s = steps[i], last = i === steps.length - 1;
      if (s.before) try { s.before(); } catch (e) {}
      card.innerHTML = '<h4></h4><p></p><div class="ui-tour-foot"><span class="step"></span>' +
        (i > 0 ? '<button class="ui-btn" data-prev>' + tr('السابق') + '</button>' : '<button class="ui-tour-skip" data-skip>' + tr('تخطي') + '</button>') +
        '<button class="ui-btn primary" data-next></button></div>';
      card.querySelector('h4').textContent = tr(s.title || '');
      card.querySelector('p').textContent = tr(s.text || '');
      card.querySelector('.step').textContent = (i + 1) + ' / ' + steps.length;
      card.querySelector('[data-next]').textContent = tr(last ? 'ابدأ الشغل' : 'التالي');
      card.querySelector('[data-next]').onclick = function () { if (last) endTour(opts.key, true); else { i++; render(); } };
      var pv = card.querySelector('[data-prev]'); if (pv) pv.onclick = function () { i--; render(); };
      var sk = card.querySelector('[data-skip]'); if (sk) sk.onclick = function () { endTour(opts.key, true); };
      setTimeout(place, s.before ? 60 : 0);
      card.querySelector('[data-next]').focus();
    }
    var onResize = function () { place(); };
    var onKey = function (e) {
      if (e.key === 'Escape') endTour(opts.key, true);
      else if (e.key === 'ArrowLeft') { e.preventDefault(); if (i < steps.length - 1) { i++; render(); } }
      else if (e.key === 'ArrowRight') { e.preventDefault(); if (i > 0) { i--; render(); } }
    };
    window.addEventListener('resize', onResize); document.addEventListener('keydown', onKey, true);
    tourState = { layer: layer, onResize: onResize, onKey: onKey };
    render();
  }
  function tourOnce(key, steps, delay) {
    var seen = false; try { seen = !!localStorage.getItem('ui_tour_' + key); } catch (e) {}
    if (!seen) setTimeout(function () { tour(steps, { key: key }); }, delay || 700);
  }
  function tourReset(key) { try { localStorage.removeItem('ui_tour_' + key); } catch (e) {} }

  /* ---------- تشغيل ---------- */
  function boot() {
    initNotes();
    if (LANG !== 'ar') {
      trNode(document.body);
      new MutationObserver(function (ms) { ms.forEach(function (m) {
        m.addedNodes.forEach(trNode);
        if (m.type === 'characterData') fixText(m.target);
      }); }).observe(document.body, { childList: true, subtree: true, characterData: true });
    }
    document.querySelectorAll('form').forEach(addCsrfInput);
    var fd = document.getElementById('flash-data');
    if (fd) {
      try {
        JSON.parse(fd.textContent || '[]').forEach(function (f, n) {
          setTimeout(function () { toast(f.m, f.c === 'error' ? 'error' : (f.c === 'warn' ? 'warn' : 'success')); }, n * 180);
        });
      } catch (e) {}
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

  window.UI = { t: tr, toast: toast, confirm: confirmBox, prompt: promptBox, alert: alertBox, esc: esc, tour: tour, tourOnce: tourOnce, tourReset: tourReset, resetNotes: resetNotes, csrf: CSRF };
})();
