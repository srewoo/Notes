const { getReport } = require('./reports');

// GET /reports/:id
function handleGetReport(id) {
  const report = getReport(id);
  return { status: 200, body: report };
}

module.exports = { handleGetReport };
