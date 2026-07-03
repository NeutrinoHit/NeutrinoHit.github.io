(() => {
  const localHosts = new Set(["localhost", "127.0.0.1", "::1"]);
  if (!localHosts.has(window.location.hostname)) return;

  const publicOrigin = "https://neutrinohit.github.io/";
  document.querySelectorAll(`a[href^="${publicOrigin}"]`).forEach((link) => {
    const url = new URL(link.href);
    const localHref = `${url.pathname}${url.search}${url.hash}`;
    const probe = `${url.pathname}${url.search}`;

    fetch(probe, { method: "HEAD" })
      .then((response) => {
        if (response.ok) link.href = localHref;
      })
      .catch(() => {});
  });
})();
