let positions = {};
let W = 700, H = 340;
let graphData = { nodes: ["A", "B"] };

function ensurePositions() {
  const nodes = graphData.nodes;
  if (!nodes.length) return;

  const known = new Set(Object.keys(positions));
  const incoming = new Set(nodes);

  for (const id of known) {
    if (!incoming.has(id)) delete positions[id];
  }

  const newNodes = nodes.filter(n => !known.has(n));
  if (!newNodes.length) return;

  const existing = Object.values(positions);
  if (existing.length) {
    const cx = existing.reduce((s, p) => s + p.x, 0) / existing.length;
    const cy = existing.reduce((s, p) => s + p.y, 0) / existing.length;
    newNodes.forEach((id, i) => {
      const angle = (2 * Math.PI * i) / Math.max(newNodes.length, 1);
      const r = 80 + Math.random() * 60;
      positions[id] = {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      };
    });
  } else {
    const n = nodes.length;
    const cx = W * 0.5, cy = H * 0.5;
    const r = Math.min(W, H) * 0.35;
    nodes.forEach((id, i) => {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2;
      positions[id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });
  }
}

// simulate corrupted session storage
positions = { "A": {x: 0, y: 0}, "B": {x: 0, y: 0} };
ensurePositions();
console.log("After corrupted:", positions);

// simulate fresh
positions = {};
ensurePositions();
console.log("After fresh:", positions);
