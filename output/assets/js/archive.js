// Discourse Static Archive — Minimal JS
// Theme preference and mobile navigation

(function () {
  "use strict";

  var themeKey = "archive-theme";
  var root = document.documentElement;
  var chooser;

  function applyTheme(theme) {
    if (theme !== "light" && theme !== "dark") theme = "system";
    if (theme === "system") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
    if (chooser) chooser.value = theme;
  }

  // Storage may be unavailable (for example, in private or restricted contexts).
  try {
    applyTheme(localStorage.getItem(themeKey));
  } catch (e) {
    applyTheme("system");
  }

  var header = document.querySelector(".header-inner");
  if (header) {
    chooser = document.createElement("select");
    chooser.className = "theme-chooser";
    chooser.setAttribute("aria-label", "Color theme");
    [["system", "System"], ["light", "Light"], ["dark", "Dark"]].forEach(function (theme) {
      var option = document.createElement("option");
      option.value = theme[0];
      option.textContent = theme[1];
      chooser.appendChild(option);
    });
    chooser.value = root.getAttribute("data-theme") || "system";
    chooser.addEventListener("change", function () {
      applyTheme(chooser.value);
      try {
        localStorage.setItem(themeKey, chooser.value);
      } catch (e) {
        // The selection still works for this page without persistent storage.
      }
    });
    header.appendChild(chooser);
  }

  window.addEventListener("storage", function (e) {
    if (e.key === themeKey || e.key === null) applyTheme(e.newValue);
  });

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
