/*
 * damchart.js - dependency-free, responsive SVG cross-section of a river/dam
 * channel. Reused by the dashboard station form and the public site.
 *
 * renderDamChart(container, values, options)
 *   container : DOM element, CSS selector, or jQuery object.
 *   values    : one cross-section, drawn left -> right. Every level is an
 *               elevation on a common datum (metres above MSL). Numbers or
 *               numeric strings; blank / non-numeric are skipped.
 *     leftBankOuter,  leftBankInner   - left bank: outer (UP) and inner (DOWN) top
 *     rightBankInner, rightBankOuter  - right bank: inner (DOWN) and outer (UP) top
 *     bedLeft, bedRight               - channel bottom: left (UP) and right (DOWN)
 *     warningUp,  warningDown         - warning stage lines (2)
 *     criticalUp, criticalDown        - critical stage lines (2)
 *     zeroUp,     zeroDown            - staff-gauge zero / datum lines (2)
 *     waterLevel                      - optional live water surface
 *   options   : { xTitle, yTitle } axis titles (localized text from statictext).
 *
 * The channel is a trapezoid whose vertices are the bank/bed points, so each
 * value lands at its own position and moves independently. The vertical scale is
 * derived from the supplied values; higher value == higher on the chart.
 */
function renderDamChart(container, values, options) {
    var el = typeof container === "string"
        ? document.querySelector(container)
        : (container && container.jquery ? container[0] : container);
    if (!el) return;

    values = values || {};
    options = options || {};

    function num(v) {
        if (v === null || v === undefined || String(v).trim() === "") return null;
        var n = parseFloat(v);
        return isNaN(n) ? null : n;
    }
    function or(a, b) { return a === null || a === undefined ? b : a; }
    function esc(s) { return String(s === undefined ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
    function r1(n) { return Math.round(n * 10) / 10; }
    function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }
    function mean(a) { var s = 0, c = 0; for (var i = 0; i < a.length; i++) if (a[i] !== null) { s += a[i]; c++; } return c ? s / c : null; }

    var v = {
        leftBankOuter: num(values.leftBankOuter),
        leftBankInner: num(values.leftBankInner),
        rightBankInner: num(values.rightBankInner),
        rightBankOuter: num(values.rightBankOuter),
        bedLeft: num(values.bedLeft),
        bedRight: num(values.bedRight),
        warningUp: num(values.warningUp),
        warningDown: num(values.warningDown),
        criticalUp: num(values.criticalUp),
        criticalDown: num(values.criticalDown),
        zeroUp: num(values.zeroUp),
        zeroDown: num(values.zeroDown),
        waterLevel: num(values.waterLevel),
    };

    // geometry (viewBox units); modest font sizes so nothing looks oversized
    var W = 380, H = 236, padL = 40, padR = 12, padT = 14, padB = 26;
    var plotW = W - padL - padR, plotH = H - padT - padB;
    var px0 = padL, px1 = W - padR, baseY = padT + plotH;

    var nums = [];
    for (var k in v) { if (v[k] !== null) nums.push(v[k]); }
    var hasData = nums.length > 0;

    var vmin, vmax, defTop, defBed;
    if (hasData) {
        vmax = Math.max.apply(null, nums);
        vmin = Math.min.apply(null, nums);
        if (vmax === vmin) { vmax += 1; vmin -= 1; }
        var raw = vmax - vmin;
        vmax += raw * 0.35;   // head-room above the crest (~70% up)
        vmin -= raw * 0.10;   // a little earth below the bed
        var rng = vmax - vmin;
        defTop = vmax - rng * 0.32;
        defBed = vmin + rng * 0.12;
    } else {
        vmin = 0; vmax = 100; defTop = 72; defBed = 20;
    }
    var vrange = vmax - vmin || 1;
    function y(val) { return padT + (vmax - val) / vrange * plotH; }

    // resolve the 6 profile vertices (fallbacks keep the shape drawable)
    var LBO = or(v.leftBankOuter, or(v.leftBankInner, defTop));
    var LBI = or(v.leftBankInner, or(v.leftBankOuter, defTop));
    var RBO = or(v.rightBankOuter, or(v.rightBankInner, defTop));
    var RBI = or(v.rightBankInner, or(v.rightBankOuter, defTop));
    var BL = or(v.bedLeft, or(v.bedRight, defBed));
    var BR = or(v.bedRight, or(v.bedLeft, defBed));

    // trapezoid breakpoints in an abstract 0..100 distance
    var LC = 18, LS = 34, RS = 66, RC = 82;
    function x(d) { return px0 + d / 100 * plotW; }

    var top =
        "M " + x(0).toFixed(1) + " " + y(LBO).toFixed(1) +
        " L " + x(LC).toFixed(1) + " " + y(LBI).toFixed(1) +
        " L " + x(LS).toFixed(1) + " " + y(BL).toFixed(1) +
        " L " + x(RS).toFixed(1) + " " + y(BR).toFixed(1) +
        " L " + x(RC).toFixed(1) + " " + y(RBI).toFixed(1) +
        " L " + x(100).toFixed(1) + " " + y(RBO).toFixed(1);
    var earth = top + " L " + x(100).toFixed(1) + " " + baseY + " L " + x(0).toFixed(1) + " " + baseY + " Z";

    // water pool: flat surface at wl, bounded by the inner slopes + bed line
    var minInner = Math.min(LBI, RBI), minBed = Math.min(BL, BR);
    var wl = or(v.waterLevel, or(mean([v.zeroUp, v.zeroDown]), minBed + (minInner - minBed) * 0.5));
    wl = clamp(wl, minBed, minInner);
    var water = "", surfX0 = 0, surfX1 = 0;
    if (wl > minBed && LBI > BL && RBI > BR) {
        var xL = LC + (LS - LC) * clamp((wl - LBI) / (BL - LBI), 0, 1);
        var xR = RS + (RC - RS) * clamp((wl - BR) / (RBI - BR), 0, 1);
        surfX0 = x(xL); surfX1 = x(xR);
        water =
            "M " + surfX0.toFixed(1) + " " + y(wl).toFixed(1) +
            " L " + x(LS).toFixed(1) + " " + y(BL).toFixed(1) +
            " L " + x(RS).toFixed(1) + " " + y(BR).toFixed(1) +
            " L " + surfX1.toFixed(1) + " " + y(wl).toFixed(1) + " Z";
    }

    // horizontal grid + elevation ticks
    var grid = "", yticks = "", ny = 5, gstep = vrange / ny;
    for (var i = 0; i <= ny; i++) {
        var gv = vmin + gstep * i, gy = y(gv).toFixed(1);
        grid += '<line x1="' + px0 + '" y1="' + gy + '" x2="' + px1 + '" y2="' + gy + '" stroke="#e5eaf0" stroke-width="0.6"/>';
        if (hasData) yticks += '<text x="' + (px0 - 4) + '" y="' + (parseFloat(gy) + 2.4) + '" text-anchor="end" font-size="6.4" fill="#7a8794">' + r1(gv) + "</text>";
    }

    // horizontal reference line with a small value tag (UP -> left, DOWN -> right)
    function hline(val, color, right, dashed) {
        if (val === null) return "";
        var yy = y(val).toFixed(1);
        var line = '<line x1="' + px0 + '" y1="' + yy + '" x2="' + px1 + '" y2="' + yy + '" stroke="' + color + '" stroke-width="' + (dashed ? 0.9 : 1.2) + '"' + (dashed ? ' stroke-dasharray="4 3"' : "") + "/>";
        var tx = right ? (px1 - 25) : px0;
        var tag = '<rect x="' + tx + '" y="' + (parseFloat(yy) - 6.5) + '" width="25" height="9.5" rx="2" fill="' + color + '"/>' +
            '<text x="' + (tx + 12.5) + '" y="' + (parseFloat(yy) + 0.6) + '" text-anchor="middle" font-size="6.2" fill="#fff">' + r1(val) + "</text>";
        return line + tag;
    }

    // ground elevation at any distance d (0..100) along the profile, so glyphs
    // sit exactly on the terrain even where the crest slopes outer -> inner
    function lerp(a, b, t) { return a + (b - a) * t; }
    function terrainAt(d) {
        if (d <= LC) return lerp(LBO, LBI, d / LC);
        if (d <= LS) return lerp(LBI, BL, (d - LC) / (LS - LC));
        if (d <= RS) return lerp(BL, BR, (d - LS) / (RS - LS));
        if (d <= RC) return lerp(BR, RBI, (d - RS) / (RC - RS));
        return lerp(RBI, RBO, (d - RC) / (100 - RC));
    }
    var dpx = 100 / plotW;   // distance units per viewBox px

    // station: a small gauging hut on stilts, feet planted on the left crest
    var sd = 9, sx = x(sd), sAvail = y(terrainAt(sd)) - padT;
    var sH = clamp(sAvail * 0.9, 12, 30);
    var legH = sH * 0.30, bodyH = sH * 0.42, roofH = sH * 0.20;
    var bw = sH * 0.5, hbw = bw / 2;
    var lx1 = sx - hbw * 0.7, lx2 = sx + hbw * 0.7;
    var g1 = y(terrainAt(sd - hbw * 0.7 * dpx)), g2 = y(terrainAt(sd + hbw * 0.7 * dpx));
    var platY = Math.min(g1, g2) - legH, bodyTop = platY - bodyH, roofTop = bodyTop - roofH;
    var station =
        // stilts (each foot on its own ground point) + cross brace
        '<g stroke="#8b98a6" stroke-width="1" fill="none">' +
        '<line x1="' + lx1.toFixed(1) + '" y1="' + g1.toFixed(1) + '" x2="' + lx1.toFixed(1) + '" y2="' + platY.toFixed(1) + '"/>' +
        '<line x1="' + lx2.toFixed(1) + '" y1="' + g2.toFixed(1) + '" x2="' + lx2.toFixed(1) + '" y2="' + platY.toFixed(1) + '"/>' +
        '<line x1="' + lx1.toFixed(1) + '" y1="' + (platY + legH * 0.55).toFixed(1) + '" x2="' + lx2.toFixed(1) + '" y2="' + (platY + legH * 0.55).toFixed(1) + '" stroke-width="0.6"/>' +
        "</g>" +
        // platform
        '<rect x="' + (sx - hbw - 1.2).toFixed(1) + '" y="' + platY.toFixed(1) + '" width="' + (bw + 2.4).toFixed(1) + '" height="1.6" fill="#b7c0ca"/>' +
        // body
        '<rect x="' + (sx - hbw).toFixed(1) + '" y="' + bodyTop.toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + bodyH.toFixed(1) + '" rx="0.8" fill="#f2f5f8" stroke="#aab4bf" stroke-width="0.7"/>' +
        // door (left) + window (right)
        '<rect x="' + (sx - hbw * 0.75).toFixed(1) + '" y="' + (bodyTop + bodyH * 0.38).toFixed(1) + '" width="' + (hbw * 0.55).toFixed(1) + '" height="' + (bodyH * 0.62).toFixed(1) + '" rx="0.4" fill="#7f8c99"/>' +
        '<rect x="' + (sx + hbw * 0.1).toFixed(1) + '" y="' + (bodyTop + bodyH * 0.25).toFixed(1) + '" width="' + (hbw * 0.7).toFixed(1) + '" height="' + (bodyH * 0.32).toFixed(1) + '" rx="0.4" fill="#8ec5e6"/>' +
        // gable roof with a slight overhang
        '<path d="M ' + (sx - hbw - 1.6).toFixed(1) + ' ' + bodyTop.toFixed(1) + ' L ' + sx.toFixed(1) + ' ' + roofTop.toFixed(1) + ' L ' + (sx + hbw + 1.6).toFixed(1) + ' ' + bodyTop.toFixed(1) + ' Z" fill="#5f6f7e"/>' +
        // solar panel lying on the right roof slope
        '<rect x="' + (sx + hbw * 0.2).toFixed(1) + '" y="' + (roofTop + roofH * 0.45).toFixed(1) + '" width="' + (hbw * 0.85).toFixed(1) + '" height="1.7" rx="0.4" fill="#3f7bbf" transform="rotate(' + (Math.atan2(roofH, hbw + 1.6) * 180 / Math.PI).toFixed(1) + ' ' + sx.toFixed(1) + ' ' + roofTop.toFixed(1) + ')"/>';

    // tree planted on the right crest (clamped)
    var td = 91, tx = x(td), ty = y(terrainAt(td)), tAvail = ty - padT;
    var fr = clamp(tAvail * 0.32, 3, 8), trunkH = clamp(tAvail - fr * 2, 4, 12), fcy = ty - trunkH - fr;
    var tree =
        '<rect x="' + (tx - 1.4) + '" y="' + (ty - trunkH).toFixed(1) + '" width="2.8" height="' + trunkH.toFixed(1) + '" fill="#8a5a2b"/>' +
        '<circle cx="' + tx + '" cy="' + fcy.toFixed(1) + '" r="' + fr.toFixed(1) + '" fill="#5aa469"/>' +
        '<circle cx="' + (tx - fr * 0.75) + '" cy="' + (fcy + fr * 0.6).toFixed(1) + '" r="' + (fr * 0.75).toFixed(1) + '" fill="#69b378"/>' +
        '<circle cx="' + (tx + fr * 0.75) + '" cy="' + (fcy + fr * 0.6).toFixed(1) + '" r="' + (fr * 0.75).toFixed(1) + '" fill="#69b378"/>';

    // subtle value labels at the bank vertices + bed
    function vtx(cx, val, anchor, dy) {
        if (val === null) return "";
        return '<text x="' + cx + '" y="' + (y(val) + dy).toFixed(1) + '" text-anchor="' + anchor + '" font-size="5.6" fill="#7a5c33">' + r1(val) + "</text>";
    }
    var labels = "";
    if (hasData) {
        labels += vtx(x(0) + 1, v.leftBankOuter, "start", -2.4);
        labels += vtx(x(LC), v.leftBankInner, "middle", -2.4);
        labels += vtx(x(RC), v.rightBankInner, "middle", -2.4);
        labels += vtx(x(100) - 1, v.rightBankOuter, "end", -2.4);
        labels += vtx(x(LS), v.bedLeft, "middle", 7);
        labels += vtx(x(RS), v.bedRight, "middle", 7);
    }

    var titles = "";
    if (options.xTitle) titles += '<text x="' + (px0 + plotW / 2) + '" y="' + (H - 1) + '" text-anchor="middle" font-size="6.8" fill="#566270">' + esc(options.xTitle) + "</text>";
    if (options.yTitle) titles += '<text x="9" y="' + (padT + plotH / 2) + '" text-anchor="middle" font-size="6.8" fill="#566270" transform="rotate(-90 9 ' + (padT + plotH / 2) + ')">' + esc(options.yTitle) + "</text>";

    var svg =
        '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" preserveAspectRatio="xMidYMid meet" style="display:block">' +
        '<defs>' +
        '<linearGradient id="dc-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#dcecfb"/><stop offset="1" stop-color="#f5faff"/></linearGradient>' +
        '<linearGradient id="dc-water" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7cc6ee"/><stop offset="1" stop-color="#2b7fc4"/></linearGradient>' +
        '<linearGradient id="dc-earth" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e3caa1"/><stop offset="1" stop-color="#a5834f"/></linearGradient>' +
        "</defs>" +
        '<rect x="' + px0 + '" y="' + padT + '" width="' + plotW + '" height="' + plotH + '" fill="url(#dc-sky)"/>' +
        grid +
        '<path d="' + earth + '" fill="url(#dc-earth)" stroke="#8a6d3b" stroke-width="0.7"/>' +
        // grass caps on the outer->inner crest segments
        '<line x1="' + x(0) + '" y1="' + y(LBO).toFixed(1) + '" x2="' + x(LC) + '" y2="' + y(LBI).toFixed(1) + '" stroke="#6fae54" stroke-width="1.6"/>' +
        '<line x1="' + x(RC) + '" y1="' + y(RBI).toFixed(1) + '" x2="' + x(100) + '" y2="' + y(RBO).toFixed(1) + '" stroke="#6fae54" stroke-width="1.6"/>' +
        (water ? '<path d="' + water + '" fill="url(#dc-water)" opacity="0.94"/>' +
            '<line x1="' + surfX0.toFixed(1) + '" y1="' + y(wl).toFixed(1) + '" x2="' + surfX1.toFixed(1) + '" y2="' + y(wl).toFixed(1) + '" stroke="#cbe8fa" stroke-width="0.8"/>' : "") +
        // datum (zero-gauge) dashed lines
        hline(v.zeroUp, "#7b8794", false, true) +
        hline(v.zeroDown, "#7b8794", true, true) +
        // warning / critical stage lines (UP left, DOWN right)
        hline(v.warningUp, "#f0a020", false, false) +
        hline(v.warningDown, "#f0a020", true, false) +
        hline(v.criticalUp, "#e23b3b", false, false) +
        hline(v.criticalDown, "#e23b3b", true, false) +
        station + tree +
        '<rect x="' + px0 + '" y="' + padT + '" width="' + plotW + '" height="' + plotH + '" fill="none" stroke="#ced4da" stroke-width="0.8"/>' +
        yticks + titles + labels +
        "</svg>";

    el.innerHTML = svg;
}
