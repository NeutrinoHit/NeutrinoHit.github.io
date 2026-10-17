(function () {
  const scriptElement = document.currentScript;
  const scriptUrl = scriptElement && scriptElement.src;
  const assetBaseUrl = scriptUrl
    ? new URL(".", scriptUrl).href
    : "https://neutrinohit.github.io/assets/reveal/";
  const contextHomeUrl = scriptElement && scriptElement.dataset.contextHome
    ? new URL(scriptElement.dataset.contextHome, window.location.href).href
    : null;

  const config = {
    homeUrl: "https://neutrinohit.github.io/",
    contextHomeUrl,
    contextHomeLabel: scriptElement && scriptElement.dataset.contextHomeLabel
      ? scriptElement.dataset.contextHomeLabel
      : "Главная страница материалов",
    contextHomeShort: scriptElement && scriptElement.dataset.contextHomeShort
      ? scriptElement.dataset.contextHomeShort
      : null,
    mathJaxRenderer: scriptElement && scriptElement.dataset.mathjaxRenderer
      ? scriptElement.dataset.mathjaxRenderer
      : "CommonHTML",
    logoUrl: new URL("dvnlogo.png", assetBaseUrl).href,
    telegramUrl: "https://t.me/NeutrinoHit",
    youtubeUrl: "https://www.youtube.com/@dmitrynaumov6099/"
  };

  function injectStyles() {
    if (document.getElementById("nh-reveal-footer-style")) return;

    const style = document.createElement("style");
    style.id = "nh-reveal-footer-style";
    style.textContent = `
      .nh-slide-footer {
        position: fixed;
        right: 5.2rem;
        bottom: 0.9rem;
        z-index: 2147483647;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        pointer-events: auto;
        font: 600 14px/1.2 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      .nh-slide-footer a {
        text-decoration: none !important;
      }

      .nh-footer-logo-link,
      .nh-footer-link {
        display: inline-grid;
        place-items: center;
        border: 1px solid rgba(255, 255, 255, 0.35);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        color: #f2f2f2;
        transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
      }

      .nh-footer-logo-link {
        width: 38px;
        height: 38px;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.95);
      }

      .nh-footer-link {
        width: 38px;
        height: 38px;
      }

      .nh-footer-course {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        height: 38px;
        padding: 0 15px 0 12px;
        border: 1px solid rgba(255, 255, 255, 0.9);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.95);
        color: #1d2b36 !important;
        font: 700 15px/1 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        white-space: nowrap;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
        transition: background 0.15s ease, transform 0.15s ease;
      }

      .nh-footer-course:hover {
        background: #ffffff;
        transform: translateY(-1px);
      }

      .nh-footer-course kbd {
        padding: 1px 5px;
        background: transparent !important;
        box-shadow: none !important;
        border: 1px solid rgba(29, 43, 54, 0.3);
        border-radius: 4px;
        color: #53616f;
        font: 600 11px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
      }

      .nh-footer-logo-link:hover,
      .nh-footer-link:hover {
        border-color: rgba(255, 255, 255, 0.72);
        background: rgba(255, 255, 255, 0.16);
        transform: translateY(-1px);
      }

      .nh-footer-logo-link:hover {
        background: rgba(255, 255, 255, 1);
      }

      .nh-slide-footer .slide-logo,
      .nh-footer-logo {
        position: static !important;
        display: block !important;
        width: 32px !important;
        height: 32px !important;
        max-width: 32px !important;
        max-height: 32px !important;
        margin: 0 !important;
        object-fit: contain !important;
        inset: auto !important;
        transform: none !important;
        opacity: 1 !important;
      }

      .nh-footer-link svg {
        width: 26px;
        height: 26px;
        display: block;
      }

      .nh-footer-link circle,
      .nh-footer-link rect {
        fill: currentColor;
      }

      .nh-footer-link path {
        fill: #000000;
      }

      @media (max-width: 720px) {
        .nh-slide-footer {
          right: 1rem;
          bottom: 3.3rem;
        }

        .nh-footer-course kbd {
          display: none;
        }
      }

      @media print {
        .nh-slide-footer {
          display: none !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function iconLink(url, label, svg, openInNewTab = true) {
    const link = document.createElement("a");
    link.className = "nh-footer-link";
    link.href = url;
    link.title = label;
    if (openInNewTab) {
      link.target = "_blank";
      link.rel = "noopener";
    }
    link.setAttribute("aria-label", label);
    link.innerHTML = svg;
    return link;
  }

  const COURSE_KEY = "u";

  function pageIsRussian() {
    return (document.documentElement.lang || "").toLowerCase().startsWith("ru");
  }

  function courseLink() {
    const ru = pageIsRussian();
    const link = document.createElement("a");
    link.className = "nh-footer-course";
    link.href = config.contextHomeUrl;
    const hint = ru ? `${config.contextHomeLabel} (клавиша U)` : `${config.contextHomeLabel} (key U)`;
    link.title = hint;
    link.setAttribute("aria-label", hint);
    link.append("← " + (config.contextHomeShort || (ru ? "Курс" : "Course")));
    const kbd = document.createElement("kbd");
    kbd.textContent = "U";
    link.appendChild(kbd);
    return link;
  }

  // U returns to the course page; Reveal leaves this key unbound
  // (Esc and O open the overview, H/J/K/L navigate).
  function bindCourseKey() {
    if (!config.contextHomeUrl || window.__neutrinohitCourseKey) return;
    window.__neutrinohitCourseKey = true;
    document.addEventListener("keydown", (event) => {
      if (event.key.toLowerCase() !== COURSE_KEY) return;
      if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
      const target = event.target;
      if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
      event.preventDefault();
      window.location.href = config.contextHomeUrl;
    });
    if (window.Reveal && typeof window.Reveal.registerKeyboardShortcut === "function") {
      window.Reveal.registerKeyboardShortcut("U", pageIsRussian() ? "К странице курса" : "Back to the course page");
    }
  }

  function logoLink() {
    const link = document.createElement("a");
    link.className = "nh-footer-logo-link";
    link.href = config.homeUrl;
    link.target = "_blank";
    link.rel = "noopener";
    link.title = "NeutrinoHit";
    link.setAttribute("aria-label", "NeutrinoHit");

    const existingLogo = document.querySelector(".reveal .slide-logo, .slide-logo");
    if (existingLogo) {
      link.appendChild(existingLogo);
      return link;
    }

    const img = document.createElement("img");
    img.className = "nh-footer-logo";
    img.src = config.logoUrl;
    img.alt = "NeutrinoHit";
    link.appendChild(img);
    return link;
  }

  function buildFooter() {
    if (!document.querySelector(".reveal, #stageArea")) return;
    if (document.querySelector(".nh-slide-footer")) return;

    injectStyles();

    const footer = document.createElement("nav");
    footer.className = "nh-slide-footer";
    footer.setAttribute("aria-label", "NeutrinoHit links");
    if (config.contextHomeUrl) {
      footer.appendChild(courseLink());
      bindCourseKey();
    }
    footer.appendChild(logoLink());
    footer.appendChild(iconLink(
      config.telegramUrl,
      "Telegram",
      '<svg viewBox="0 0 48 48" role="img" aria-hidden="true"><circle cx="24" cy="24" r="21"></circle><path d="M38.8 12.1 33.4 37c-.4 1.8-1.5 2.3-3.1 1.4l-8.5-6.3-4.1 4c-.5.5-.8.8-1.7.8l.6-8.7 15.9-14.4c.7-.6-.2-1-1.1-.4L11.7 26.8l-8.5-2.7c-1.8-.6-1.8-1.8.4-2.6L36.7 8.7c1.5-.6 2.8.3 2.1 3.4z"></path></svg>'
    ));
    footer.appendChild(iconLink(
      config.youtubeUrl,
      "YouTube",
      '<svg viewBox="0 0 48 48" role="img" aria-hidden="true"><rect x="6" y="12" width="36" height="24" rx="8"></rect><path d="M21 18l12 6-12 6z"></path></svg>'
    ));

    document.body.appendChild(footer);
  }

  // The RevealJS MathJax2 plugin typesets only the slides; slide titles
  // copied into the slide menu would otherwise show raw TeX.
  function typesetSlideMenu() {
    const hub = window.MathJax && window.MathJax.Hub;
    const menu = document.querySelector(".slide-menu-wrapper");
    if (hub && menu) hub.Queue(["Typeset", hub, menu]);
  }

  // MathJax measures the surrounding font when it typesets. Formulas on a
  // slide or tab that is not displayed at that moment come out at half size,
  // so the visible part of a slide is rendered again the first time it is shown.
  const renderedWhileShown = new WeakSet();

  function visibleTabPanels(slide) {
    return Array.from(slide.querySelectorAll('[role="tabpanel"]'))
      .filter((panel) => !panel.hidden && panel.offsetParent !== null);
  }

  function isShown(part) {
    const slide = window.Reveal && window.Reveal.getCurrentSlide();
    return Boolean(slide && part.isConnected && (part === slide || slide.contains(part))
      && part.offsetParent !== null && !part.closest("[hidden]"));
  }

  // Visibility is checked when the queued job runs, not when it is queued:
  // a slide or tab left before MathJax reaches it keeps its mark unset and
  // is rendered again the next time it is shown.
  function rerenderIfShown(part) {
    const hub = window.MathJax && window.MathJax.Hub;
    if (!hub || renderedWhileShown.has(part) || !isShown(part)) return null;
    renderedWhileShown.add(part);
    if (part.matches(".slide, section")) {
      // The whole slide is typeset again: its visible tabs come out right,
      // its hidden tabs come out wrong and must be redone when opened.
      part.querySelectorAll('[role="tabpanel"]').forEach((panel) => renderedWhileShown.delete(panel));
      visibleTabPanels(part).forEach((panel) => renderedWhileShown.add(panel));
    }
    if (!part.querySelector(".MathJax_CHTML, .MathJax_SVG, .MathJax")) return null;
    return hub.Rerender(part);
  }

  function rerenderShownMath() {
    const hub = window.MathJax && window.MathJax.Hub;
    const slide = window.Reveal && typeof window.Reveal.getCurrentSlide === "function"
      ? window.Reveal.getCurrentSlide()
      : null;
    if (!hub || !slide) return;
    [slide, ...visibleTabPanels(slide)].forEach((part) => hub.Queue(() => rerenderIfShown(part)));
    hub.Queue(() => window.Reveal.layout());
  }

  function watchShownMath() {
    window.Reveal.on("slidechanged", rerenderShownMath);
    // Capture phase: the click on a tab does not always bubble to the document.
    document.addEventListener("click", (event) => {
      if (event.target.closest('[role="tab"]')) window.setTimeout(rerenderShownMath, 0);
    }, true);
    rerenderShownMath();
  }

  function configureMathJax() {
    if (window.__neutrinohitMathJaxConfigured) return;
    const setRenderer = config.mathJaxRenderer && config.mathJaxRenderer !== "default";

    const revealElement = document.querySelector(".reveal");
    if (revealElement) revealElement.addEventListener("menu-ready", typesetSlideMenu);

    let attempts = 0;
    const maxAttempts = 120;
    const interval = window.setInterval(() => {
      attempts += 1;
      const hub = window.MathJax && window.MathJax.Hub;
      if (!hub) {
        if (attempts >= maxAttempts) window.clearInterval(interval);
        return;
      }

      window.clearInterval(interval);
      window.__neutrinohitMathJaxConfigured = true;

      try {
        if (setRenderer) {
          hub.Queue(["setRenderer", hub, config.mathJaxRenderer]);
          hub.Queue(["Rerender", hub]);
        }
        typesetSlideMenu();
        hub.Queue(() => {
          if (window.Reveal && typeof window.Reveal.layout === "function") {
            window.Reveal.layout();
            watchShownMath();
          }
        });
      } catch (error) {
        console.warn("NeutrinoHit: could not configure MathJax renderer", error);
      }
    }, 100);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      buildFooter();
      configureMathJax();
    }, { once: true });
  } else {
    buildFooter();
    configureMathJax();
  }
})();
