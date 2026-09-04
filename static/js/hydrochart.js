// hydrochart.js - ECharts hydrograph shared by the dashboard Station Data page
// and the public station page.
//
// renderHydroChart(container, res, options)
//   container : DOM element / jQuery object holding (or receiving) the chart
//   res       : response of POST /api/stationdata/series with `parameters`
//               ({ series: {key: {points, bucket}}, bucket })
//   options   : { keys: [...Data keys in drawing order], labels: StationDataParameters,
//                 keysMap: StationDataKeys, buckets: StationDataBuckets,
//                 minLabel, maxLabel }  (all labels from statictext)
//   returns   : { chart, present, total }  (present = keys that had points)
//
// Level on the left axis (Water Level area + Water Level 2 dashed), flow and
// velocity on right axes, rain as bars hanging from the top (hyetograph).
// Wetted area is never drawn (a derived helper value). Tooltip text is 12px.
function renderHydroChart(container, res, options) {
    const el = container && container.jquery ? container[0] : container;
    if (!el || typeof echarts === "undefined" || !res || !res.series) {
        return null;
    }
    options = options || {};
    const K = options.keysMap || {};
    const L = options.labels || {};
    const B = options.buckets || {};
    const keys = (options.keys || [K.WaterLevel, K.WaterLevel2, K.Rainfall, K.Velocity, K.Flow]).filter(Boolean);
    const present = keys.filter((k) => res.series[k] && res.series[k].points && res.series[k].points.length);
    if (!present.length) {
        return { chart: null, present: [], total: 0 };
    }

    const body = getComputedStyle(document.body);
    const c = {
        text: body.color || "#333",
        muted: body.getPropertyValue("--bs-secondary-color") || "#6c757d",
        primary: getComputedStyle(document.documentElement).getPropertyValue("--bs-primary").trim() || "#0d6efd",
    };
    const name = (k) => (L[k] || { text: k }).text;
    const unit = (k) => (L[k] || { unit: "" }).unit || "";
    const palette = { [K.WaterLevel]: c.primary, [K.WaterLevel2]: "#6f42c1", [K.Rainfall]: "#0dcaf0", [K.Velocity]: "#fd7e14", [K.Flow]: "#198754" };
    const axisOf = { [K.WaterLevel]: 0, [K.WaterLevel2]: 0, [K.Flow]: 1, [K.Velocity]: 2, [K.Rainfall]: 3 };
    const axisLabel = { color: c.muted, fontSize: 10 };
    const aggregated = res.bucket !== "raw";
    const rainMax = Math.max(0.1, ...((res.series[K.Rainfall] || { points: [] }).points.map((p) => p.v)));
    const total = Math.max(...present.map((k) => res.series[k].points.length));

    const series = present.map((k) => {
        const pts = res.series[k].points;
        const base = { name: name(k), yAxisIndex: axisOf[k], data: pts.map((p) => [p.t, p.v]), itemStyle: { color: palette[k] } };
        if (k === K.Rainfall) {
            return Object.assign(base, { type: "bar", barMaxWidth: 10, itemStyle: { color: echarts.color.modifyAlpha(palette[k], 0.7) } });
        }
        return Object.assign(base, {
            type: "line",
            showSymbol: pts.length <= 200,
            symbolSize: 4,
            lineStyle: { width: k === K.WaterLevel ? 2.5 : 1.5, color: palette[k], type: k === K.WaterLevel2 ? "dashed" : "solid" },
            areaStyle: k === K.WaterLevel ? { color: echarts.color.modifyAlpha(palette[k], 0.1) } : undefined,
        });
    });

    const chart = echarts.getInstanceByDom(el) || echarts.init(el);
    chart.resize();
    chart.setOption(
        {
            animationDuration: 600,
            grid: { left: 52, right: present.includes(K.Velocity) && present.includes(K.Flow) ? 96 : 56, top: 34, bottom: 52 },
            legend: { top: 0, icon: "roundRect", itemWidth: 12, itemHeight: 6, textStyle: { color: c.text, fontSize: 11 }, data: present.map((k) => name(k)) },
            tooltip: {
                textStyle: { fontSize: 12 },
                trigger: "axis",
                axisPointer: { type: "line", lineStyle: { color: c.muted, type: "dashed" } },
                formatter: function (items) {
                    const lines = [moment(items[0].value[0]).format("YYYY-MM-DD HH:mm")];
                    items.forEach((it) => {
                        const k = present[it.seriesIndex];
                        const p = res.series[k].points[it.dataIndex];
                        const extra = aggregated && p && p.min !== undefined ? ` <span style="color:${c.muted}">(${p.min} – ${p.max})</span>` : "";
                        lines.push(`${it.marker} ${it.seriesName}: <b>${it.value[1]}</b> ${unit(k)}${extra}`);
                    });
                    return lines.join("<br>");
                },
            },
            xAxis: { type: "time", axisLabel: axisLabel, axisLine: { lineStyle: { color: c.muted } } },
            yAxis: [
                { type: "value", scale: true, name: unit(K.WaterLevel), nameTextStyle: axisLabel, axisLabel: axisLabel, splitLine: { lineStyle: { color: "rgba(128,128,128,0.15)" } } },
                { type: "value", scale: true, name: unit(K.Flow), nameTextStyle: axisLabel, axisLabel: axisLabel, splitLine: { show: false }, show: present.includes(K.Flow) },
                { type: "value", scale: true, name: unit(K.Velocity), nameTextStyle: axisLabel, axisLabel: axisLabel, splitLine: { show: false }, show: present.includes(K.Velocity), offset: present.includes(K.Flow) ? 44 : 0 },
                { type: "value", inverse: true, min: 0, max: rainMax * 3, show: false },
            ],
            dataZoom: [{ type: "inside" }, { type: "slider", height: 18, bottom: 8 }],
            series: series,
        },
        true
    );
    return { chart, present, total, bucketText: B[res.bucket] || res.bucket };
}
