(() => {
  const localHosts = new Set(["localhost", "127.0.0.1", "::1"]);
  if (!localHosts.has(window.location.hostname)) return;

  const publicOrigin = "https://neutrinohit.github.io/";
  document.querySelectorAll(`a[href^="${publicOrigin}"]`).forEach((link) => {
    const url = new URL(link.href);
    link.href = `${url.pathname}${url.search}${url.hash}`;
  });
})();
