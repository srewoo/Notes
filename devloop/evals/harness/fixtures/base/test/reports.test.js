const test = require('node:test');
const assert = require('node:assert');
const { getReport, listReports } = require('../src/reports');

test('getReport trims the title', () => {
  assert.equal(getReport('r1').title, 'Quarterly sales');
});

test('getReport returns null for a missing id', () => {
  assert.equal(getReport('nope'), null);
});

test('listReports lists every report', () => {
  assert.equal(listReports().length, 2);
});
