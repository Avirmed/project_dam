/*
 * profilechart.js - dependency-free, responsive SVG preview of a surveyed
 * cross-section polygon (Sensor -> Flow tab, "Custom Profile"). Reusable.
 *
 * renderProfileChart(container, points, options)
 *   container : DOM element, CSS selector, or jQuery object.
 *   points    : [{x, y, ...}] in survey order (numbers or numeric strings; rows
 *               with a blank / invalid coordinate are skipped). Extra keys are
 *               kept and handed back to onChange, so the caller can carry e.g.
 *               its table row index.
 *   options   : { ref: "Level" | "Depth", xTitle, yTitle,
 *                 onChange(point, x, y), precision }
 *               ref "Depth": the y axis grows downwards (distance below the
 *               reference). onChange enables dragging: while a marker is
 *               dragged the callback receives the original point object and its
 *               new coordinates (rounded to `precision` decimals, default 3);
 *               the caller updates its data and calls renderProfileChart again.
 *
 * Draws the points numbered in order, straight segments between consecutive
 * points and a dashed closing segment back to the first point - the closed
 * polygon whose area under a water line is the wetted cross-section.
 */
function renderProfileChart(container, points, options) {
    var el = typeof container === "string"
        ? document.querySelector(container)
        : (container && container.jquery ? container[0] : container);
    if (!el) return;

    options = options || {};
    var depth = options.ref === "Depth";
    var interactive = typeof options.onChange === "function";
    var precision = options.precision === undefined ? 3 : options.precision;

    function num(v) {
        if (v === null || v === undefined || String(v).trim() === "") return null;
        var n = parseFloat(v);
        return isNaN(n) ? null : n;
    }
    function esc(s) { return String(s === undefined ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
    function fmt(n) { return Math.round(n * 1000) / 1000; }

    var pts = [];
    (points || []).forEach(function (p) {
        var x = num(p && p.x), y = num(p && p.y);
        if (x !== null && y !== null) pts.push({ x: x, y: y, src: p });
    });

    // Draw at the container's real pixel size so typography stays crisp and
    // the same size whatever the width. The width is measured only when the
    // container's size really changes (ResizeObserver: tab shown, window
    // resized); re-renders caused by typing / clicking reuse the cached width,
    // so the picture never jumps under the pointer. Height is fixed.
    el._pcArgs = { points: points, options: options };
    var measured = el.clientWidth || (el.getBoundingClientRect ? el.getBoundingClientRect().width : 0) || 0;
    if (measured > 0 && !el._pcWidth) el._pcWidth = Math.round(measured);   // first visible render
    var W = Math.max(320, el._pcWidth || options.width || 800);
    var H = Math.round(options.height || 320);
    var padL = 54, padR = 22, padT = 18, padB = 38;
    var plotW = W - padL - padR, plotH = H - padT - padB;
    var F = { tick: 10, title: 11, label: 11, hint: 10 };   // font sizes in px

    if (!el._pcResize && typeof window !== "undefined") {
        el._pcResize = true;
        var redraw = function (width) {
            if (!el._pcArgs || el._pcDrag) return;
            width = Math.round(width);
            if (width < 1 || width === el._pcWidth) return;   // hidden, or unchanged
            el._pcWidth = width;
            renderProfileChart(el, el._pcArgs.points, el._pcArgs.options);
        };
        if (typeof window.ResizeObserver === "function") {
            new window.ResizeObserver(function (entries) {
                redraw(entries[0].contentRect.width);
            }).observe(el);
        } else if (window.addEventListener) {
            var timer = null;
            window.addEventListener("resize", function () {
                clearTimeout(timer);
                timer = setTimeout(function () { redraw(el.clientWidth || 0); }, 150);
            });
        }
    }

    // Scale from the data; frozen while a marker is being dragged so the
    // picture does not jump under the pointer.
    var scale;
    if (el._pcDrag && el._pcScale) {
        scale = el._pcScale;
    } else {
        var xmin = -1, xmax = 1, ymin = -1, ymax = 1;
        if (pts.length) {
            xmin = Math.min.apply(null, pts.map(function (p) { return p.x; }));
            xmax = Math.max.apply(null, pts.map(function (p) { return p.x; }));
            ymin = Math.min.apply(null, pts.map(function (p) { return p.y; }));
            ymax = Math.max.apply(null, pts.map(function (p) { return p.y; }));
            if (xmax === xmin) { xmax += 1; xmin -= 1; }
            if (ymax === ymin) { ymax += 1; ymin -= 1; }
            var px = (xmax - xmin) * 0.08, py = (ymax - ymin) * 0.12;
            xmin -= px; xmax += px; ymin -= py; ymax += py;
        }
        scale = { xmin: xmin, xmax: xmax, ymin: ymin, ymax: ymax };
    }
    el._pcScale = scale;
    var xr = scale.xmax - scale.xmin, yr = scale.ymax - scale.ymin;
    function X(v) { return padL + (v - scale.xmin) / xr * plotW; }
    // "Level": larger y is higher on screen; "Depth": larger y is lower.
    function Y(v) { return depth ? padT + (v - scale.ymin) / yr * plotH : padT + (scale.ymax - v) / yr * plotH; }

    var grid = "", ticks = "", i, n = 5;
    for (i = 0; i <= n; i++) {
        var gx = scale.xmin + xr * i / n, gy = scale.ymin + yr * i / n;
        grid += '<line x1="' + X(gx).toFixed(1) + '" y1="' + padT + '" x2="' + X(gx).toFixed(1) + '" y2="' + (padT + plotH) + '" stroke="#eef1f5" stroke-width="1"/>';
        grid += '<line x1="' + padL + '" y1="' + Y(gy).toFixed(1) + '" x2="' + (padL + plotW) + '" y2="' + Y(gy).toFixed(1) + '" stroke="#eef1f5" stroke-width="1"/>';
        ticks += '<text x="' + X(gx).toFixed(1) + '" y="' + (padT + plotH + 16) + '" text-anchor="middle" font-size="' + F.tick + '" fill="#8a94a3">' + fmt(gx) + "</text>";
        ticks += '<text x="' + (padL - 8) + '" y="' + (Y(gy) + 3.5).toFixed(1) + '" text-anchor="end" font-size="' + F.tick + '" fill="#8a94a3">' + fmt(gy) + "</text>";
    }

    var shape = "", edges = "", closing = "", markers = "";
    if (pts.length >= 2) {
        var d = pts.map(function (p, k) { return (k ? "L " : "M ") + X(p.x).toFixed(1) + " " + Y(p.y).toFixed(1); }).join(" ");
        if (pts.length >= 3) {
            shape = '<path d="' + d + ' Z" fill="#7cc6ee" fill-opacity="0.12" stroke="none"/>';
            var a = pts[pts.length - 1], b = pts[0];
            closing = '<line x1="' + X(a.x).toFixed(1) + '" y1="' + Y(a.y).toFixed(1) + '" x2="' + X(b.x).toFixed(1) + '" y2="' + Y(b.y).toFixed(1) + '" stroke="#2b5aa6" stroke-width="1" stroke-dasharray="5 4" stroke-opacity="0.7"/>';
        }
        edges = '<path d="' + d + '" fill="none" stroke="#2b5aa6" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>';
    }
    pts.forEach(function (p, k) {
        var cx = X(p.x), cy = Y(p.y);
        var active = el._pcDrag && el._pcDrag.index === k;
        markers += '<circle cx="' + cx.toFixed(1) + '" cy="' + cy.toFixed(1) + '" r="' + (active ? 5 : 3.2) + '" fill="#ffffff" stroke="#1a56db" stroke-width="1.6"' +
            (interactive ? ' style="cursor:grab"' : "") + ' data-index="' + k + '"/>' +
            '<text x="' + (cx + 6).toFixed(1) + '" y="' + (cy + 13).toFixed(1) + '" font-size="' + F.label + '" font-weight="600" fill="#1a56db">' + (k + 1) + "</text>";
        if (active) {
            markers += '<text x="' + (cx + 8).toFixed(1) + '" y="' + (cy - 8).toFixed(1) + '" font-size="' + F.hint + '" fill="#2b3a4a">' + fmt(p.x) + ", " + fmt(p.y) + "</text>";
        }
    });

    var titles = "";
    if (options.xTitle) titles += '<text x="' + (padL + plotW / 2) + '" y="' + (H - 6) + '" text-anchor="middle" font-size="' + F.title + '" fill="#6b7480">' + esc(options.xTitle) + "</text>";
    if (options.yTitle) titles += '<text x="14" y="' + (padT + plotH / 2) + '" text-anchor="middle" font-size="' + F.title + '" fill="#6b7480" transform="rotate(-90 14 ' + (padT + plotH / 2) + ')">' + esc(options.yTitle) + "</text>";

    el.innerHTML =
        '<svg viewBox="0 0 ' + W + " " + H + '" width="' + W + '" height="' + H + '" style="display:block;max-width:100%;font-family:inherit' + (interactive ? ";touch-action:none;user-select:none" : "") + '">' +
        '<rect x="' + padL + '" y="' + padT + '" width="' + plotW + '" height="' + plotH + '" fill="#fbfdff" stroke="#e1e6ec" stroke-width="1"/>' +
        grid + shape + closing + edges + markers + ticks + titles +
        "</svg>";

    // ---- dragging (pointer events on the container survive re-renders) ----
    el._pcState = { pts: pts, depth: depth, padL: padL, padT: padT, plotW: plotW, plotH: plotH, onChange: options.onChange, precision: precision };
    if (!interactive || el._pcBound || typeof el.addEventListener !== "function") return;
    el._pcBound = true;

    function toViewBox(evt) {
        var svg = el.querySelector("svg");
        if (!svg || !svg.getScreenCTM) return null;
        var pt = svg.createSVGPoint();
        pt.x = evt.clientX; pt.y = evt.clientY;
        return pt.matrixTransform(svg.getScreenCTM().inverse());
    }
    function toData(loc) {
        var s = el._pcState, sc = el._pcScale;
        var x = sc.xmin + (loc.x - s.padL) / s.plotW * (sc.xmax - sc.xmin);
        var y = s.depth
            ? sc.ymin + (loc.y - s.padT) / s.plotH * (sc.ymax - sc.ymin)
            : sc.ymax - (loc.y - s.padT) / s.plotH * (sc.ymax - sc.ymin);
        var f = Math.pow(10, s.precision);
        return { x: Math.round(x * f) / f, y: Math.round(y * f) / f };
    }

    el.addEventListener("pointerdown", function (evt) {
        var target = evt.target;
        if (!target || target.tagName !== "circle" || target.getAttribute("data-index") === null) return;
        var index = parseInt(target.getAttribute("data-index"), 10);
        var point = el._pcState.pts[index];
        if (!point) return;
        el._pcDrag = { index: index, src: point.src };
        evt.preventDefault();
        if (el.setPointerCapture) el.setPointerCapture(evt.pointerId);
    });
    el.addEventListener("pointermove", function (evt) {
        if (!el._pcDrag) return;
        var loc = toViewBox(evt);
        if (!loc) return;
        var data = toData(loc);
        el._pcState.onChange(el._pcDrag.src, data.x, data.y);
    });
    function endDrag(evt) {
        if (!el._pcDrag) return;
        el._pcDrag = null;
        if (el.releasePointerCapture && evt && evt.pointerId !== undefined) {
            try { el.releasePointerCapture(evt.pointerId); } catch (e) { /* already released */ }
        }
        // one more render with a fresh scale and the normal marker size
        el._pcState.onChange(null, null, null);
    }
    el.addEventListener("pointerup", endDrag);
    el.addEventListener("pointercancel", endDrag);
}
