/* Blog behaviour: theme toggle, reading progress, contents, copy buttons.

   Syntax highlighting is Prism's job, not ours. An earlier version of this
   file hand-rolled a regex highlighter, which corrupted its own output the
   moment a Python keyword appeared inside a class attribute it had just
   emitted. Prism tokenises properly; blog.css colours the tokens from the
   theme palette.

   Pico reads `data-theme` off <html>. With the attribute absent it follows the
   OS, which is the third state of the toggle. The initial value is applied by
   an inline script in <head> so the page never flashes the wrong theme. */

(function () {
  "use strict";

  var root = document.documentElement;
  var KEY = "blog-theme";
  var ORDER = ["system", "light", "dark"];
  var LABEL = { system: "Auto", light: "Light", dark: "Dark" };

  // ------------------------------------------------------------- theme

  function stored() {
    try { return localStorage.getItem(KEY) || "system"; } catch (e) { return "system"; }
  }

  function apply(mode) {
    if (mode === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", mode);
    try { localStorage.setItem(KEY, mode); } catch (e) { /* private browsing */ }
    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.textContent = LABEL[mode];
      btn.setAttribute("aria-label", "Theme: " + LABEL[mode] + ". Activate to change.");
    }
  }

  function initTheme() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    apply(stored());
    btn.addEventListener("click", function () {
      apply(ORDER[(ORDER.indexOf(stored()) + 1) % ORDER.length]);
    });
  }

  // ------------------------------------------------------------- progress

  function initProgress() {
    var bar = document.getElementById("progress");
    var article = document.querySelector("article");
    if (!bar || !article) return;
    var queued = false;

    function update() {
      var span = article.offsetHeight - window.innerHeight;
      var pct = span <= 0 ? 0 : (window.scrollY - article.offsetTop) / span;
      bar.style.width = Math.max(0, Math.min(1, pct)) * 100 + "%";
      queued = false;
    }
    addEventListener("scroll", function () {
      if (!queued) { queued = true; requestAnimationFrame(update); }
    }, { passive: true });
    addEventListener("resize", update, { passive: true });
    update();
  }

  // ------------------------------------------------------------- contents

  function slug(s) {
    return s.toLowerCase().replace(/[^\w\s-]/g, "").trim()
            .replace(/\s+/g, "-").slice(0, 60);
  }

  function initToc() {
    var host = document.getElementById("toc");
    if (!host) return;
    var heads = document.querySelectorAll("article section > h2, article .takeaways > h2");
    if (heads.length < 3) { host.remove(); return; }

    var ol = document.createElement("ol");
    Array.prototype.forEach.call(heads, function (h) {
      if (!h.id) h.id = slug(h.textContent);
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = "#" + h.id;
      a.textContent = h.textContent;
      li.appendChild(a);
      ol.appendChild(li);
    });
    host.appendChild(ol);
  }

  // ------------------------------------------------------------- code

  function initCode() {
    Array.prototype.forEach.call(document.querySelectorAll("pre > code"), function (code) {
      var text = code.textContent;

      // tag Python blocks for Prism; leave the plain URL block alone
      if (/\b(import|def|print|from|lambda)\b/.test(text) && !code.className) {
        code.className = "language-python";
      }

      var btn = document.createElement("button");
      btn.className = "copy-btn";
      btn.type = "button";
      btn.textContent = "Copy";
      btn.addEventListener("click", function () {
        navigator.clipboard.writeText(text).then(function () {
          btn.textContent = "Copied";
          setTimeout(function () { btn.textContent = "Copy"; }, 1400);
        }, function () { btn.textContent = "Failed"; });
      });
      code.parentNode.appendChild(btn);
    });

    if (window.Prism) window.Prism.highlightAll();
  }

  // -------------------------------------------------------------

  function boot() { initTheme(); initProgress(); initToc(); initCode(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
