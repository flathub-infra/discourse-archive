// Discourse Static Archive — Minimal JS
// Only for mobile nav toggle and time formatting

(function () {
  "use strict";

  // Mobile navigation toggle
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".site-nav");

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var expanded = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", expanded);
    });

    // Close nav when clicking outside
    document.addEventListener("click", function (e) {
      if (!toggle.contains(e.target) && !nav.contains(e.target)) {
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }
})();
