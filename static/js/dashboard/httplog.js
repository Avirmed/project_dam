// Outbound HTTP delivery log (read-only). The shared Tabulator engine
// (project.js) builds the grid from cfg-ajax-url; this file adds the
// Queue / Sent / Failed counters, the date filters and the detail dialog.
let pagePermission = [1, 2, 3];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}

const httplogTableID = "#httplogTable";

// Current filter values, same shape the grid sends (params.filters).
function httplogFilters() {
    let filters = {};
    $(".tabulator-filters :input").serializeArray().forEach(function (item) {
        if (item.value.trim() !== "") {
            filters[item.name] = item.value;
        }
    });
    return filters;
}

function loadHttplogCounters() {
    $.ajax({
        url: "/api/httplog/counters",
        type: "POST",
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        data: JSON.stringify({ filters: httplogFilters() }),
    }).done(function (counts) {
        $.each(counts, function (status, count) {
            $(`.httplog-counters h5[data-status="${status}"]`).text(count);
        });
    });
}

$(function () {
    // date filters: bootstrap-datepicker updates the input, then notify the grid
    $(".tabulator-filters .datepicker").datepicker().on("changeDate clearDate", function () {
        $(this).trigger("change");
    });

    // refresh the counters every time the grid reloads (filters, paging, sort)
    let bindCounters = function (tries) {
        let table = Tabulator.findTable(httplogTableID)[0];
        if (table) {
            table.on("dataLoaded", loadHttplogCounters);
            loadHttplogCounters();
        } else if (tries > 0) {
            setTimeout(function () { bindCounters(tries - 1); }, 200);
        }
    };
    bindCounters(25);
});

// Detail dialog: full URL, request body, response code / body, attempts.
$(document).on("click", `${httplogTableID} .viewBtn`, function () {
    let rowId = $(this).closest(".tabulator-row").data("id");
    let F = LOCAL_VARIABLES.StaticText.HttpLogField || {};
    let label = (key) => F[key] || key;

    $.get(`/api/httplog/get/${rowId}`, function (data) {
        let status = (LOCAL_VARIABLES.StaticText.HttpLogStatuses || {})[data.Status] || {};
        let content = typeof data.Content === "string" ? data.Content : JSON.stringify(data.Content || {}, null, 2);
        let esc = (s) => $("<div>").text(s == null ? "" : String(s)).html();

        let html = `
            <dl class="row small mb-0">
                <dt class="col-sm-3">${label("SiteName")}</dt><dd class="col-sm-9">${esc(data.SiteName)} (${esc(data.DeviceID)})</dd>
                <dt class="col-sm-3">${label("Status")}</dt><dd class="col-sm-9"><span class="${status.class || ""}">${esc(status.text)}</span></dd>
                <dt class="col-sm-3">${label("Method")}</dt><dd class="col-sm-9">${esc((data.Method || "").toUpperCase())}</dd>
                <dt class="col-sm-3">${label("URL")}</dt><dd class="col-sm-9 text-break">${esc(data.URL)}</dd>
                <dt class="col-sm-3">${label("Request")}</dt><dd class="col-sm-9"><pre class="bg-light border rounded p-2 mb-0 text-wrap">${esc(data.Request)}</pre></dd>
                <dt class="col-sm-3">${label("Content")}</dt><dd class="col-sm-9"><pre class="bg-light border rounded p-2 mb-0 text-wrap">${esc(content)}</pre></dd>
                <dt class="col-sm-3">${label("ResponseCode")}</dt><dd class="col-sm-9">${esc(data.ResponseCode)}</dd>
                <dt class="col-sm-3">${label("Response")}</dt><dd class="col-sm-9"><pre class="bg-light border rounded p-2 mb-0 text-wrap">${esc(data.Response)}</pre></dd>
                <dt class="col-sm-3">${label("Attempts")}</dt><dd class="col-sm-9">${esc(data.Attempts)}</dd>
                <dt class="col-sm-3">${label("CreateDate")}</dt><dd class="col-sm-9">${esc(data.CreateDate)}</dd>
                <dt class="col-sm-3">${label("SentDate")}</dt><dd class="col-sm-9">${esc(data.SentDate)}</dd>
                <dt class="col-sm-3">${label("NextAttempt")}</dt><dd class="col-sm-9">${esc(data.NextAttempt)}</dd>
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
});
