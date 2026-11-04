// Tabs, copy buttons and the guide's step rail.
document.querySelectorAll('[data-tabs]').forEach(function (box) {
  var btns = box.querySelectorAll('[role=tab]');
  btns.forEach(function (b) {
    b.addEventListener('click', function () {
      btns.forEach(function (o) {
        var on = o === b;
        o.setAttribute('aria-selected', on ? 'true' : 'false');
        document.getElementById(o.getAttribute('aria-controls')).hidden = !on;
      });
    });
  });
});
document.querySelectorAll('.code').forEach(function (c) {
  var btn = c.querySelector('.copy');
  if (!btn) return;
  btn.addEventListener('click', function () {
    var pre = c.querySelector('pre');
    var text = Array.from(pre.childNodes).map(function (n) {
      return n.nodeType === 1 && n.classList.contains('c') ? '' : n.textContent;
    }).join('').replace(/[ \t]+$/gm, '').replace(/\n{3,}/g, '\n\n').trim();
    var done = function () { btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = 'Copy'; }, 1400); };
    try {
      navigator.clipboard.writeText(text).then(done, function () { select(pre); });
    } catch (e) { select(pre); }
  });
});
function select(el) {
  var r = document.createRange(); r.selectNodeContents(el);
  var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
}
(function () {
  var links = Array.from(document.querySelectorAll('.rail a[href^="#"]'));
  if (!links.length) return;
  var targets = links.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
  var ticking = false;
  function mark() {
    ticking = false;
    var line = window.innerHeight * 0.3, cur = 0;
    targets.forEach(function (t, i) { if (t && t.getBoundingClientRect().top <= line) cur = i; });
    links.forEach(function (a, i) { a.classList.toggle('on', i === cur); });
  }
  window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(mark); } }, { passive: true });
  mark();
})();
