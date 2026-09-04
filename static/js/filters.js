// Shared filter helpers for the list / report pages (dashboard + public front).
//
// cascadeStationFilter(scope): the Station filter (#StationIDFilter) depends on the
// Project (#ProjectIDFilter) and Watershed (#RiverBasinIDFilter) filters - whenever
// one of them changes the station list is reloaded from the select's data-url with
// those filters; the current station is kept when it is still in the list, cleared
// (with a change event, so the grid / chart reload) when it is not. A preset can be
// given through the data-selectid attribute (e.g. /statistics/<StationID>).
function cascadeStationFilter(scope) {
    scope = $(scope || document);
    const station = scope.find("#StationIDFilter");
    const project = scope.find("#ProjectIDFilter");
    const basin = scope.find("#RiverBasinIDFilter");
    if (!station.length || !station.data("url")) {
        return null;
    }
    const firstText = station.find("option:first").text().trim() || `-- ${LOCAL_VARIABLES.StaticText.All} --`;
    const label = (s) => `${s.SiteCode} – ${s.SiteName}${s.DeviceID ? ` (${s.DeviceID})` : ""}`;

    function reload() {
        const filters = {};
        if (project.val()) filters.ProjectID = project.val();
        if (basin.val()) filters.RiverBasinID = basin.val();
        const before = station.val() || "";
        const wanted = station.attr("data-selectid") || before;

        $.ajax({
            url: station.data("url"),
            type: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify({ filters: filters }),
        }).done(function (res) {
            station.empty().append(new Option(firstText, "", false, false));
            (res.data || []).forEach((s) => station.append(new Option(label(s), s.StationID, false, false)));
            station.select2();
            station.removeAttr("data-selectid");
            const exists = wanted !== "" && station.find(`option[value="${wanted}"]`).length > 0;
            const after = exists ? String(wanted) : "";
            station.val(after);
            if (after !== before) {
                station.trigger("change"); // selection preset or lost -> grid / chart reload
            } else {
                station.trigger("change.select2"); // repaint only
            }
        }).fail(ajaxFailToast);
    }

    project.add(basin).on("change", reload);
    reload();
    return reload;
}
