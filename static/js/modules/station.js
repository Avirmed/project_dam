// Public station page (/station/<id>, front design slide 8).
//   POST /api/stations/public      -> identity, specifications, newest values, rain accumulation
//   POST /api/stations/cameras     -> the station's cameras + latest snapshots
//   POST /api/eventlog/list        -> recent security events of the station
//   POST /api/stationdata/series   -> hydrograph (shared hydrochart.js)
//   POST /api/stationdata/summary  -> tiles of the measurement section
//   the payload grid below the chart is the shared Tabulator engine (project.js)
//   fed by cfg-extra-params (StationID) + the .tabulator-filters period.
(function () {
    const ST = LOCAL_VARIABLES.StaticText;
    const T = (ST.FrontPage || {}).Station || {};
    const F = ST.StationDataField || {};
    const K = ST.StationDataKeys || {};
    const page = $(".station-page");
    const stationId = Number(page.data("station")) || null;
    if (!page.length) {
        return;
    }
    if (!stationId) {
        page.find(".station-notfound").removeClass("d-none");
        return;
    }

    const fmt = (v, digits) => (v === null || v === undefined || v === "" ? "-" : isNaN(Number(v)) ? v : Number(v).toFixed(digits));
    const esc = (s) => $("<div>").text(s == null ? "" : String(s)).html();
    const when = (v, format = "DD/MM/YYYY HH:mm") => (v ? moment(v).format(format) : "-");
    const postJSON = (url, body) => $.ajax({ url, type: "POST", contentType: "application/json; charset=utf-8", dataType: "json", data: JSON.stringify(body) });
    let chart = null;

    // ------------------------------------------------------------ identity
    function render(d) {
        const type = (ST.WaterLevelTypes || {})[d.WaterLevelType] || {};
        page.find(".station-title").text(`${d.SiteCode} - ${d.SiteName}`);
        page.find(".station-subtitle").html([esc(d.ProjectName), esc(d.WatershedName), `<span class="badge rounded-pill station-status-badge" style="background:${type.color || "#7f7f7f"}">${esc(type.text_en || "")}</span>`, d.RecordTime ? `${esc(T.LastUpdate)}: ${esc(moment(d.RecordTime).fromNow())}` : ""].filter(Boolean).join(" · "));
        page.find(".station-link-stats").attr("href", `/statistics/${stationId}`);
        document.title = `${d.SiteCode} - ${d.SiteName}`;

        // measurements
        $.each(d.Values || {}, function (key, value) {
            page.find(`[data-value='${key}']`).text(fmt(value, 2));
        });
        page.find(".station-wl2-row").toggleClass("d-none", (d.Values || {}).WaterLevel2 == null || (d.Values || {}).WaterLevel2 === "");
        page.find("[data-value='RecordTime']").text(when(d.RecordTime));
        page.find("[data-value='LatestRainfall']").text(when(d.LatestRainfall));
        (d.RainAccumulation || []).forEach(function (acc) {
            const row = page.find(`tr[data-rain='${acc.days}']`);
            row.find(".rain-label").text((T.RainAcc || "{n}").replace("{n}", acc.days));
            row.find(".rain-window").text(`${when(acc.from, "HH:mm DD/MM")} – ${when(acc.to, "HH:mm DD/MM")}`);
            row.find(".rain-value").text(fmt(acc.value, 2));
        });
        // distance of the level to the warning / critical stage of Point 1
        const wl = Number((d.Values || {}).WaterLevel);
        const spec = d.Specifications || {};
        const warn = Number(spec.WARNING_UP), crit = Number(spec.CRITICAL_UP);
        if (!isNaN(wl) && (!isNaN(warn) || !isNaN(crit))) {
            const ref = !isNaN(crit) && wl >= crit ? { v: crit, label: T.Critical, color: (ST.WaterLevelTypes[2] || {}).color } : !isNaN(warn) ? { v: warn, label: T.Warning, color: (ST.WaterLevelTypes[1] || {}).color } : null;
            if (ref) {
                const diff = wl - ref.v;
                page.find(".station-wl-note").html(`<span style="color:${ref.color}">${Math.abs(diff).toFixed(2)} m ${diff >= 0 ? esc(T.Above) : esc(T.Below)} ${esc(ref.label)} (${ref.v.toFixed(2)})</span>`);
                page.find(".station-wl-note-row").removeClass("d-none");
            }
        }

        // specifications
        $.each(d.Specifications || {}, function (key, value) {
            page.find(`[data-spec='${key}']`).text(value === null || value === undefined || value === "" ? "-" : value);
        });

        // identity
        ["SiteName", "SiteCode", "DeviceID", "ProjectName", "WatershedName", "Latitude", "Longitude", "Address", "MeasuredValue", "SiteInstall", "Region"].forEach(function (key) {
            page.find(`[data-info='${key}']`).text(d[key] || "-");
        });
        // station photo: medium size in the card, the large one in the lightbox
        const stationName = `${d.SiteCode} - ${d.SiteName}`;
        page.find(".station-image").attr({ src: d.ImageMD || d.Image || ST.Images.Blank, alt: stationName, title: stationName });
        // lightbox (blueimp, data-gallery) only when the station really has a picture;
        // the default blank image stays a plain, non-clickable placeholder
        const hasImage = !!d.Image && !/blank\.png$/.test(d.Image);
        page.find(".station-image-link").attr({ href: hasImage ? d.Image : "#", title: stationName })
            .toggleClass("no-image", !hasImage)
            .each(function () { hasImage ? this.setAttribute("data-gallery", "#station-gallery") : this.removeAttribute("data-gallery"); })
            .off("click.blank").on("click.blank", function (e) { if (!hasImage) e.preventDefault(); });

        // breadcrumb: the page is not a menu entry, so the generic builder has nothing
        const crumbs = $(".page-breadcrumb .breadcrumb");
        if (crumbs.length && !crumbs.find(".station-crumb").length) {
            crumbs.append(`<li class="breadcrumb-item station-crumb"><a href="/">${esc(T.Breadcrumb || "")}</a></li>`);
            crumbs.append(`<li class="breadcrumb-item active station-crumb">${esc(d.SiteCode)}</li>`);
        }

        renderDam(d);
        bilingualLabels();
        page.find(".station-body").removeClass("d-none");
        loadCameras();
        loadEvents();
        loadData();
    }

    // "Key - ข้อความไทย" labels (statictext keeps the design's bilingual wording):
    // show the Thai text first, the English key as a small muted suffix.
    function bilingualLabels() {
        const re = /^(.*?)\s*[-–]\s*([\u0E00-\u0E7F][^]*)$/;
        page.find("th, .dash-card-title, .station-specs h6").each(function () {
            const el = $(this);
            if (el.data("bilingual") || el.children().length > 1) return;
            const m = re.exec(el.text().trim());
            if (!m) return;
            el.data("bilingual", true).html(`<span class="lbl-th">${esc(m[2].trim())}</span> <span class="lbl-key">${esc(m[1].trim())}</span>`);
        });
    }

    // ------------------------------------------------------ cross-section
    const DAM_FIELDS = {
        LEFT_BANK_WL_UP: "leftBankOuter", LEFT_BANK_WL_DOWN: "leftBankInner",
        RIGHT_BANK_WL_DOWN: "rightBankInner", RIGHT_BANK_WL_UP: "rightBankOuter",
        GROUND_LEVEL_WL_UP: "bedLeft", GROUND_LEVEL_WL_DOWN: "bedRight",
        WARNING_UP: "warningUp", WARNING_DOWN: "warningDown",
        CRITICAL_UP: "criticalUp", CRITICAL_DOWN: "criticalDown",
        ZEROGATE_UP: "zeroUp", ZEROGATE_DOWN: "zeroDown",
    };
    function renderDam(d) {
        const el = page.find(".station-dam");
        if (!el.length || typeof renderDamChart !== "function") {
            return;
        }
        const values = {};
        $.each(DAM_FIELDS, (field, key) => { values[key] = (d.Specifications || {})[field]; });
        values.waterLevel = (d.Values || {}).WaterLevel;
        const dc = ST.DamChart || {};
        const draw = () => renderDamChart(el.get(0), values, { xTitle: dc.x, yTitle: dc.y });
        draw();
        $(window).on("resize", draw);

        // click = the same drawing enlarged in a wide dialog (the SVG scales with its box)
        el.attr("title", T.CrossSectionZoom || "").addClass("station-dam-zoom").off("click.zoom").on("click.zoom", function () {
            const box = bootbox.dialog({
                title: `${esc(T.CrossSection)} · ${esc(d.SiteCode)} - ${esc(d.SiteName)}`,
                message: '<div class="station-dam-large"></div>',
                size: "xl",
                centerVertical: true,
                onEscape: true,
                backdrop: true,
                className: "station-dam-dialog",
                buttons: { close: { label: ST.Close, className: "btn-secondary btn-sm" } },
            });
            box.on("shown.bs.modal", function () {
                renderDamChart(box.find(".station-dam-large").get(0), values, { xTitle: dc.x, yTitle: dc.y });
            });
        });
    }

    // ------------------------------------------------------------ cameras
    function loadCameras() {
        postJSON("/api/stations/cameras", { filters: { StationID: stationId } }).done(function (res) {
            const st = (res.data || []).find((s) => s.StationID === stationId);
            const cams = st ? st.Cameras : [];
            // only the header button: the CCTV page shows the pictures
            page.find(".station-link-cctv").toggleClass("d-none", !cams.length).attr("href", `/cctv/${stationId}`).find(".cctv-count").remove();
            if (cams.length) {
                page.find(".station-link-cctv").append(` <span class="cctv-count">(${cams.length})</span>`);
            }
        });
    }

    // ------------------------------------------------------------- events
    function loadEvents() {
        postJSON("/api/eventlog/list", { filters: { StationID: stationId }, page: 1, size: 6, sort: [{ field: "EventTime", dir: "desc" }] }).done(function (res) {
            const rows = res.data || [];
            const box = page.find(".station-events").empty();
            page.find(".station-events-empty").toggleClass("d-none", rows.length > 0);
            const statuses = ST.EventLogStatuses || {};
            rows.forEach(function (ev) {
                const status = statuses[ev.Status] || {};
                box.append(`
                    <a class="station-event" href="/events/${ev.ID}">
                        <img class="station-event-img" src="${esc(ev.Image)}" alt="" onerror="this.onerror=null;this.src='${esc(ST.Images.Blank)}'">
                        <div class="min-w-0 flex-fill">
                            <div class="d-flex justify-content-between gap-2"><span class="fw-semibold text-truncate">${esc(ev.Event || "")}</span><span class="text-muted text-nowrap" style="font-size:11px">${when(ev.EventTime)}</span></div>
                            <div class="d-flex justify-content-between gap-2" style="font-size:11px"><span class="text-muted text-truncate">${esc(ev.CameraName || "")}</span><span class="${esc(status.class || "")}">${esc(status.text || "")}</span></div>
                        </div>
                    </a>`);
            });
        });
    }

    // ------------------------------------------------- measurements section
    function dataFilters() {
        const filters = { StationID: stationId };
        page.find(".station-data .tabulator-filters :input[name]").serializeArray().forEach(function (item) {
            if (item.value.trim() !== "") {
                filters[item.name] = item.value;
            }
        });
        return filters;
    }

    function loadData() {
        const filters = dataFilters();
        postJSON("/api/stationdata/summary", { filters }).done(function (s) {
            const box = page.find(".station-summary");
            box.find("[data-summary='total']").text(Number(s.total || 0).toLocaleString());
            box.find("[data-summary='first']").text(s.first ? when(s.first, "DD/MM HH:mm") : "-");
            box.find("[data-summary='last']").text(s.last ? when(s.last, "DD/MM HH:mm") : "-");
        });
        const KEYS = [K.WaterLevel, K.WaterLevel2, K.Rainfall, K.Velocity, K.Flow].filter(Boolean);
        const el = page.find(".station-chart");
        const empty = page.find(".station-chart-empty");
        postJSON("/api/stationdata/series", { filters, parameters: KEYS, bucket: page.find("#BucketSelect").val() }).done(function (res) {
            el.removeClass("d-none");
            const drawn = renderHydroChart(el, res, { keys: KEYS, keysMap: K, labels: ST.StationDataParameters, buckets: ST.StationDataBuckets });
            if (!drawn || !drawn.present.length) {
                el.addClass("d-none");
                empty.removeClass("d-none");
                page.find(".station-chart-info").text("-");
                return;
            }
            empty.addClass("d-none");
            page.find(".station-chart-info").text(`${drawn.bucketText} · ${drawn.total} ${F.Points || ""}`);
            if (!chart) {
                chart = drawn.chart;
                $(window).on("resize", () => chart && chart.resize());
            }
        });
    }

    $(function () {
        // period filter behaviour (same as Station Data): quick range vs custom dates
        page.find(".datepicker").datepicker().on("changeDate clearDate", function () {
            $(this).trigger("change");
        });
        page.find("#DateFromFilter, #DateToFilter").on("change", function () {
            if ($(this).val().trim() !== "" && page.find("#RangeFilter").val() !== "custom") {
                page.find("#RangeFilter").val("custom").trigger("change.select2");
            }
        });
        page.find("#RangeFilter").on("change", function () {
            if ($(this).val() !== "custom") {
                page.find("#DateFromFilter, #DateToFilter").val("");
            }
        });
        page.find("#BucketSelect").on("change", loadData);
        // grid reload (filters change) -> refresh tiles + chart too
        const bind = function (tries) {
            const table = Tabulator.findTable("#stationDataTable")[0];
            if (table) {
                table.on("dataLoaded", loadData);
            } else if (tries > 0) {
                setTimeout(() => bind(tries - 1), 200);
            }
        };
        bind(25);
    });

    postJSON("/api/stations/public", { cid: stationId }).done(function (res) {
        if (res && res.Result) {
            render(res.Data);
        } else {
            page.find(".station-notfound").removeClass("d-none");
        }
    }).fail(function () {
        page.find(".station-notfound").removeClass("d-none");
    });
})();
