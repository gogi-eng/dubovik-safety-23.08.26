(function () {
  const STORAGE_KEY = "dubovik_lang";
  let currentLang = localStorage.getItem(STORAGE_KEY) || "ru";

  function t(key) {
    const pack = window.DUBOVIK_I18N[currentLang] || window.DUBOVIK_I18N.ru;
    return pack[key] || window.DUBOVIK_I18N.ru[key] || key;
  }

  function applyLang(lang) {
    currentLang = lang === "pt" ? "pt" : "ru";
    localStorage.setItem(STORAGE_KEY, currentLang);
    document.documentElement.lang = currentLang;

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      el.textContent = t(key);
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.placeholder = t(el.getAttribute("data-i18n-placeholder"));
    });

    document.title = t("pageTitle");
    const meta = document.querySelector('meta[name="description"]');
    if (meta) meta.setAttribute("content", t("metaDescription"));

    const btn = document.getElementById("lang-toggle");
    if (btn) btn.textContent = t("langSwitch");
  }

  function initSectionVideos() {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    if (prefersReduced || isMobile) {
      document.querySelectorAll(".section-video").forEach((video) => {
        video.pause();
        video.removeAttribute("autoplay");
      });
      return;
    }
    document.querySelectorAll(".section-video").forEach((video) => {
      const play = () => video.play().catch(() => {});
      if (video.readyState >= 2) play();
      else video.addEventListener("loadeddata", play, { once: true });
    });
  }

  function initAboutPhotoCrossfade() {
    const wrap = document.getElementById("about-photo");
    if (!wrap) return;

    const imgs = Array.from(wrap.querySelectorAll(".about-photo__img"));
    if (imgs.length < 2) return;

    const markReady = () => {
      if (imgs.every((img) => img.complete && img.naturalWidth > 0)) {
        wrap.classList.add("about-photo--ready");
      }
    };

    imgs.forEach((img) => {
      if (img.complete) return;
      img.addEventListener("load", markReady, { once: true });
      img.addEventListener("error", markReady, { once: true });
    });
    markReady();
  }

  document.addEventListener("DOMContentLoaded", () => {
    applyLang(currentLang);
    initSectionVideos();
    initAboutPhotoCrossfade();

    const langBtn = document.getElementById("lang-toggle");
    if (langBtn) {
      langBtn.addEventListener("click", () => {
        applyLang(currentLang === "ru" ? "pt" : "ru");
      });
    }

    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener("click", (e) => {
        e.preventDefault();
        const target = document.querySelector(anchor.getAttribute("href"));
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.style.opacity = "1";
            entry.target.style.transform = "translateY(0)";
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -100px 0px" }
    );

    document
      .querySelectorAll(".service-card, .step, .why-item, .stat-item, .gallery-item")
      .forEach((el) => {
        el.style.opacity = "0";
        el.style.transform = "translateY(20px)";
        el.style.transition = "opacity 0.6s ease-out, transform 0.6s ease-out";
        observer.observe(el);
      });

    const phoneInput = document.getElementById("phone");
    if (phoneInput) {
      phoneInput.addEventListener("input", (e) => {
        let value = e.target.value.replace(/\D/g, "");
        if (value.length > 0) {
          if (value.startsWith("375")) value = value.substring(3);
          let formatted = "+375";
          if (value.length > 0) {
            formatted += " (" + value.substring(0, 2);
            if (value.length > 2) {
              formatted += ") " + value.substring(2, 5);
              if (value.length > 5) {
                formatted += "-" + value.substring(5, 7);
                if (value.length > 7) formatted += "-" + value.substring(7, 9);
              }
            }
          }
          e.target.value = formatted;
        }
      });
    }

    const form = document.getElementById("contact-form");
    const statusEl = document.getElementById("form-status");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const submitBtn = form.querySelector('button[type="submit"]');
        const payload = {
          name: form.name.value.trim(),
          phone: form.phone.value.trim(),
          message: form.message.value.trim(),
          lang: currentLang,
          website: form.website ? form.website.value : "",
        };
        submitBtn.disabled = true;
        submitBtn.textContent = t("formSending");
        if (statusEl) statusEl.textContent = "";
        try {
          const resp = await fetch("/api/contact", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const data = await resp.json();
          if (resp.ok && data.ok) {
            if (statusEl) {
              statusEl.style.color = "#2ecc71";
              statusEl.textContent = t("formSuccess");
            }
            form.reset();
          } else {
            throw new Error(data.error || "fail");
          }
        } catch (err) {
          if (statusEl) {
            statusEl.style.color = "#ffb4b4";
            statusEl.textContent = t("formError");
          }
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = t("formSubmit");
        }
      });
    }
  });
})();
