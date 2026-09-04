// Station Data (read-only): every payload received by the REST API server.
// The shared Tabulator engine (project.js) builds the grid from cfg-ajax-url and
// sends the .tabulator-filters inputs as `filters`; this file wires the filter
// lists, the quick period <-> custom dates rule, the summary tiles, the ECharts
// series of one parameter for the selected station (payload detail: payload.js).
let pagePermission = [1, 2, 3];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}

const stationdataTableID = "#stationdataTable";
const ST_FIELD = LOCAL_VARIABLES.StaticText.StationDataField || {};
const ST_PARAMS = LOCAL_VARIABLES.StaticText.StationDataParameters || {};
let stationdataChart = null;

// Current filter values, same shape the grid sends (params.filters).
function stationdataFilters() {
    let filters = {};
    $(".tabulator-filters :input").serializeArray().forEach(function (item) {
        if (item.value.trim() !== "") {
            filters[item.name] = item.value;
        }
    });
    return filters;
}

function postJSON(url, body) {
    return $.ajax({
        url: url,
        type: "POST",
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        data: JSON.stringify(body),
    });
}

// ------------------------------------------------------------ summary tiles
function loadStationdataSummary() {
    postJSON("/api/stationdata/summary", { filters: stationdataFilters() }).done(function (s) {
        let box = $(".stationdata-summary");
        box.find("[data-summary='total']").text(Number(s.total || 0).toLocaleString());
        box.find("[data-summary='stations']").text(s.stations || 0);
        box.find("[data-summary='first']").text(s.first || "-");
        box.find("[data-summary='last']").text(s.last || "-");
    });
}

// ------------------------------------------------------------------ chart
function loadStationdataChart() {
    let card = $(".stationdata-chart-card");
    let el = card.find(".stationdata-chart");
    let empty = card.find(".stationdata-chart-empty");
    let info = card.find(".stationdata-chart-info");
    let filters = stationdataFilters();
    const K = LOCAL_VARIABLES.StaticText.StationDataKeys || {};
    // every measured column except the wetted area (a derived helper value)
    const KEYS = [K.WaterLevel, K.WaterLevel2, K.Rainfall, K.Velocity, K.Flow].filter(Boolean);

    if (!filters.StationID || typeof echarts === "undefined") {
        el.addClass("d-none");
        empty.text(ST_FIELD.SelectStation).removeClass("d-none");
        info.text("");
        return;
    }

    postJSON("/api/stationdata/series", { filters: filters, parameters: KEYS, bucket: $("#BucketSelect").val() }).done(function (res) {
        el.removeClass("d-none");
        let drawn = renderHydroChart(el, res, { keys: KEYS, keysMap: K, labels: ST_PARAMS, buckets: LOCAL_VARIABLES.StaticText.StationDataBuckets });
        if (!drawn || !drawn.present.length) {
            el.addClass("d-none");
            empty.text(ST_FIELD.NoNumeric).removeClass("d-none");
            info.text("");
            return;
        }
        empty.addClass("d-none");
        info.text(`${$("#StationIDFilter option:selected").text()} · ${drawn.bucketText} · ${drawn.total} ${ST_FIELD.Points}`);
        if (!stationdataChart) {
            stationdataChart = drawn.chart;
            $(window).on("resize", () => stationdataChart && stationdataChart.resize());
        }
    }).fail(ajaxFailToast);
}

// The payload detail dialog (.viewBtn) is shared: static/js/payload.js.

// ------------------------------------------------------------------ wiring
$(function () {
    // filter lists (the shared engine only makes them select2; options come from here)
    select2Ajax($("#ProjectIDFilter"), "ProjectID", "ProjectName");
    select2Ajax($("#RiverBasinIDFilter"), "RiverBasinID", "WatershedName");
    cascadeStationFilter(); // station list follows the project / watershed filters

    // date filters: bootstrap-datepicker updates the input, then notify the grid
    $(".tabulator-filters .datepicker").datepicker().on("changeDate clearDate", function () {
        $(this).trigger("change");
    });

    // quick period and custom dates are mutually exclusive
    $("#DateFromFilter, #DateToFilter").on("change", function () {
        if ($(this).val().trim() !== "" && $("#RangeFilter").val() !== "custom") {
            $("#RangeFilter").val("custom").trigger("change.select2");
        }
    });
    $("#RangeFilter").on("change", function () {
        if ($(this).val() !== "custom") {
            $("#DateFromFilter, #DateToFilter").val("");
        }
    });

    // Min / Max: reload on Enter (blur / change is handled by the shared engine)
    $("#MinFilter, #MaxFilter").on("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            $(this).trigger("change");
        }
    });

    $("#BucketSelect").on("change", loadStationdataChart);

    // refresh tiles + chart every time the grid reloads (filters, paging, sort)
    let bind = function (tries) {
        let table = Tabulator.findTable(stationdataTableID)[0];
        if (table) {
            table.on("dataLoaded", function () {
                loadStationdataSummary();
                loadStationdataChart();
            });
            loadStationdataSummary();
            loadStationdataChart();
        } else if (tries > 0) {
            setTimeout(function () { bind(tries - 1); }, 200);
        }
    };
    bind(25);
});
