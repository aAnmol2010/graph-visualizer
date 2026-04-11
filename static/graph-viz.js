(function () {
  "use strict";

  var SCROLL_KEY = "graphVizScrollY";

  document.addEventListener(
    "submit",
    function () {
      try {
        sessionStorage.setItem(
          SCROLL_KEY,
          String(window.scrollY || window.pageYOffset || 0)
        );
      } catch (e) {}
    },
    true
  );

  function restoreScrollAfterFormPost() {
    try {
      var raw = sessionStorage.getItem(SCROLL_KEY);
      if (raw === null) return;
      sessionStorage.removeItem(SCROLL_KEY);
      var y = parseInt(raw, 10);
      if (isNaN(y) || y < 0) return;
      function apply() {
        window.scrollTo(0, y);
      }
      apply();
      requestAnimationFrame(function () {
        requestAnimationFrame(apply);
      });
      window.setTimeout(apply, 100);
    } catch (e) {}
  }

  var NODE_R = 22;
  var PAD = 44;
  var MIN_H = 300;
  var STEP_MS = 620;

  var state = {
    layout: null,
    data: null,
    seed: 1,
    cssW: 0,
    cssH: 0,
    ctx: null,
    traversal: [],
    trace: [],
    animStep: 0,
    animTimer: null,
    pulseRaf: null,
  };

  function mulberry32(seed) {
    return function () {
      var t = (seed += 0x6d2b79f5);
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function hashSeed(str) {
    var h = 2166136261;
    for (var i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function runLayout(data, W, H, seed) {
    var rng = mulberry32(seed);
    var ids = data.nodes.map(function (n) {
      return n.id;
    });
    var n = ids.length;
    var pos = {};
    var cx = W / 2;
    var cy = H / 2;
    var R = Math.min(W, H) * 0.3;
    var i;
    for (i = 0; i < n; i++) {
      var id = ids[i];
      var ang = (2 * Math.PI * i) / Math.max(n, 1) + rng() * 0.5;
      var rr = R * (0.75 + 0.45 * rng());
      pos[id] = { x: cx + rr * Math.cos(ang), y: cy + rr * Math.sin(ang) };
    }

    var edges = data.edges.filter(function (e) {
      return e.from !== e.to;
    });
    var area = W * H;
    var k = Math.sqrt(area / Math.max(n, 1));
    var iter;

    for (iter = 0; iter < 480; iter++) {
      var disp = {};
      for (i = 0; i < ids.length; i++) {
        disp[ids[i]] = { x: 0, y: 0 };
      }

      var a, b, dx, dy, dist, fr, fa, j;
      for (i = 0; i < ids.length; i++) {
        for (j = i + 1; j < ids.length; j++) {
          a = ids[i];
          b = ids[j];
          dx = pos[b].x - pos[a].x;
          dy = pos[b].y - pos[a].y;
          dist = Math.hypot(dx, dy) || 0.01;
          fr = (k * k) / dist;
          dx /= dist;
          dy /= dist;
          disp[a].x -= fr * dx;
          disp[a].y -= fr * dy;
          disp[b].x += fr * dx;
          disp[b].y += fr * dy;
        }
      }

      for (i = 0; i < edges.length; i++) {
        var e = edges[i];
        a = e.from;
        b = e.to;
        if (!pos[a] || !pos[b]) continue;
        dx = pos[b].x - pos[a].x;
        dy = pos[b].y - pos[a].y;
        dist = Math.hypot(dx, dy) || 0.01;
        fa = ((dist * dist) / k) * 0.048;
        dx /= dist;
        dy /= dist;
        disp[a].x += fa * dx;
        disp[a].y += fa * dy;
        disp[b].x -= fa * dx;
        disp[b].y -= fa * dy;
      }

      var t = 0.38 * (1 - iter / 480) + 0.025;
      for (i = 0; i < ids.length; i++) {
        id = ids[i];
        dx = disp[id].x;
        dy = disp[id].y;
        var m = Math.hypot(dx, dy) || 1;
        var step = Math.min(m, k * 0.18) * t;
        pos[id].x += (dx / m) * step;
        pos[id].y += (dy / m) * step;
        pos[id].x = Math.max(PAD, Math.min(W - PAD, pos[id].x));
        pos[id].y = Math.max(PAD, Math.min(H - PAD, pos[id].y));
      }
    }

    fitPositions(pos, ids, W, H, PAD);
    return { pos: pos, ids: ids, edges: data.edges };
  }

  function fitPositions(pos, ids, W, H, pad) {
    if (!ids.length) return;
    var minX = Infinity;
    var minY = Infinity;
    var maxX = -Infinity;
    var maxY = -Infinity;
    var i;
    for (i = 0; i < ids.length; i++) {
      var p = pos[ids[i]];
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
    }
    var bw = maxX - minX || 1;
    var bh = maxY - minY || 1;
    var scale = Math.min((W - 2 * pad) / bw, (H - 2 * pad) / bh);
    if (!isFinite(scale) || scale <= 0) scale = 1;
    var cx = (minX + maxX) / 2;
    var cy = (minY + maxY) / 2;
    var tcx = W / 2;
    var tcy = H / 2;
    for (i = 0; i < ids.length; i++) {
      var id = ids[i];
      pos[id].x = (pos[id].x - cx) * scale + tcx;
      pos[id].y = (pos[id].y - cy) * scale + tcy;
    }
  }

  function shortenSegment(x1, y1, x2, y2, r1, r2) {
    var dx = x2 - x1;
    var dy = y2 - y1;
    var dist = Math.hypot(dx, dy);
    if (dist < 1e-6) return null;
    dx /= dist;
    dy /= dist;
    return {
      x1: x1 + dx * r1,
      y1: y1 + dy * r1,
      x2: x2 - dx * r2,
      y2: y2 - dy * r2,
    };
  }

  function drawArrowHead(ctx, x, y, angle, color) {
    var sz = 12;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(-sz, -sz * 0.55);
    ctx.lineTo(-sz, sz * 0.55);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  function drawSelfLoop(ctx, x, y, directed, stroke) {
    var cx = x + NODE_R + 18;
    var cy = y - 26;
    var loopR = 24;
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(cx, cy, loopR, 0.35 * Math.PI, 1.65 * Math.PI, true);
    ctx.stroke();
    if (directed) {
      var ang = 1.65 * Math.PI + Math.PI / 2;
      var px = cx + loopR * Math.cos(1.65 * Math.PI);
      var py = cy + loopR * Math.sin(1.65 * Math.PI);
      drawArrowHead(ctx, px, py, ang, stroke);
    }
  }

  function formatWeight(w) {
    var f = Number(w);
    if (Number.isInteger(f)) return String(f);
    return String(Math.round(f * 1000) / 1000);
  }

  function drawEdgeLabel(ctx, text, mx, my) {
    ctx.font = '500 10px "JetBrains Mono", Consolas, monospace';
    var padX = 4;
    var padY = 2;
    var m = ctx.measureText(text);
    var w = m.width + padX * 2;
    var h = 12 + padY * 2;
    ctx.fillStyle = "rgba(15, 20, 25, 0.92)";
    ctx.strokeStyle = "rgba(45, 58, 79, 0.95)";
    ctx.lineWidth = 1;
    var rx = mx - w / 2;
    var ry = my - h / 2;
    ctx.beginPath();
    if (typeof ctx.roundRect === "function") {
      ctx.roundRect(rx, ry, w, h, 3);
    } else {
      ctx.rect(rx, ry, w, h);
    }
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#8b9cb3";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, mx, my);
  }

  function buildHighlightState(traversal, step) {
    var len = traversal.length;
    var orderById = {};
    var i;
    for (i = 0; i < step && i < len; i++) {
      orderById[traversal[i]] = i + 1;
    }
    var current = null;
    if (step < len) {
      current = traversal[step];
    }
    return {
      orderById: orderById,
      current: current,
      onStack: {},
      useStack: false,
    };
  }

  function buildHighlightFromTrace(trace, step) {
    var len = trace.length;
    var orderById = {};
    var i;
    for (i = 0; i < step && i < len; i++) {
      orderById[trace[i].focus] = i + 1;
    }
    var current = null;
    var onStack = {};
    if (step < len) {
      var frame = trace[step];
      current = frame.focus;
      var stk = frame.stack || [];
      for (i = 0; i < stk.length; i++) {
        if (stk[i] !== current) {
          onStack[stk[i]] = true;
        }
      }
    }
    return {
      orderById: orderById,
      current: current,
      onStack: onStack,
      useStack: true,
    };
  }

  function drawOrderBadge(ctx, x, y, num, isActive) {
    var r = 11;
    ctx.beginPath();
    ctx.arc(x, y + NODE_R + 14, r, 0, Math.PI * 2);
    if (isActive) {
      ctx.fillStyle = "rgba(245, 166, 35, 0.2)";
      ctx.strokeStyle = "#f5a623";
    } else {
      ctx.fillStyle = "rgba(52, 199, 89, 0.25)";
      ctx.strokeStyle = "#34c759";
    }
    ctx.lineWidth = 1.5;
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = isActive ? "#ffd59a" : "#a8e9b8";
    ctx.font = '600 10px "DM Sans", system-ui, sans-serif';
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(num), x, y + NODE_R + 14);
  }

  function drawNode(ctx, id, p, hi) {
    var orderById = hi.orderById;
    var current = hi.current;
    var isCurrent = current === id;
    var ord = orderById[id];
    var onStack = hi.useStack && hi.onStack && hi.onStack[id];

    if (isCurrent) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, NODE_R + 8, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255, 200, 100, 0.95)";
      ctx.lineWidth = 3.5;
      ctx.stroke();
    } else if (onStack) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, NODE_R + 4, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(201, 139, 43, 0.75)";
      ctx.lineWidth = 2.5;
      ctx.stroke();
    }

    ctx.beginPath();
    ctx.arc(p.x, p.y, NODE_R, 0, Math.PI * 2);
    if (isCurrent) {
      ctx.fillStyle = "#4a3518";
      ctx.strokeStyle = "#ffc964";
    } else if (hi.useStack && onStack) {
      ctx.fillStyle = "#352a1e";
      ctx.strokeStyle = "#d4a04a";
    } else if (ord !== undefined) {
      ctx.fillStyle = "#152a24";
      ctx.strokeStyle = "#34c759";
    } else {
      ctx.fillStyle = "#1e2a3d";
      ctx.strokeStyle = "#3d9cf5";
    }
    ctx.lineWidth = isCurrent ? 3 : onStack ? 2.5 : 2.5;
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#e8edf4";
    ctx.font = '600 13px "DM Sans", system-ui, sans-serif';
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(id), p.x, p.y);

    if (ord !== undefined && !isCurrent) {
      drawOrderBadge(ctx, p.x, p.y, ord, false);
    } else if (isCurrent) {
      var stepNum = Object.keys(orderById).length + 1;
      drawOrderBadge(ctx, p.x, p.y, stepNum, true);
    }
  }

  function draw(ctx, layout, data, W, H, hi) {
    ctx.clearRect(0, 0, W, H);
    var edgeMain = "#7eb3ea";
    var edgeGlow = "rgba(126, 179, 234, 0.45)";
    var pos = layout.pos;
    var i;

    for (i = 0; i < layout.edges.length; i++) {
      var e = layout.edges[i];
      var u = e.from;
      var v = e.to;
      if (!pos[u] || !pos[v]) continue;
      var x1 = pos[u].x;
      var y1 = pos[u].y;
      var x2 = pos[v].x;
      var y2 = pos[v].y;
      if (u === v) {
        drawSelfLoop(ctx, x1, y1, data.directed, edgeMain);
        drawEdgeLabel(ctx, formatWeight(e.w), x1 + NODE_R + 18, y1 - 52);
        continue;
      }
      var seg = shortenSegment(x1, y1, x2, y2, NODE_R, NODE_R);
      if (!seg) continue;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      ctx.moveTo(seg.x1, seg.y1);
      ctx.lineTo(seg.x2, seg.y2);
      ctx.strokeStyle = edgeGlow;
      ctx.lineWidth = 8;
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(seg.x1, seg.y1);
      ctx.lineTo(seg.x2, seg.y2);
      ctx.strokeStyle = edgeMain;
      ctx.lineWidth = 3.5;
      ctx.stroke();
      if (data.directed) {
        var adx = seg.x2 - seg.x1;
        var ady = seg.y2 - seg.y1;
        var ang = Math.atan2(ady, adx);
        drawArrowHead(ctx, seg.x2, seg.y2, ang, edgeMain);
      }
      var mx = (seg.x1 + seg.x2) / 2;
      var my = (seg.y1 + seg.y2) / 2 - 10;
      drawEdgeLabel(ctx, formatWeight(e.w), mx, my);
    }

    for (i = 0; i < layout.ids.length; i++) {
      var id = layout.ids[i];
      drawNode(ctx, id, pos[id], hi);
    }
  }

  function setupCanvas(canvas, cssW, cssH) {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(cssW * dpr);
    canvas.height = Math.floor(cssH * dpr);
    canvas.style.width = cssW + "px";
    canvas.style.height = cssH + "px";
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return ctx;
  }

  function parseData() {
    var el = document.getElementById("graph-viz-json");
    if (!el) return { directed: false, nodes: [], edges: [] };
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return { directed: false, nodes: [], edges: [] };
    }
  }

  function parseTraversal() {
    var el = document.getElementById("graph-viz-traversal");
    if (!el) return [];
    try {
      var t = JSON.parse(el.textContent);
      return Array.isArray(t) ? t : [];
    } catch (e) {
      return [];
    }
  }

  function parseTrace() {
    var el = document.getElementById("graph-viz-trace");
    if (!el) return [];
    try {
      var t = JSON.parse(el.textContent);
      if (!Array.isArray(t)) return [];
      return t.filter(function (x) {
        return x && x.focus != null && Array.isArray(x.stack);
      });
    } catch (e) {
      return [];
    }
  }

  function stopAnimation() {
    if (state.animTimer !== null) {
      clearInterval(state.animTimer);
      state.animTimer = null;
    }
    if (state.pulseRaf !== null) {
      cancelAnimationFrame(state.pulseRaf);
      state.pulseRaf = null;
    }
  }

  function updateStepLabel(trace, traversal, step) {
    var el = document.getElementById("graph-viz-step");
    if (!el) return;
    var len = trace.length > 0 ? trace.length : traversal.length;
    if (!len) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    if (step < len) {
      if (trace.length > 0) {
        var fr = trace[step];
        el.textContent =
          "Recursive call stack: " +
          fr.stack.join(" → ") +
          ' — visiting / printing "' +
          fr.focus +
          '"';
      } else {
        var cur = traversal[step];
        el.textContent =
          "Step " +
          (step + 1) +
          " of " +
          len +
          ': visiting "' +
          cur +
          '" (output order)';
      }
    } else {
      el.textContent = "Done — order: " + traversal.join(" → ");
    }
  }

  function animStepCount() {
    return state.trace.length > 0 ? state.trace.length : state.traversal.length;
  }

  function buildAnimHighlight(step) {
    if (state.trace.length > 0) {
      return buildHighlightFromTrace(state.trace, step);
    }
    return buildHighlightState(state.traversal, step);
  }

  function redrawFrame() {
    if (!state.ctx || !state.layout) return;
    var hi = buildAnimHighlight(state.animStep);
    draw(state.ctx, state.layout, state.data, state.cssW, state.cssH, hi);
    updateStepLabel(state.trace, state.traversal, state.animStep);
  }

  function startTraversalAnimation() {
    stopAnimation();
    var n = animStepCount();
    if (!n) {
      updateStepLabel([], [], 0);
      redrawFrame();
      return;
    }
    state.animStep = 0;
    redrawFrame();
    state.animTimer = window.setInterval(function () {
      state.animStep += 1;
      redrawFrame();
      if (state.animStep >= n) {
        stopAnimation();
      }
    }, STEP_MS);
  }

  function renderFull() {
    var host = document.getElementById("graph-viz-host");
    var canvas = document.getElementById("graph-viz-canvas");
    var emptyEl = document.getElementById("graph-viz-empty");
    if (!host || !canvas) return;

    stopAnimation();

    var data = parseData();
    state.data = data;
    state.traversal = parseTraversal();
    state.trace = parseTrace();
    var hasNodes = data.nodes && data.nodes.length > 0;

    if (emptyEl) {
      emptyEl.style.display = hasNodes ? "none" : "block";
    }
    canvas.style.display = hasNodes ? "block" : "none";

    var stepEl = document.getElementById("graph-viz-step");
    if (stepEl && !hasNodes) {
      stepEl.hidden = true;
      stepEl.textContent = "";
    }

    if (!hasNodes) {
      state.layout = null;
      return;
    }

    var cssW = Math.max(host.clientWidth || 400, 260);
    var cssH = Math.round(Math.min(520, Math.max(MIN_H, cssW * 0.78)));
    state.cssW = cssW;
    state.cssH = cssH;
    state.ctx = setupCanvas(canvas, cssW, cssH);
    state.layout = runLayout(data, cssW, cssH, state.seed);

    if (state.trace.length > 0 || state.traversal.length > 0) {
      state.animStep = 0;
      startTraversalAnimation();
    } else {
      var neutral = {
        orderById: {},
        current: null,
        onStack: {},
        useStack: false,
      };
      draw(state.ctx, state.layout, data, cssW, cssH, neutral);
      if (stepEl) {
        stepEl.hidden = true;
        stepEl.textContent = "";
      }
    }
  }

  function reshuffle() {
    state.seed = (Math.random() * 0xffffffff) >>> 0;
    renderFull();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var raw = document.getElementById("graph-viz-json");
    if (raw) {
      state.seed = hashSeed(raw.textContent || "0");
    }
    renderFull();
    var btn = document.getElementById("graph-viz-shuffle");
    if (btn) btn.addEventListener("click", reshuffle);

    var host = document.getElementById("graph-viz-host");
    if (host && typeof ResizeObserver !== "undefined") {
      var t = null;
      var ro = new ResizeObserver(function () {
        if (t) clearTimeout(t);
        t = setTimeout(function () {
          renderFull();
        }, 80);
      });
      ro.observe(host);
    } else {
      window.addEventListener("resize", function () {
        renderFull();
      });
    }

    restoreScrollAfterFormPost();
  });
})();
