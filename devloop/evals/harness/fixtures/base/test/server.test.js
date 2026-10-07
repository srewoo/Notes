const test = require('node:test');
const assert = require('node:assert');
const { handleGetReport } = require('../src/server');

test('GET /reports/:id returns the report', () => {
  const res = handleGetReport('r2');
  assert.equal(res.status, 200);
  assert.equal(res.body.title, 'Churn by region');
});
