let pagePermission = [1, 2, 3];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}

let mapContainerID = "mapContainer";
mapMonitor(mapContainerID);

// ---------------------------------------------------------------------------
// Dashboard overview: one GET /main/summary every REFRESH_MS, rendered into
// the KPI cards, ECharts panels, attention list, worker table and system tiles
// (templates/dashboard/main/index.html). All labels come from
// LOCAL_VARIABLES.StaticText.DashboardSummary.
// ---------------------------------------------------------------------------
(function () {
    const REFRESH_MS = 60 * 1000;
    const ST = LOCAL_VARIABLES.StaticText;
    const T = ST.DashboardSummary || {};
    const root = $(".dash-overview");
    if (!root.length || typeof echarts === "undefined") {
        return;
    }
    const isAdmin = root.data("admin") == 1;
    const LEVEL_COLORS = Object.fromEntries(Object.entries(ST.WaterLevelTypes).map(([k, v]) => [k, v.color]));
    const HTTP_COLORS = { 0: "#6c757d", 1: "#198754", 2: "#dc3545" };
    const EVENT_COLORS = { 0: "#6c757d", 1: "#dc3545", 2: "#212529" };

    let charts = {};
    let lastFetched = null;
    // Server clock at the last /main/summary (generated_at) and the browser time
    // it arrived: every "x ago" is computed against the server clock, so the
    // dashboard stays right when the browser sits in another time zone than the
    // server (all timestamps are server-local, without a zone).
    let serverClock = null;
    let workerJobs = [];
    let uptimeBase = null;

    // -------------------------------------------------------------- helpers
    function textColor() {
        return getComputedStyle(document.body).color || "#333";
    }
    function mutedColor() {
        return getComputedStyle(document.body).getPropertyValue("--bs-secondary-color") || "#6c757d";
    }
    function fmtBytes(bytes) {
        if (bytes === null || bytes === undefined) return "-";
        const units = ["B", "KB", "MB", "GB", "TB"];
        let i = 0;
        let v = Number(bytes);
        while (v >= 1024 && i < units.length - 1) {
            v /= 1024;
            i++;
        }
        return `${v.toFixed(v >= 100 || i === 0 ? 0 : 1)} ${units[i]}`;
    }
    function fmtDuration(seconds) {
        seconds = Math.max(0, Math.round(seconds || 0));
        const d = Math.floor(seconds / 86400);
        const h = Math.floor((seconds % 86400) / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        const parts = [];
        if (d) parts.push(`${d}${T.Days || "d"}`);
        if (d || h) parts.push(`${h}${T.Hours || "h"}`);
        parts.push(`${m}${T.Minutes || "m"}`);
        if (!d) parts.push(`${s}${T.Seconds || "s"}`);
        return parts.join(" ");
    }
    // "now" on the server: generated_at plus the time elapsed since it arrived
    function serverNow() {
        return serverClock ? moment(serverClock.server).add(Date.now() - serverClock.at, "ms") : moment();
    }
    function fmtAgo(value, reference = null) {
        if (!value) return "-";
        const diff = Math.max(0, (reference || serverNow()).diff(moment(value), "seconds"));
        if (diff < 5) return T.JustNow;
        return `${fmtDuration(diff)} ${T.Ago}`;
    }
    function fmtTime(value, format = "HH:mm:ss") {
        return value ? moment(value).format(format) : "-";
    }
    function escapeHtml(text) {
        return $("<div>").text(text === null || text === undefined ? "" : text).html();
    }

    // Animated counters: tween from the current displayed value to the new one.
    function animateNumber(el, value, decimals = 0) {
        el = $(el);
        const from = parseFloat(String(el.text()).replace(/[^\d.-]/g, "")) || 0;
        const to = Number(value) || 0;
        if (from === to) {
            el.text(to.toFixed(decimals));
            return;
        }
        $({ n: from }).animate(
            { n: to },
            {
                duration: 700,
                easing: "swing",
                step: function () {
                    el.text(this.n.toFixed(decimals));
                },
                complete: function () {
                    el.text(to.toFixed(decimals));
                },
            }
        );
    }
    function setBar(name, percent) {
        root.find(`[data-bar='${name}']`).css("width", `${Math.max(0, Math.min(100, percent || 0))}%`);
    }

    function chart(id) {
        const el = document.getElementById(id);
        if (!el) return null;
        if (!charts[id]) {
            charts[id] = echarts.init(el, null, { renderer: "canvas" });
        }
        return charts[id];
    }

    // --------------------------------------------------------------- panels
    function renderStations(data) {
        animateNumber(root.find("[data-kpi='stations']"), data.total);
        let total = 0;
        Object.entries(data.counts).forEach(([level, n]) => {
            animateNumber(root.find(`[data-kpi='level-${level}']`), n);
            total += n;
        });
        // pulse the Critical card while any station is critical
        root.find(".kpi-card[data-level='2']").toggleClass("pulse", (data.counts[2] || 0) > 0);

        const c = chart("dashStatusChart");
        if (c) {
            c.setOption({
                animationDuration: 800,
                animationEasing: "cubicOut",
                color: Object.values(LEVEL_COLORS),
                tooltip: { textStyle: { fontSize: 12 }, trigger: "item", formatter: "{b}: {c} ({d}%)" },
                legend: { bottom: 0, icon: "circle", itemWidth: 8, itemHeight: 8, textStyle: { color: textColor(), fontSize: 11 } },
                series: [
                    {
                        type: "pie",
                        radius: ["58%", "80%"],
                        center: ["50%", "42%"],
                        avoidLabelOverlap: true,
                        label: { show: false },
                        emphasis: { scale: true, scaleSize: 6 },
                        itemStyle: { borderColor: "rgba(255,255,255,0.6)", borderWidth: 2 },
                        data: Object.entries(ST.WaterLevelTypes).map(([k, v]) => ({
                            name: v.text_en,
                            value: data.counts[k] || 0,
                            itemStyle: { color: v.color },
                        })),
                    },
                    {
                        // centre label: total
                        type: "pie",
                        radius: [0, "56%"],
                        center: ["50%", "42%"],
                        silent: true,
                        label: {
                            position: "center",
                            formatter: `{n|${total}}\n{t|${T.Stations}}`,
                            rich: {
                                n: { fontSize: 22, fontWeight: 600, color: textColor() },
                                t: { fontSize: 11, color: mutedColor() },
                            },
                        },
                        data: [{ value: 1, itemStyle: { color: "transparent" } }],
                    },
                ],
            });
        }

        // attention list
        const list = root.find(".dash-attention").empty();
        const items = data.attention || [];
        root.find("[data-kpi='attention-count']").text(items.length);
        root.find(".dash-attention-empty").toggleClass("d-none", items.length > 0);
        items.forEach((row, i) => {
            const type = ST.WaterLevelTypes[row.WaterLevelType] || {};
            const wl = row.WaterLevel !== null && row.WaterLevel !== undefined ? `${row.WaterLevel} m` : "";
            list.append(`
                <li class="list-group-item px-0 py-2 d-flex align-items-center gap-2 fade-in" style="animation-delay:${Math.min(i, 12) * 40}ms">
                    <span class="status-dot flex-shrink-0" style="background:${type.color}"></span>
                    <div class="flex-fill min-w-0">
                        <div class="d-flex justify-content-between gap-2">
                            <a class="fw-semibold text-truncate text-reset" href="/dashboard/stations/${row.StationID}" title="${T.OpenStation}">${escapeHtml(row.SiteCode)} - ${escapeHtml(row.SiteName)}</a>
                            <span class="small text-nowrap" style="color:${type.color}">${escapeHtml(type.text_en)}</span>
                        </div>
                        <div class="small text-muted d-flex justify-content-between">
                            <span>${wl}</span>
                            <span>${row.RecordTime ? fmtAgo(row.RecordTime) : ""}</span>
                        </div>
                    </div>
                </li>`);
        });
    }

    function renderPayloads(data) {
        animateNumber(root.find("[data-kpi='today']"), data.today);
        root.find("[data-kpi='last']").text(data.last ? fmtAgo(data.last) : "-").attr("title", data.last || "");
        const c = chart("dashPayloadChart");
        if (!c) return;
        const primary = getComputedStyle(document.documentElement).getPropertyValue("--bs-primary").trim() || "#0d6efd";
        c.setOption({
            animationDuration: 900,
            animationEasing: "cubicOut",
            grid: { left: 36, right: 12, top: 16, bottom: 28 },
            tooltip: { textStyle: { fontSize: 12 },
                trigger: "axis",
                axisPointer: { type: "line", lineStyle: { color: mutedColor(), type: "dashed" } },
                formatter: (p) => `${p[0].axisValue}<br>${p[0].marker} ${p[0].value}`,
            },
            xAxis: {
                type: "category",
                data: data.series.map((r) => fmtTime(r.t, "HH:00")),
                axisTick: { show: false },
                axisLine: { lineStyle: { color: mutedColor() } },
                axisLabel: { color: mutedColor(), fontSize: 10, interval: 2 },
            },
            yAxis: {
                type: "value",
                minInterval: 1,
                splitLine: { lineStyle: { color: "rgba(128,128,128,0.15)" } },
                axisLabel: { color: mutedColor(), fontSize: 10 },
            },
            series: [
                {
                    type: "line",
                    smooth: 0.35,
                    showSymbol: false,
                    symbolSize: 6,
                    data: data.series.map((r) => r.n),
                    lineStyle: { width: 2.5, color: primary },
                    itemStyle: { color: primary, borderColor: "#fff", borderWidth: 2 },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: echarts.color.modifyAlpha(primary, 0.35) },
                            { offset: 1, color: echarts.color.modifyAlpha(primary, 0.02) },
                        ]),
                    },
                    markPoint: {
                        symbol: "pin",
                        symbolSize: 34,
                        itemStyle: { color: primary },
                        label: { color: "#fff", fontSize: 10 },
                        data: [{ type: "max" }],
                    },
                    emphasis: { focus: "series" },
                },
            ],
        });
    }

    function renderHttp(counters) {
        let total = 0;
        Object.entries(ST.HttpLogStatuses).forEach(([k]) => {
            const n = Number(counters[k] || 0);
            total += n;
            animateNumber(root.find(`[data-kpi='http-${k}']`), n);
            root.find(`.dash-http-dot-${k}`).css("background", HTTP_COLORS[k]);
        });
        const c = chart("dashHttpChart");
        if (!c) return;
        c.setOption({
            animationDuration: 800,
            tooltip: { textStyle: { fontSize: 12 }, trigger: "item", formatter: "{b}: {c}" },
            series: [
                {
                    type: "pie",
                    radius: ["66%", "92%"],
                    label: { show: true, position: "center", formatter: String(total), fontSize: 16, fontWeight: 600, color: textColor() },
                    itemStyle: { borderColor: "rgba(255,255,255,0.6)", borderWidth: 2 },
                    emphasis: { label: { show: true } },
                    data: Object.entries(ST.HttpLogStatuses).map(([k, v]) => ({
                        name: v.text,
                        value: Number(counters[k] || 0),
                        itemStyle: { color: HTTP_COLORS[k] },
                    })),
                },
            ],
        });
    }

    function renderEvents(counters) {
        Object.entries(ST.EventLogStatuses).forEach(([k]) => {
            animateNumber(root.find(`[data-kpi='event-${k}']`), Number(counters[k] || 0));
            root.find(`.dash-event-${k}`).css("box-shadow", `inset 3px 0 0 ${EVENT_COLORS[k]}`);
        });
    }

    function renderWorker(worker) {
        if (!worker) return;
        workerJobs = worker.jobs || [];
        const state = !worker.alive ? T.WorkerStopped : worker.enabled === false ? T.WorkerDisabled : T.WorkerAlive;
        const color = !worker.alive ? "#dc3545" : worker.enabled === false ? "#ffc107" : "#198754";
        root.find(".dash-worker-state").text(state);
        root.find(".dash-worker-dot").css("background", color).toggleClass("pulse-dot", worker.alive && worker.enabled !== false);
        root.find(".dash-worker-started").text(fmtTime(worker.started_at, "YYYY-MM-DD HH:mm"));
        root.find(".dash-worker-tick").text(fmtAgo(worker.last_tick)).attr("title", worker.last_tick || "");

        const body = root.find(".dash-worker-table tbody").empty();
        workerJobs.forEach((job) => {
            const name = (ST.WorkerJobs || {})[job.name] || job.name;
            const ok = !job.error;
            const result = job.error ? job.error : job.result || "";
            body.append(`
                <tr class="fade-in" data-job="${job.name}">
                    <td class="text-nowrap"><span class="status-dot me-2" style="background:${job.runs ? (ok ? "#198754" : "#dc3545") : "#adb5bd"}"></span>${escapeHtml(name)}</td>
                    <td class="text-end text-muted small">${fmtDuration(job.interval)}</td>
                    <td class="small text-muted">${escapeHtml(job.schedule || "")}</td>
                    <td class="small text-nowrap" title="${job.last_run || ""}">${job.last_run ? fmtAgo(job.last_run) : T.NeverRun}</td>
                    <td class="small text-nowrap"><span class="dash-next" data-next="${job.next_in === null ? "" : job.next_in}">${job.next_in === null ? "-" : fmtDuration(job.next_in)}</span></td>
                    <td class="text-end small text-muted">${job.duration === null || job.duration === undefined ? "-" : `${(job.duration * 1000).toFixed(0)} ms`}</td>
                    <td class="text-end small">${job.runs}${job.errors ? ` <span class="text-danger">(${job.errors})</span>` : ""}</td>
                    <td class="${ok ? "text-muted" : "text-danger"}"><span class="dash-result" title="${escapeHtml(result)}">${result ? escapeHtml(result) : "&ndash;"}</span></td>
                </tr>`);
        });
    }

    function renderSystem(sys) {
        if (!sys) return;
        uptimeBase = { uptime: sys.uptime, at: Date.now() };
        root.find("[data-sys='uptime']").text(fmtDuration(sys.uptime));
        root.find("[data-sys='mode']").text(sys.debug ? T.Debug : T.Production);
        root.find("[data-sys='platform']").text(sys.platform);
        root.find("[data-sys='host']").text(sys.host);
        root.find("[data-sys='pid']").text(sys.pid);
        root.find("[data-sys='python']").text(sys.python);

        root.find("[data-sys='cpu-count']").text(sys.cpu_count ? `(${sys.cpu_count})` : "");
        animateNumber(root.find("[data-sys='cpu']"), sys.cpu ?? 0, 1);
        setBar("cpu", sys.cpu);

        const mem = sys.memory || {};
        animateNumber(root.find("[data-sys='mem']"), mem.percent ?? 0, 1);
        setBar("mem", mem.percent);
        root.find("[data-sys='mem-text']").text(`${fmtBytes(mem.used)} / ${fmtBytes(mem.total)}`);
        root.find("[data-sys='process']").text(fmtBytes(mem.process));

        const disk = sys.disk || {};
        root.find("[data-sys='disk-path']").text(disk.path || "");
        animateNumber(root.find("[data-sys='disk']"), disk.percent ?? 0, 1);
        setBar("disk", disk.percent);
        root.find("[data-sys='disk-text']").text(`${fmtBytes(disk.free)} ${T.Free} / ${fmtBytes(disk.total)}`);
        root.find("[data-bar='disk']").toggleClass("bg-danger", (disk.percent || 0) > 90).toggleClass("bg-warning", (disk.percent || 0) <= 90);

        const dbi = sys.database || {};
        root.find("[data-sys='db-size']").text(fmtBytes(dbi.size));
        root.find("[data-sys='db-conn']").text(dbi.connections ?? "-");
        root.find("[data-sys='db-version']").text(dbi.version || "");
        const c = chart("dashTableChart");
        if (c) {
            const tables = (dbi.tables || []).slice().reverse();
            c.setOption({
                animationDuration: 800,
                grid: { left: 4, right: 56, top: 4, bottom: 4, containLabel: true },
                tooltip: { textStyle: { fontSize: 12 },
                    trigger: "item",
                    formatter: (p) => `${p.name}<br>${fmtBytes(p.value)} &middot; ${tables[p.dataIndex].rows.toLocaleString()} ${T.Rows}`,
                },
                xAxis: { type: "value", show: false },
                yAxis: {
                    type: "category",
                    data: tables.map((t) => t.name.replace(/^tbl_/, "")),
                    axisTick: { show: false },
                    axisLine: { show: false },
                    axisLabel: { color: mutedColor(), fontSize: 10 },
                },
                series: [
                    {
                        type: "bar",
                        data: tables.map((t) => t.size),
                        barMaxWidth: 12,
                        itemStyle: { borderRadius: [0, 4, 4, 0], color: "#0dcaf0" },
                        label: { show: true, position: "right", fontSize: 10, color: mutedColor(), formatter: (p) => fmtBytes(p.value) },
                    },
                ],
            });
        }

        const folders = root.find(".dash-folders").empty();
        const maxSize = Math.max(1, ...(sys.folders || []).map((f) => f.size));
        (sys.folders || []).forEach((f) => {
            folders.append(`
                <li class="mb-1">
                    <div class="d-flex justify-content-between align-items-baseline">
                        <span class="dash-folder-name ${f.exists ? "" : "text-muted"}" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</span>
                        <span class="dash-folder-size text-muted"><span class="fw-semibold text-body">${fmtBytes(f.size)}</span> &middot; ${Number(f.files).toLocaleString()} ${T.Files}</span>
                    </div>
                    <div class="progress dash-progress" style="height: 3px;"><div class="progress-bar bg-info" style="width: ${(100 * f.size) / maxSize}%"></div></div>
                </li>`);
        });
    }

    // ------------------------------------------------------------- refresh
    function load() {
        root.find(".dash-refresh").addClass("spin");
        $.getJSON("/main/summary")
            .done((data) => {
                lastFetched = Date.now();
                if (data.generated_at) {
                    serverClock = { server: data.generated_at, at: lastFetched };
                }
                root.find("[data-kpi='timeout']").text(data.timeout_minutes);
                renderStations(data.stations);
                renderPayloads(data.payloads);
                renderHttp(data.http || {});
                renderEvents(data.events || {});
                if (isAdmin) {
                    renderWorker(data.worker);
                    renderSystem(data.system);
                }
            })
            .fail((jqXHR) => {
                const res = jqXHR.responseJSON;
                if (res && res.Message) {
                    toastr.error(res.Message, res.Title);
                }
            })
            .always(() => root.find(".dash-refresh").removeClass("spin"));
    }

    // 1 s ticker: "updated x ago", next-run countdowns, uptime
    function tick() {
        root.find(".dash-updated-text").text(lastFetched ? `${T.Updated} ${fmtAgo(lastFetched, moment())}` : "");
        root.find(".dash-next").each(function () {
            const el = $(this);
            const raw = el.attr("data-next");
            if (raw === "") return;
            const left = Math.max(0, Number(raw) - 1);
            el.attr("data-next", left).text(fmtDuration(left));
        });
        if (uptimeBase) {
            root.find("[data-sys='uptime']").text(fmtDuration(uptimeBase.uptime + (Date.now() - uptimeBase.at) / 1000));
        }
    }

    root.on("click", ".dash-refresh", load);
    $(window).on("resize", () => Object.values(charts).forEach((c) => c.resize()));
    // re-theme charts when the dark-mode switch flips the root attribute
    new MutationObserver(() => load()).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    load();
    setInterval(load, REFRESH_MS);
    setInterval(tick, 1000);
})();
