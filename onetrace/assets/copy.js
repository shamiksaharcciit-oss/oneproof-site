/* Adds a "Copy" button to each code block. Without scripts the page works the same, and the
   code stays selectable. Nothing is loaded and nothing is sent. */
(function () {
  if (!document.querySelectorAll) return;
  var blocks = document.querySelectorAll(".code");
  for (var i = 0; i < blocks.length; i++) {
    (function (block) {
      var pre = block.querySelector("pre");
      if (!pre) return;
      var button = document.createElement("button");
      button.type = "button";
      button.className = "copy";
      button.textContent = "Copy";
      button.setAttribute("aria-label", "Copy this code");
      button.addEventListener("click", function () {
        var text = pre.innerText;
        var done = function () {
          button.textContent = "Copied";
          setTimeout(function () { button.textContent = "Copy"; }, 1500);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, function () { select(pre); });
        } else {
          select(pre);
        }
      });
      block.appendChild(button);
    })(blocks[i]);
  }
  function select(el) {
    var range = document.createRange();
    range.selectNodeContents(el);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }
})();
