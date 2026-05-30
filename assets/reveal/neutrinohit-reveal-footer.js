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
    footer.appendChild(logoLink());
    if (config.contextHomeUrl) {
      footer.appendChild(iconLink(
        config.contextHomeUrl,
        config.contextHomeLabel,
        '<svg viewBox="0 0 48 48" role="img" aria-hidden="true"><rect x="7" y="8" width="34" height="32" rx="4"></rect><path d="M15 15h18v3H15zm0 7h18v3H15zm0 7h12v3H15z"></path></svg>',
        false
      ));
    }
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildFooter, { once: true });
  } else {
    buildFooter();
  }
})();
