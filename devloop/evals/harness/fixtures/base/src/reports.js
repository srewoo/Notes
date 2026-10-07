const store = require('./store');
const { formatTitle } = require('./format');
const { emitUsage } = require('./usage');

function getReport(id) {
  const report = store.get(id);
  if (!report) return null;
  emitUsage({ action: 'report.view', id });
  return { ...report, title: formatTitle(report.title) };
}

function listReports() {
  return store.all().map((r) => ({ id: r.id, title: formatTitle(r.title) }));
}

module.exports = { getReport, listReports };
