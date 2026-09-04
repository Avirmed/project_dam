// Payload detail dialog shared by every grid that lists /api/stationdata/list
// (dashboard Station Data, public Report, public station page). The grid's
// "Payload detail" icon (.viewBtn) opens the mapped Data and the raw payload.
function showPayloadDetail(rowId) {
    const ST_FIELD = LOCAL_VARIABLES.StaticText.StationDataField || {};
    const label = (key) => ST_FIELD[key] || key;
    const esc = (s) => $("<div>").text(s == null ? "" : String(s)).html();
    const pretty = (v) => (v && typeof v === "object" ? JSON.stringify(v, null, 2) : v == null ? "" : String(v));

    $.get(`/api/stationdata/get/${rowId}`, function (data) {
        const raw = data.Raw == null
            ? `<span class="text-muted">${esc(label("RawPurged"))}</span>`
            : `<pre class="bg-light border rounded p-2 mb-0 text-wrap">${esc(pretty(data.Raw))}</pre>`;
        const html = `
            <dl class="row small mb-0">
                <dt class="col-sm-3">${label("SiteName")}</dt><dd class="col-sm-9">${esc(data.SiteCode)} - ${esc(data.SiteName)} (${esc(data.DeviceID)})</dd>
                <dt class="col-sm-3">${label("RecordTime")}</dt><dd class="col-sm-9">${esc(data.RecordTime)}</dd>
                <dt class="col-sm-3">${label("Data")}</dt><dd class="col-sm-9"><pre class="bg-light border rounded p-2 mb-0 text-wrap">${esc(pretty(data.Data))}</pre></dd>
                <dt class="col-sm-3">${label("Raw")}</dt><dd class="col-sm-9">${raw}</dd>
            </dl>`;

        bootbox.dialog({
            title: `${label("Detail")} #${data.ID}`,
            message: html,
            size: "lg",
            centerVertical: true,
            onEscape: true,
            buttons: {
                close: { label: LOCAL_VARIABLES.StaticText.Close, className: "btn-secondary btn-sm" },
            },
        });
    }, "json").fail(ajaxFailToast);
}

// Delegated: works for grids rendered later and on every page (dashboard + front).
$(document).on("click", '.app-tabulator-table[cfg-ajax-url="/api/stationdata/list"] .viewBtn', function () {
    showPayloadDetail($(this).closest(".tabulator-row").data("id"));
});
