(function () {
  const stats = document.querySelector("[data-student-thesis-stats]");
  if (!stats) return;

  const rows = Array.from(document.querySelectorAll(".thesis-list-supervised .thesis-row"));
  const list = document.querySelector(".thesis-list-supervised");
  rows
    .sort((left, right) => {
      const leftYear = Number(left.querySelector(".thesis-year")?.textContent || 0);
      const rightYear = Number(right.querySelector(".thesis-year")?.textContent || 0);
      return rightYear - leftYear;
    })
    .forEach((row) => list.appendChild(row));

  const counts = rows.reduce(
    (result, row) => {
      result.total += 1;
      const category = row.dataset.thesisCategory;
      if (category in result) result[category] += 1;
      return result;
    },
    { total: 0, phd: 0, master: 0, bachelor: 0, diploma: 0 }
  );

  Object.entries(counts).forEach(([category, value]) => {
    const output = stats.querySelector(`[data-thesis-count="${category}"]`);
    if (output) output.textContent = String(value);
  });
})();
