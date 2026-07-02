(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  /* ----------------------------------------------------------------------
   * Scroll-linked floating cans
   * Each [data-float] element gets a translateY + rotate driven by its
   * position relative to the viewport centre, layered on top of the
   * continuous CSS "bob" animation on its .float-inner child.
   * ------------------------------------------------------------------- */
  var floaters = Array.prototype.slice.call(document.querySelectorAll("[data-float]"));
  var ticking = false;

  function updateFloaters() {
    var vh = window.innerHeight;

    floaters.forEach(function (el) {
      var speed = parseFloat(el.getAttribute("data-speed")) || 0.15;
      var rotateMax = parseFloat(el.getAttribute("data-rotate")) || 8;
      var maxShift = 64; // cap the offset so far-off-screen elements can't be dragged into view
      var rect = el.getBoundingClientRect();
      var elCenter = rect.top + rect.height / 2;
      var delta = vh / 2 - elCenter;

      var translate = clamp(delta * speed, -maxShift, maxShift);
      var rotation = clamp((delta / vh) * rotateMax, -rotateMax, rotateMax);

      el.style.transform =
        "translateY(" + translate.toFixed(2) + "px) rotate(" + rotation.toFixed(2) + "deg)";
    });

    ticking = false;
  }

  function onScrollOrResize() {
    if (!ticking) {
      window.requestAnimationFrame(updateFloaters);
      ticking = true;
    }
  }

  if (floaters.length) {
    if (reduceMotion) {
      // Keep a static, gentle offset instead of a scroll-driven one.
      floaters.forEach(function (el) {
        el.style.transform = "translateY(0) rotate(0deg)";
      });
    } else {
      window.addEventListener("scroll", onScrollOrResize, { passive: true });
      window.addEventListener("resize", onScrollOrResize);
      updateFloaters();
    }
  }

  /* ----------------------------------------------------------------------
   * Header shadow once the page has scrolled
   * ------------------------------------------------------------------- */
  var header = document.getElementById("siteHeader");
  function onHeaderScroll() {
    if (!header) return;
    header.style.boxShadow = window.scrollY > 8 ? "0 8px 24px rgba(18,20,26,.08)" : "none";
  }
  window.addEventListener("scroll", onHeaderScroll, { passive: true });
  onHeaderScroll();

  /* ----------------------------------------------------------------------
   * Mobile menu toggle
   * ------------------------------------------------------------------- */
  var menuToggle = document.getElementById("menuToggle");
  var mainNav = document.getElementById("mainNav");

  if (menuToggle && mainNav) {
    menuToggle.addEventListener("click", function () {
      var isOpen = mainNav.classList.toggle("is-open");
      menuToggle.setAttribute("aria-expanded", String(isOpen));
    });

    mainNav.addEventListener("click", function (event) {
      if (event.target.tagName === "A") {
        mainNav.classList.remove("is-open");
        menuToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ----------------------------------------------------------------------
   * Newsletter signup — client-side only (no backend wired up yet)
   * ------------------------------------------------------------------- */
  var form = document.getElementById("signupForm");
  var status = document.getElementById("formStatus");
  var emailInput = document.getElementById("emailInput");

  if (form && status && emailInput) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();

      if (!emailInput.checkValidity()) {
        status.textContent = "Please pop in a valid email address.";
        status.style.color = "#c0264f";
        emailInput.focus();
        return;
      }

      status.textContent = "You're on the list — keep an eye on your inbox.";
      status.style.color = "";
      form.reset();
    });
  }

  /* ----------------------------------------------------------------------
   * Footer year
   * ------------------------------------------------------------------- */
  var yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());
})();
