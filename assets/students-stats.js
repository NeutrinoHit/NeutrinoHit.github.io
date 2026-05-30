(function () {
  const stats = document.querySelector("[data-student-thesis-stats]");
  if (!stats) return;

  const rows = Array.from(document.querySelectorAll(".thesis-list-supervised .thesis-row"));
  const counts = rows.reduce(
    (result, row) => {
      result.total += 1;
      const category = row.dataset.thesisCategory;
      if (category in result) result[category] += 1;
      return result;
    },
    { total: 0, phd: 0, diploma: 0 }
  );

  Object.entries(counts).forEach(([category, value]) => {
    const output = stats.querySelector(`[data-thesis-count="${category}"]`);
    if (output) output.textContent = String(value);
  });
})();
