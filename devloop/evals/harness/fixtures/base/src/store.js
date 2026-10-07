const reports = new Map([
  ['r1', { id: 'r1', title: '  Quarterly sales ', rows: 120 }],
  ['r2', { id: 'r2', title: 'Churn by region', rows: 48 }],
]);

function get(id) {
  return reports.get(id) ?? null;
}

function all() {
  return [...reports.values()];
}

module.exports = { get, all };
