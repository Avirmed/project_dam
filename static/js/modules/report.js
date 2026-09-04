// Public Report page (front design slide 9). The shared Tabulator engine
// (project.js) builds the grid from cfg-ajax-url and sends the
// .tabulator-filters inputs as `filters`; this file only wires the filter lists,
// the date pickers and the quick period <-> custom dates rule.
$(function () {
    const page = $(".report-page");
    if (!page.length) {
        return;
    }
    select2Ajax(page.find("#ProjectIDFilter"), "ProjectID", "ProjectName");
    select2Ajax(page.find("#RiverBasinIDFilter"), "RiverBasinID", "WatershedName");
    cascadeStationFilter(page); // station list follows the project / watershed filters

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
});
