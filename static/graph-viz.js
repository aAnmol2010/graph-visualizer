/**
 * graph-viz.js — Interactive canvas renderer for the Graph Visualizer.
 *
 * Features:
 *   • Click-to-add nodes (canvas click → prompt overlay)
 *   • Drag-to-connect edges (drag from node → node)
 *   • Drag-to-move nodes (drag node → new position)
 *   • Right-click context menu per node
 *   • Zoom / pan with mouse wheel and toolbar buttons
 *   • Step-by-step algorithm playback from server-returned order arrays
 *   • MST edge highlighting and SCC colour mapping
 *
 * All state is local to this module; communication with Flask is via
 * standard HTML form submissions (no fetch needed for the core flow).
 */

"use strict";

// -------------------------------------------------------------------------
// Scroll position persistence across form submissions
// -------------------------------------------------------------------------

window.addEventListener("beforeunload", () => {
  sessionStorage.setItem("graph-viz-scroll", window.scrollY);
});

const savedScroll = sessionStorage.getItem("graph-viz-scroll");
if (savedScroll !== null) {
  // Use a slight timeout to ensure DOM is fully laid out before scrolling
  setTimeout(() => window.scrollTo(0, parseInt(savedScroll, 10)), 0);
}

// -------------------------------------------------------------------------
// Data hydration from server-injected <script type="application/json"> tags
// -------------------------------------------------------------------------

function readJSON(id, fallback) {
  const el = document.getElementById(id);
  if (!el) return fallback;
  try {
    return JSON.parse(el.textContent);
  } catch {
    return fallback;
  }
}

const graphData   = readJSON("graph-viz-json",    { nodes: [], edges: [], directed: false });
const traversal   = readJSON("graph-viz-traversal", []);
const trace       = readJSON("graph-viz-trace",    []);
const mstEdgeData = readJSON("graph-viz-mst",      []);
const sccData     = readJSON("graph-viz-sccs",     []);

// -------------------------------------------------------------------------
// Canvas setup
// -------------------------------------------------------------------------

const host   = document.getElementById("graph-viz-host");
const canvas = document.getElementById("graph-viz-canvas");
const ctx    = canvas.getContext("2d");
const empty  = document.getElementById("graph-viz-empty");

let W = 0, H = 0;

function resize() {
  const rect = host.getBoundingClientRect();
  W = rect.width  || 700;
  H = Math.max(rect.height, 340);
  canvas.width  = W * devicePixelRatio;
  canvas.height = H * devicePixelRatio;
  canvas.style.width  = W + "px";
  canvas.style.height = H + "px";
  ctx.scale(devicePixelRatio, devicePixelRatio);
  ensurePositions();
  render();
}

const ro = new ResizeObserver(resize);
ro.observe(host);

// -------------------------------------------------------------------------
// Colour palette
// -------------------------------------------------------------------------

const COLOURS = {
  bg:           "#0f1419",
  surface:      "#1a2332",
  border:       "#2d3a4f",
  text:         "#e8edf4",
  muted:        "#8b9cb3",
  accent:       "#3d9cf5",
  accentDim:    "#2b7fc4",
  success:      "#34c759",
  warning:      "#f5a623",
  error:        "#ff5c5c",
  nodeDefault:  "#1f3050",
  nodeStroke:   "#3d9cf5",
  nodeVisited:  "#0c3d70",
  nodeActive:   "#3d9cf5",
  nodeFinal:    "#34c759",
  edgeDefault:  "#2d3a4f",
  edgeMST:      "#f5a623",
  edgePath:     "#3d9cf5",
};

const SCC_PALETTE = [
  "#3d9cf5", "#34c759", "#f5a623", "#ff5c5c",
  "#af52de", "#5ac8fa", "#ffcc00", "#ff3b30",
];

// -------------------------------------------------------------------------
// Node layout state
// -------------------------------------------------------------------------

/**
 * positions: { [nodeId]: { x, y } }
 * Persisted in sessionStorage so layout survives page reloads.
 */
let positions = {};

function loadPositions() {
  try {
    const raw = sessionStorage.getItem("graph-viz-positions");
    if (raw) {
      positions = JSON.parse(raw);
      // Auto-repair any nodes that got stuck at (0, 0) during the previous W=0 bug
      for (const id in positions) {
        if (positions[id].x === 0 && positions[id].y === 0) {
          delete positions[id];
        }
      }
    }
  } catch {}
}

function savePositions() {
  try {
    sessionStorage.setItem("graph-viz-positions", JSON.stringify(positions));
  } catch {}
}

function ensurePositions() {
  const nodes = graphData.nodes;
  if (!nodes.length) return;

  const known = new Set(Object.keys(positions));
  const incoming = new Set(nodes);

  // Remove stale nodes
  for (const id of known) {
    if (!incoming.has(id)) delete positions[id];
  }

  // Assign positions for new nodes
  const newNodes = nodes.filter(n => !known.has(n));
  if (!newNodes.length) return;

  // If we already have layout, scatter new nodes near the centroid
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
    // Initial circular layout
    const n = nodes.length;
    const cx = W * 0.5, cy = H * 0.5;
    const r = Math.min(W, H) * 0.35;
    nodes.forEach((id, i) => {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2;
      positions[id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });
  }
  savePositions();
}

loadPositions();

// -------------------------------------------------------------------------
// Transform (zoom / pan)
// -------------------------------------------------------------------------

let transform = { x: 0, y: 0, scale: 1 };

function toCanvas(wx, wy) {
  return {
    x: (wx - transform.x) / transform.scale,
    y: (wy - transform.y) / transform.scale,
  };
}

function toWorld(cx, cy) {
  return {
    x: cx * transform.scale + transform.x,
    y: cy * transform.scale + transform.y,
  };
}

function applyZoom(delta, cx, cy) {
  const MIN = 0.3, MAX = 4;
  const newScale = Math.min(MAX, Math.max(MIN, transform.scale * delta));
  const ratio = newScale / transform.scale;
  transform.x = cx - ratio * (cx - transform.x);
  transform.y = cy - ratio * (cy - transform.y);
  transform.scale = newScale;
  render();
}

// -------------------------------------------------------------------------
// Algorithm playback state
// -------------------------------------------------------------------------

let playback = {
  steps:    [],     // array of nodeId strings (visit order)
  current:  -1,     // current step index (-1 = show all final)
  timer:    null,
  playing:  false,
  speedMs:  700,    // ms per step
};

const PB_SPEED_MAP = [1200, 900, 600, 350, 150]; // index 0..4

const pbBar   = document.getElementById("playback-bar");
const pbLabel = document.getElementById("pb-label");
const pbPlay  = document.getElementById("pb-play");

function initPlayback(steps) {
  if (!steps || !steps.length) { pbBar.hidden = true; return; }
  playback.steps   = steps;
  playback.current = -1;
  playback.playing = false;
  stopPlaybackTimer();
  pbBar.hidden = false;
  updatePbLabel();
  render();
}

function updatePbLabel() {
  const total = playback.steps.length;
  const cur   = playback.current;
  if (cur < 0)            pbLabel.textContent = `Ready — ${total} steps`;
  else if (cur >= total)  pbLabel.textContent = `Done (${total}/${total})`;
  else                    pbLabel.textContent = `Step ${cur + 1}/${total}: visit "${playback.steps[cur]}"`;
  pbPlay.textContent = playback.playing ? "⏸" : "▶";
  pbPlay.classList.toggle("active", playback.playing);
}

function stopPlaybackTimer() {
  if (playback.timer) { clearInterval(playback.timer); playback.timer = null; }
  playback.playing = false;
}

function stepPlayback(dir) {
  const total = playback.steps.length;
  playback.current = Math.max(-1, Math.min(total, playback.current + dir));
  updatePbLabel();
  render();
}

document.getElementById("pb-reset").addEventListener("click", () => {
  stopPlaybackTimer(); playback.current = -1; updatePbLabel(); render();
});
document.getElementById("pb-prev").addEventListener("click", () => {
  stopPlaybackTimer(); stepPlayback(-1);
});
document.getElementById("pb-next").addEventListener("click", () => {
  stopPlaybackTimer(); stepPlayback(1);
});
document.getElementById("pb-end").addEventListener("click", () => {
  stopPlaybackTimer(); playback.current = playback.steps.length; updatePbLabel(); render();
});
document.getElementById("pb-play").addEventListener("click", () => {
  if (playback.playing) {
    stopPlaybackTimer(); updatePbLabel(); return;
  }
  if (playback.current >= playback.steps.length) {
    playback.current = -1;
  }
  playback.playing = true;
  updatePbLabel();
  playback.timer = setInterval(() => {
    playback.current++;
    updatePbLabel();
    render();
    if (playback.current >= playback.steps.length) {
      stopPlaybackTimer(); updatePbLabel();
    }
  }, playback.speedMs);
});
document.getElementById("pb-speed").addEventListener("input", function () {
  playback.speedMs = PB_SPEED_MAP[this.value - 1];
  if (playback.playing) {
    stopPlaybackTimer();
    playback.playing = true;
    updatePbLabel();
    playback.timer = setInterval(() => {
      playback.current++;
      updatePbLabel();
      render();
      if (playback.current >= playback.steps.length) {
        stopPlaybackTimer(); updatePbLabel();
      }
    }, playback.speedMs);
  }
});

// Start playback if traversal data was returned from server
if (traversal.length) { initPlayback(traversal); }

// -------------------------------------------------------------------------
// SCC colour map
// -------------------------------------------------------------------------

const sccColourMap = {}; // nodeId → colour string
if (sccData.length) {
  sccData.forEach((scc, i) => {
    const colour = SCC_PALETTE[i % SCC_PALETTE.length];
    scc.forEach(nodeId => { sccColourMap[nodeId] = colour; });
  });
}

// -------------------------------------------------------------------------
// MST edge set
// -------------------------------------------------------------------------

const mstEdgeSet = new Set();
mstEdgeData.forEach(([u, v]) => {
  mstEdgeSet.add(`${u}|${v}`);
  mstEdgeSet.add(`${v}|${u}`);
});

// -------------------------------------------------------------------------
// Render
// -------------------------------------------------------------------------

const NODE_R = 22;

function visitedUpTo(idx) {
  return new Set(idx < 0 ? [] : playback.steps.slice(0, idx + 1));
}

function render() {
  ctx.clearRect(0, 0, W, H);

  // Show empty hint?
  empty.style.display = graphData.nodes.length ? "none" : "flex";

  ctx.save();
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.scale, transform.scale);

  const visited = visitedUpTo(playback.current);
  const activeNode = playback.current >= 0 && playback.current < playback.steps.length
    ? playback.steps[playback.current] : null;

  // ---- Draw edges ----
  graphData.edges.forEach(({ u, v, w }) => {
    const pu = positions[u], pv = positions[v];
    if (!pu || !pv) return;

    const isMST  = mstEdgeSet.has(`${u}|${v}`);
    const isPath = visited.has(u) && visited.has(v);

    ctx.beginPath();
    ctx.lineWidth = isMST ? 3.5 : isPath ? 2.5 : 1.5;
    ctx.strokeStyle = isMST ? COLOURS.edgeMST
                    : isPath ? COLOURS.edgePath
                    : COLOURS.edgeDefault;

    if (graphData.directed) {
      drawArrow(ctx, pu.x, pu.y, pv.x, pv.y);
    } else {
      ctx.moveTo(pu.x, pu.y);
      ctx.lineTo(pv.x, pv.y);
    }
    ctx.stroke();

    // Weight label
    if (w !== undefined && w !== null) {
      const mx = (pu.x + pv.x) / 2;
      const my = (pu.y + pv.y) / 2;
      ctx.save();
      ctx.font = "600 11px 'JetBrains Mono', monospace";
      ctx.fillStyle = isMST ? COLOURS.edgeMST : COLOURS.muted;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(w, mx + 6, my - 6);
      ctx.restore();
    }
  });

  // ---- Draw drag-preview edge ----
  if (dragState.mode === "edge" && dragState.sourceId) {
    const ps = positions[dragState.sourceId];
    if (ps) {
      ctx.beginPath();
      ctx.lineWidth = 2;
      ctx.strokeStyle = COLOURS.accent + "99";
      ctx.setLineDash([6, 4]);
      ctx.moveTo(ps.x, ps.y);
      ctx.lineTo(dragState.mx, dragState.my);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  // ---- Draw nodes ----
  graphData.nodes.forEach(id => {
    const p = positions[id];
    if (!p) return;

    const isVisited = visited.has(id);
    const isActive  = id === activeNode;
    const sccColour = sccColourMap[id];
    const isDone    = playback.current >= playback.steps.length && traversal.includes(id);

    // Node circle
    ctx.beginPath();
    ctx.arc(p.x, p.y, NODE_R, 0, Math.PI * 2);
    ctx.fillStyle = isActive  ? COLOURS.accent
                  : isDone    ? COLOURS.nodeFinal
                  : isVisited ? COLOURS.nodeVisited
                  : sccColour ? sccColour + "22"
                  : COLOURS.nodeDefault;
    ctx.fill();

    // Node stroke
    ctx.lineWidth = isActive ? 3 : 2;
    ctx.strokeStyle = isActive  ? COLOURS.accent
                    : sccColour ? sccColour
                    : isVisited ? COLOURS.accentDim
                    : COLOURS.nodeStroke;
    ctx.stroke();

    // Glow for active
    if (isActive) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, NODE_R + 5, 0, Math.PI * 2);
      ctx.lineWidth = 3;
      ctx.strokeStyle = COLOURS.accent + "44";
      ctx.stroke();
    }

    // Label
    ctx.font = "700 13px 'DM Sans', system-ui, sans-serif";
    ctx.fillStyle = isActive ? "#0a0e14" : COLOURS.text;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(id, p.x, p.y);
  });

  ctx.restore();
}

function drawArrow(ctx, x1, y1, x2, y2) {
  const angle  = Math.atan2(y2 - y1, x2 - x1);
  const len    = Math.hypot(x2 - x1, y2 - y1);
  const endX   = x1 + (len - NODE_R) * Math.cos(angle);
  const endY   = y1 + (len - NODE_R) * Math.sin(angle);
  const startX = x1 + NODE_R * Math.cos(angle);
  const startY = y1 + NODE_R * Math.sin(angle);

  ctx.moveTo(startX, startY);
  ctx.lineTo(endX, endY);
  ctx.stroke();

  // Arrowhead
  const hs = 10, hw = 5;
  ctx.beginPath();
  ctx.moveTo(endX, endY);
  ctx.lineTo(
    endX - hs * Math.cos(angle) + hw * Math.sin(angle),
    endY - hs * Math.sin(angle) - hw * Math.cos(angle)
  );
  ctx.lineTo(
    endX - hs * Math.cos(angle) - hw * Math.sin(angle),
    endY - hs * Math.sin(angle) + hw * Math.cos(angle)
  );
  ctx.closePath();
  ctx.fill();
}

// -------------------------------------------------------------------------
// Interaction state machine
// -------------------------------------------------------------------------

const dragState = {
  mode:     null,   // null | "node" | "edge" | "pan"
  sourceId: null,   // node being dragged from
  targetId: null,   // potential edge target
  mx:       0,      // mouse x in canvas coords
  my:       0,
  panStartX: 0,
  panStartY: 0,
  panTX:    0,
  panTY:    0,
  moved:    false,
};

function hitTest(cx, cy) {
  for (const id of [...graphData.nodes].reverse()) {
    const p = positions[id];
    if (!p) continue;
    const dx = p.x - cx, dy = p.y - cy;
    if (dx * dx + dy * dy <= NODE_R * NODE_R) return id;
  }
  return null;
}

function canvasXY(e) {
  const rect = canvas.getBoundingClientRect();
  const px = (e.clientX - rect.left);
  const py = (e.clientY - rect.top);
  return toCanvas(px, py);
}

canvas.addEventListener("mousedown", e => {
  e.preventDefault();
  const { x, y } = canvasXY(e);
  const hit = hitTest(x, y);

  if (e.button === 2) return; // handled by contextmenu

  if (e.altKey && hit) {
    // Alt+drag = move node
    dragState.mode = "node";
    dragState.sourceId = hit;
    dragState.moved = false;
  } else if (hit) {
    // Normal drag on node = draw edge
    dragState.mode = "edge";
    dragState.sourceId = hit;
    dragState.mx = x;
    dragState.my = y;
    dragState.moved = false;
  } else {
    // Drag on empty = pan
    dragState.mode = "pan";
    dragState.panStartX = e.clientX;
    dragState.panStartY = e.clientY;
    dragState.panTX = transform.x;
    dragState.panTY = transform.y;
    dragState.moved = false;
  }
});

canvas.addEventListener("mousemove", e => {
  const { x, y } = canvasXY(e);
  dragState.mx = x;
  dragState.my = y;

  if (dragState.mode === "node") {
    dragState.moved = true;
    positions[dragState.sourceId] = { x, y };
    savePositions();
    render();
  } else if (dragState.mode === "edge") {
    dragState.moved = true;
    dragState.targetId = hitTest(x, y);
    render();
  } else if (dragState.mode === "pan") {
    dragState.moved = true;
    transform.x = dragState.panTX + (e.clientX - dragState.panStartX);
    transform.y = dragState.panTY + (e.clientY - dragState.panStartY);
    render();
  }
});

canvas.addEventListener("mouseup", e => {
  const { x, y } = canvasXY(e);

  if (dragState.mode === "edge" && dragState.sourceId) {
    const target = hitTest(x, y);
    if (target && target !== dragState.sourceId) {
      // User dragged from source to target — fill in the edge form
      prefillEdgeForm(dragState.sourceId, target);
    } else if (!dragState.moved) {
      // Click on a node — do nothing special (context menu handles actions)
    }
  } else if (dragState.mode === null && !dragState.moved) {
    // Click on empty canvas — prompt to add node
    const { x: cx, y: cy } = canvasXY(e);
    const hit = hitTest(cx, cy);
    if (!hit) showAddNodePrompt(cx, cy);
  }

  if (dragState.mode === "pan" && !dragState.moved) {
    // Click on canvas (no node hit) handled above
    const hit = hitTest(x, y);
    if (!hit) showAddNodePrompt(x, y);
  }

  dragState.mode = null;
  dragState.sourceId = null;
  dragState.moved = false;
  render();
});

canvas.addEventListener("wheel", e => {
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const cx = e.clientX - rect.left;
  const cy = e.clientY - rect.top;
  const factor = e.deltaY < 0 ? 1.12 : 0.9;
  applyZoom(factor, cx, cy);
}, { passive: false });

canvas.addEventListener("contextmenu", e => {
  e.preventDefault();
  const { x, y } = canvasXY(e);
  const hit = hitTest(x, y);
  if (hit) showContextMenu(e.clientX, e.clientY, hit);
  else hideContextMenu();
});

document.addEventListener("click", hideContextMenu);
document.addEventListener("keydown", e => {
  if (e.key === "Escape") { hideContextMenu(); hidePrompt(); }
});

// -------------------------------------------------------------------------
// Context menu
// -------------------------------------------------------------------------

const ctxMenu = document.getElementById("canvas-ctx-menu");
let ctxNodeId = null;

function showContextMenu(px, py, nodeId) {
  ctxNodeId = nodeId;
  ctxMenu.hidden = false;
  ctxMenu.style.left = px + "px";
  ctxMenu.style.top  = py + "px";
}

function hideContextMenu() {
  ctxMenu.hidden = true;
  ctxNodeId = null;
}

document.getElementById("ctx-set-start").addEventListener("click", () => {
  if (!ctxNodeId) return;
  // Prefill all start-node inputs
  ["bfs-start","dfs-start","dijk-start","bf-start"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = ctxNodeId;
  });
  hideContextMenu();
});

document.getElementById("ctx-set-end").addEventListener("click", () => {
  hideContextMenu(); // no end-node inputs in this UI yet; extensible
});

document.getElementById("ctx-delete-node").addEventListener("click", () => {
  if (!ctxNodeId) return;
  const form = document.createElement("form");
  form.method = "POST";
  form.action = "/delete_node";
  const input = document.createElement("input");
  input.name = "node_id";
  input.value = ctxNodeId;
  form.appendChild(input);
  document.body.appendChild(form);
  form.submit();
});

// -------------------------------------------------------------------------
// Prompt overlay (add node on click)
// -------------------------------------------------------------------------

const overlay = document.getElementById("canvas-prompt-overlay");
const promptInput = document.getElementById("canvas-prompt-input");
let pendingCanvasXY = null;

function showAddNodePrompt(cx, cy) {
  pendingCanvasXY = { cx, cy };
  document.getElementById("canvas-prompt-title").textContent = "Add node";
  promptInput.value = "";
  document.getElementById("canvas-prompt-extra").innerHTML = "";
  overlay.hidden = false;
  setTimeout(() => promptInput.focus(), 50);
}

function hidePrompt() {
  overlay.hidden = true;
  pendingCanvasXY = null;
}

document.getElementById("canvas-prompt-cancel").addEventListener("click", hidePrompt);
document.getElementById("canvas-prompt-confirm").addEventListener("click", () => {
  const id = promptInput.value.trim();
  if (!id) return;
  // Submit via the existing add-node form
  const nodeInput = document.getElementById("add-node-id");
  if (nodeInput) nodeInput.value = id;
  document.getElementById("add-node-form").submit();
});

promptInput.addEventListener("keydown", e => {
  if (e.key === "Enter") document.getElementById("canvas-prompt-confirm").click();
});

overlay.addEventListener("click", e => {
  if (e.target === overlay) hidePrompt();
});

// -------------------------------------------------------------------------
// Edge form prefill helper
// -------------------------------------------------------------------------

function prefillEdgeForm(from, to) {
  const fromInput = document.getElementById("edge-from");
  const toInput   = document.getElementById("edge-to");
  if (fromInput) fromInput.value = from;
  if (toInput)   toInput.value   = to;
  // Highlight the weight input
  const wInput = document.getElementById("edge-weight");
  if (wInput) { wInput.focus(); }
}

// -------------------------------------------------------------------------
// Toolbar buttons
// -------------------------------------------------------------------------

document.getElementById("graph-viz-shuffle").addEventListener("click", () => {
  const n = graphData.nodes.length;
  if (!n) return;
  const cx = W * 0.5, cy = H * 0.5;
  const r  = Math.min(W, H) * 0.33;
  graphData.nodes.forEach((id, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2 + (Math.random() - 0.5) * 0.4;
    positions[id] = {
      x: cx + r * Math.cos(angle) * (0.8 + Math.random() * 0.4),
      y: cy + r * Math.sin(angle) * (0.8 + Math.random() * 0.4),
    };
  });
  savePositions();
  render();
});

document.getElementById("graph-viz-zoom-in").addEventListener("click",  () => applyZoom(1.2, W / 2, H / 2));
document.getElementById("graph-viz-zoom-out").addEventListener("click", () => applyZoom(0.83, W / 2, H / 2));
document.getElementById("graph-viz-zoom-reset").addEventListener("click", () => {
  transform = { x: 0, y: 0, scale: 1 };
  render();
});

// -------------------------------------------------------------------------
// Initial render
// -------------------------------------------------------------------------

render();
