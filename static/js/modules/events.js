// Public Event Log (security camera events). The shared Tabulator engine
// (project.js) builds the grid from cfg-ajax-url; this file adds the
// Approve / Reject counters, the date filters and the row actions.
const eventlogTableID = "#eventlogTable";

function eventlogFilters() {
    let filters = {};
    $(".tabulator-filters :input").serializeArray().forEach(function (item) {
        if (item.value.trim() !== "") {
            filters[item.name] = item.value;
        }
    });
    return filters;
}

function loadEventlogCounters() {
    $.ajax({
        url: "/api/eventlog/counters",
        type: "POST",
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        data: JSON.stringify({ filters: eventlogFilters() }),
    }).done(function (counts) {
        $.each(counts, function (status, count) {
            $(`.eventlog-counters [data-status="${status}"]`).text(count);
        });
    });
}

$(function () {
    // filter lists (the shared engine only makes them select2; options come from here)
    select2Ajax($("#ProjectIDFilter"), "ProjectID", "ProjectName");
    select2Ajax($("#RiverBasinIDFilter"), "RiverBasinID", "WatershedName");

    $(".tabulator-filters .datepicker").datepicker().on("changeDate clearDate", function () {
        $(this).trigger("change");
    });

    let bindCounters = function (tries) {
        let table = Tabulator.findTable(eventlogTableID)[0];
        if (table) {
            table.on("dataLoaded", loadEventlogCounters);
            loadEventlogCounters();
        } else if (tries > 0) {
            setTimeout(function () { bindCounters(tries - 1); }, 200);
        }
    };
    bindCounters(25);
});

// Approve / Reject: update the status, then refresh the grid and counters.
$(document).on("click", `${eventlogTableID} .actionBtn`, function () {
    let rowId = $(this).closest(".tabulator-row").data("id");
    let status = $(this).data("status");

    $.post("/api/eventlog/action", { ID: rowId, Status: status }, function (jsonData) {
        if (jsonData.Result) {
            let table = Tabulator.findTable(eventlogTableID)[0];
            if (table) {
                table.setData();
            }
            toastr.success(jsonData.Message, jsonData.Title);
        } else {
            toastr.error(jsonData.Message, jsonData.Title);
        }
    }, "json").fail(ajaxFailToast);
});
