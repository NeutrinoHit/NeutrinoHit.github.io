(() => {
  const token = "0b70c86ad46f4e9686d31b45b98002ac";
  const beaconSrc = "https://static.cloudflareinsights.com/beacon.min.js";
  const marker = "data-neutrinohit-cloudflare-web-analytics";
  const localHosts = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

  if (window.NEUTRINOHIT_DISABLE_ANALYTICS) {
    return;
  }

  if (window.location.protocol === "file:" || localHosts.has(window.location.hostname)) {
    return;
  }

  if (!token || token.startsWith("REPLACE_WITH_")) {
    return;
  }

  if (document.querySelector(`script[${marker}]`)) {
    return;
  }

  const script = document.createElement("script");
  script.defer = true;
  script.src = beaconSrc;
  script.dataset.cfBeacon = JSON.stringify({ token });
  script.dataset.neutrinohitCloudflareWebAnalytics = "1";
  document.head.appendChild(script);
})();
