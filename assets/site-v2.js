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
  var links = document.querySelectorAll('.rail a[href^="#"]');
  if (!links.length || !('IntersectionObserver' in window)) return;
  var map = {};
  links.forEach(function (a) { map[a.getAttribute('href').slice(1)] = a; });
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (e.isIntersecting && map[e.target.id]) {
        links.forEach(function (a) { a.classList.remove('on'); });
        map[e.target.id].classList.add('on');
      }
    });
  }, { rootMargin: '-30% 0px -60% 0px' });
  Object.keys(map).forEach(function (id) { var el = document.getElementById(id); if (el) io.observe(el); });
})();
