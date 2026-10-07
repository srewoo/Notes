const events = [];

function emitUsage(event) {
  events.push({ ...event, at: Date.now() });
}

module.exports = { emitUsage, events };
