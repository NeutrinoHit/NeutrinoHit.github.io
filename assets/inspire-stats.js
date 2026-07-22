(() => {
  const container = document.querySelector("[data-inspire-stats]");

  if (!container) {
    return;
  }

  const isEnglish = String(document.documentElement.lang || "").toLowerCase().startsWith("en");
  const endpoint =
    "https://inspirehep.net/api/literature/facets?facet_name=citation-summary&q=a%20Dmitry.V.Naumov.1";
  const formatNumber = new Intl.NumberFormat(isEnglish ? "en-US" : "ru-RU").format;
  const setText = (selector, value) => {
    const element = container.querySelector(selector);

    if (element) {
      element.textContent = value;
    }
  };

  fetch(endpoint, { headers: { Accept: "application/json" } })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Publication metrics request failed: ${response.status}`);
      }

      return response.json();
    })
    .then((data) => {
      const summary = data.aggregations.citation_summary;
      const citeable = summary.citations.buckets.all;

      setText("[data-inspire-papers]", formatNumber(data.hits.total.value));
      setText("[data-inspire-citations]", formatNumber(citeable.citations_count.value));
      setText("[data-inspire-h-index]", formatNumber(summary["h-index"].value.all));
      setText(
        "[data-inspire-status]",
        isEnglish ? "Publication metrics updated automatically." : "Публикационные метрики обновлены автоматически."
      );
    })
    .catch(() => {
      setText(
        "[data-inspire-status]",
        isEnglish
          ? "Fallback publication metrics are shown."
          : "Показаны резервные публикационные метрики."
      );
    });
})();
