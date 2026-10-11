'use strict';
const field = document.getElementById('source-filter');
if (field) {
  const rows = Array.from(document.querySelectorAll('#source-table tbody tr'));
  const count = document.getElementById('filter-count');
  const update = () => {
    const query = field.value.toLocaleLowerCase().trim();
    let visible = 0;
    rows.forEach(row => {
      row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
      if (!row.hidden) visible++;
    });
    count.textContent = `${visible} of ${rows.length} sources shown`;
  };
  field.addEventListener('input', update);
  update();
}
