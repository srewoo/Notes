const { formatTitle } = require('./format');
const { emitUsage } = require('./usage');

function exportCsv(reports) {
  emitUsage({ action: 'report.export', count: reports.length });
  const lines = reports.map((r) => `${r.id},${formatTitle(r.title)}`);
  return ['id,title', ...lines].join('\n');
}

module.exports = { exportCsv };
