// Public Statistics page (front design slide 9): one ECharts line per checked
// parameter for the selected station and period (POST /api/stationdata/series
// per parameter); CSV export of the fetched points and print.
(function () {
    const ST = LOCAL_VARIABLES.StaticText;
    const T = (ST.FrontPage || {}).Statistics || {};
    const PARAMS = ST.StationDataParameters || {};
    const page = $(".statistics-page");
    if (!page.length) {
        return;
    }

    const charts = {};
    let lastSeries = {};

    function filters() {
        let out = {};
        page.find(".stat-filters :input[name]").serializeArray().forEach(function (item) {
            if (item.value.trim() !== "") {
                out[item.name] = item.value;
            }
        });
        return out;
    }

    function selectedParams() {
        return page.find(".stat-params input:checked").map((i, el) => el.value).get();
    }

    function colors() {
        return {
            muted: getComputedStyle(document.body).getPropertyValue("--bs-secondary-color") || "#6c757d",
            palette: ["#0d6efd", "#198754", "#fd7e14", "#6f42c1", "#dc3545", "#20c997"],
        };
    }

    function chartCard(key) {
        let card = page.find(`.stat-card[data-key='${key}']`);
        if (!card.length) {
            const meta = PARAMS[key] || { text: key, unit: "" };
            card = $(`
                <div class="card mb-3 stat-card" data-key="${key}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="dash-card-title mb-0">${meta.text}${meta.unit ? ` (${meta.unit})` : ""}</div>
                            <small class="text-muted stat-info"></small>
                        </div>
                        <div class="stat-chart" style="height: 220px;"></div>
                        <div class="small text-muted text-center py-4 stat-nodata d-none">${T.NoData || ""}</div>
                    </div>
                </div>`);
            page.find(".stat-charts").append(card);
        }
        return card;
    }

    function draw(key, res, index) {
        const card = chartCard(key);
        const el = card.find(".stat-chart");
        const meta = PARAMS[key] || { text: key, unit: "" };
        const buckets = ST.StationDataBuckets || {};
        if (!res.points || !res.points.length) {
            el.addClass("d-none");
            card.find(".stat-nodata").removeClass("d-none");
            card.find(".stat-info").text("");
            return;
        }
        el.removeClass("d-none");
        card.find(".stat-nodata").addClass("d-none");
        card.find(".stat-info").text(`${buckets[res.bucket] || res.bucket} · ${res.points.length} ${T.Points || ""}`);
        const c = colors();
        const color = c.palette[index % c.palette.length];
        const aggregated = res.bucket !== "raw";
        if (!charts[key]) {
            charts[key] = echarts.init(el.get(0));
        }
        charts[key].resize();
        const series = [
            {
                name: meta.text,
                type: key === ST.StationDataKeys.Rainfall ? "bar" : "line",
                showSymbol: res.points.length <= 200,
                symbolSize: 4,
                lineStyle: { width: 2, color: color },
                itemStyle: { color: color },
                areaStyle: key === ST.StationDataKeys.Rainfall ? undefined : { color: echarts.color.modifyAlpha(color, 0.12) },
                barMaxWidth: 14,
                data: res.points.map((p) => [p.t, p.v]),
            },
        ];
        charts[key].setOption(
            {
                animationDuration: 500,
                grid: { left: 48, right: 16, top: 16, bottom: 44 },
                tooltip: { textStyle: { fontSize: 12 },
                    trigger: "axis",
                    formatter: function (items) {
                        const p = res.points[items[0].dataIndex];
                        let lines = [moment(p.t).format("YYYY-MM-DD HH:mm"), `${meta.text}: <b>${p.v}</b> ${meta.unit || ""}`];
                        if (aggregated) {
                            lines.push(`min ${p.min} · max ${p.max} · n = ${p.n}`);
                        }
                        return lines.join("<br>");
                    },
                },
                xAxis: { type: "time", axisLabel: { color: c.muted, fontSize: 10 } },
                yAxis: { type: "value", scale: true, axisLabel: { color: c.muted, fontSize: 10 }, splitLine: { lineStyle: { color: "rgba(128,128,128,0.15)" } } },
                dataZoom: [{ type: "inside" }, { type: "slider", height: 16, bottom: 6 }],
                series: series,
            },
            true
        );
    }

    function load() {
        const f = filters();
        const params = selectedParams();
        const empty = page.find(".stat-empty");
        page.find(".stat-charts .stat-card").each(function () {
            if (params.indexOf($(this).data("key")) === -1) {
                const key = $(this).data("key");
                if (charts[key]) {
                    charts[key].dispose();
                    delete charts[key];
                }
                $(this).remove();
            }
        });
        if (!f.StationID || !params.length || typeof echarts === "undefined") {
            empty.removeClass("d-none");
            page.find(".stat-csv, .stat-print").prop("disabled", true);
            return;
        }
        empty.addClass("d-none");
        lastSeries = {};
        params.forEach(function (key, index) {
            chartCard(key);
            $.ajax({
                url: "/api/stationdata/series",
                type: "POST",
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                data: JSON.stringify({ filters: $.extend({}, f, { Parameter: key }), bucket: page.find("#BucketSelect").val() }),
            }).done(function (res) {
                lastSeries[key] = res;
                draw(key, res, index);
                page.find(".stat-csv, .stat-print").prop("disabled", false);
            }).fail(ajaxFailToast);
        });
    }

    // CSV of everything currently drawn: time, then one column per parameter
    function exportCsv() {
        const keys = Object.keys(lastSeries);
        const times = {};
        keys.forEach(function (key) {
            (lastSeries[key].points || []).forEach(function (p) {
                times[p.t] = times[p.t] || {};
                times[p.t][key] = p.v;
            });
        });
        const header = ["RecordTime"].concat(keys.map((k) => `${(PARAMS[k] || {}).text || k} (${(PARAMS[k] || {}).unit || ""})`));
        const rows = Object.keys(times).sort().map((t) => [t].concat(keys.map((k) => (times[t][k] === undefined ? "" : times[t][k]))));
        const csv = "﻿" + [header].concat(rows).map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\r\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${page.find("#StationIDFilter option:selected").text().split(" ")[0] || "statistics"}_${moment().format("YYYYMMDD_HHmm")}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
    }

    $(function () {
        select2Ajax(page.find("#ProjectIDFilter"), "ProjectID", "ProjectName");
        select2Ajax(page.find("#RiverBasinIDFilter"), "RiverBasinID", "WatershedName");
        // station list follows the project / watershed filters; a preset comes from the URL
        const preset = Number($("#module-container").data("contentid")) || null;
        if (preset) {
            page.find("#StationIDFilter").attr("data-selectid", preset);
        }
        cascadeStationFilter(page);
        page.find(".datepicker").datepicker().on("changeDate clearDate", function () {
            $(this).trigger("change");
        });
        page.find("#DateFromFilter, #DateToFilter").on("change", function () {
            if ($(this).val().trim() !== "" && page.find("#RangeFilter").val() !== "custom") {
                page.find("#RangeFilter").val("custom").trigger("change.select2");
            }
            load();
        });
        page.find("#RangeFilter").on("change", function () {
            if ($(this).val() !== "custom") {
                page.find("#DateFromFilter, #DateToFilter").val("");
            }
            load();
        });
        page.find("#StationIDFilter, #BucketSelect").on("change", load);
        page.find(".stat-params input").on("change", load);
        page.find(".stat-csv").on("click", exportCsv);
        page.find(".stat-print").on("click", () => window.print());
        $(window).on("resize", () => Object.values(charts).forEach((c) => c.resize()));

        load();
    });
})();
