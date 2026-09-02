let pagePermission = [1, 2, 3];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}

let moduleContainer = $("#module-container");
let moduleTitle = $(".page-breadcrumb h2 span.text").text();
$(".form-tmp form").attr("form-title", moduleTitle);
let formTmp = $(".form-tmp").html();
$(".form-tmp").remove();

const module = "sensors";

// Flow tab: draw the Custom Profile polygon (numbered survey points) as it is
// typed. Cells: 0 = row number, 1 = x, 2 = y, last = delete.
function readProfilePoints(form) {
    let points = [];
    form.find(".table-configure[data-field='CustomProfile'] tbody tr").each(function (rowIndex) {
        let cells = $(this).find("td");
        // rowIndex travels with the point so a dragged marker writes back to
        // its own table row even when blank rows are skipped by the chart
        points.push({ x: cells.eq(1).text().trim(), y: cells.eq(2).text().trim(), row: rowIndex });
    });
    return points;
}

function renderSensorProfile(form) {
    let block = form.find(".app-json-data[data-field='Flow']");
    let chart = block.find(".profile-chart")[0];
    if (!chart || typeof renderProfileChart !== "function") {
        return;
    }
    let pc = (LOCAL_VARIABLES.StaticText && LOCAL_VARIABLES.StaticText.ProfileChart) || {};
    renderProfileChart(chart, readProfilePoints(form), {
        ref: block.find(":input[name='AreaRef']").val() || "Level",
        xTitle: pc.x,
        yTitle: pc.y,
        // drag a marker -> update that row's x / y cells, then redraw
        onChange: function (point, x, y) {
            if (point) {
                let cells = block.find(".table-configure[data-field='CustomProfile'] tbody tr").eq(point.row).find("td");
                cells.eq(1).text(x);
                cells.eq(2).text(y);
            }
            renderSensorProfile(form);
        },
    });
}

// typing in cells, Ref. change, row add / delete and drag-reorder
$(document).on("input change click sortupdate", ".app-json-data[data-field='Flow']", function () {
    if (moduleForm) {
        renderSensorProfile(moduleForm);
    }
});

// Replace a .table-configure body with rows [{column: value}] (same cell
// markup as the generic engine, so editing / sorting / serializing still work).
function fillConfigTable(table, rows) {
    let body = table.find("tbody").empty();
    let headers = [];
    table.find("thead th[data-value]").each(function () {
        headers.push($(this));
    });
    $.each(rows || [], function (i, row) {
        let tr = $("<tr/>");
        tr.append(`<td class="drag-btn">${i + 1}</td>`);
        $.each(headers, function (_, th) {
            let value = row[th.data("value")];
            tr.append(configTableCell(th, value != null ? value : "", table.data("align")));
        });
        tr.append(`<td><span class="deleteBtn" role="button">${LOCAL_VARIABLES.StaticText.Icon['-']}</span></td>`);
        body.append(tr);
    });
}

// "Calculate": Profile (water level -> wetted area) from the Custom Profile
// points; the result only lands in the table - Save stores it.
$(document).on("click", ".profile-calc", function () {
    let btn = $(this);
    let block = moduleForm.find(".app-json-data[data-field='Flow']");
    let points = readProfilePoints(moduleForm).map(function (p) { return { x: p.x, y: p.y }; });

    btn.prop("disabled", true);
    $.ajax({
        url: `/api/${module}/profile`,
        type: "POST",
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        data: JSON.stringify({ AreaRef: block.find(":input[name='AreaRef']").val() || "Level", CustomProfile: points }),
    }).done(function (jsonData) {
        if (jsonData.Result) {
            fillConfigTable(block.find(".table-configure[data-field='Profile']"), jsonData.Data);
            toastr.success(jsonData.Message, jsonData.Title);
        } else {
            toastr.error(jsonData.Message, jsonData.Title);
        }
    }).fail(ajaxFailToast).always(function () {
        btn.prop("disabled", false);
    });
});
let moduleForm = null;
let submitBtn = null;

function loadForm(cid = '') {
    if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
        return;
    }

    let tableEl = $("#sensorTable");
    let table = Tabulator.findTable(tableEl[0])[0];

    let dialog = bootbox.dialog({
        size: "xl",
        title: `${moduleTitle} - ${cid ? LOCAL_VARIABLES.StaticText.Edit : LOCAL_VARIABLES.StaticText.Add}`,
        message: " ",
        centerVertical: true,
        onShown: function () {
            dialog.find(".bootbox-body").html(formTmp);

            moduleForm = dialog.find(".bootbox-body").find("form");
            submitBtn = moduleForm.find("button[type='submit']");
            submitBtn.attr("data-text", submitBtn.html());

            if (cid != '') {
                $.get(`/api/${module}/get/${cid}`, function (jsonData) {
                    dialog.find(".bootbox-body").find(".form-processing").remove();
                    moduleForm.removeClass("invisible");

                    updateEditForm(moduleForm, jsonData);
                    CKEDITOR.replace("Remark");
                    renderSensorProfile(moduleForm);
                }).fail(function (jqXHR) {
                    if (jqXHR.responseJSON) {
                        toastr.error(jqXHR.responseJSON.Message, jqXHR.responseJSON.Title);
                    } else if (jqXHR.responseText) {
                        toastr.error(jqXHR.responseText);
                    } else {
                        toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoInternetConnection);
                    }
                    dialog.modal("hide");
                });
            } else {
                dialog.find(".bootbox-body").find(".form-processing").remove();
                moduleForm.removeClass("invisible");

                moduleForm.find(`[name='SortOrder']`).val(tableEl.data("total") ? parseInt(tableEl.data("total")) + 1 : 1);
                moduleForm.find(`[type='checkbox'][name='Status']`).prop('checked', true);

                CKEDITOR.replace("Remark");
                renderSensorProfile(moduleForm);
            }


            $(".selectTwo").select2();
            initForm(moduleForm);

            moduleForm.validate();
            moduleForm.ajaxForm({
                url: `/api/${module}/save`,
                type: "POST",
                dataType: "json",
                beforeSerialize: function ($form, options) {
                    serializeEditForm($form);

                    options.data = $.extend({}, options.data, serializeJsonData($form));
                },
                beforeSubmit: function () {
                    lockFormInputs(moduleForm, true);
                    submitBtn.html(LOCAL_VARIABLES.StaticText.Icon.LoadingCog + " " + submitBtn.data("text").replace(/<\/?[^>]+(>|$)/g, ''));
                },
                error: function (jqXHR) {
                    if (jqXHR.responseJSON) {
                        toastr.error(jqXHR.responseJSON.Message, jqXHR.responseJSON.Title);
                    } else if (jqXHR.responseText) {
                        toastr.error(jqXHR.responseText);
                    } else {
                        toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoInternetConnection);
                    }

                    lockFormInputs(moduleForm, false, function () {
                        submitBtn.html(submitBtn.data("text"));
                    });
                },
                success: function (jsonData) {
                    if (jsonData.Data.ID == null || jsonData.Data.ID == '') {
                        table.setData();
                        dialog.modal("hide");
                        return;
                    }

                    updateEditForm(moduleForm, jsonData.Data);

                    table.setData();
                    toastr.success(jsonData.Message, jsonData.Title);

                    lockFormInputs(moduleForm, false, function () {
                        submitBtn.html(submitBtn.data("text"));
                    });
                }
            });
        },
        onHidden: function () {
            if (
                typeof moduleForm.attr("data-url") !== 'undefined' && moduleForm.attr("data-url") !== false
            ) {
                let url = moduleForm.attr("data-url")
                url = url.substring(0, url.indexOf("/#"));
                window.history.replaceState("", "", url);
            }
        }
    });
}

if (moduleContainer.data("contentid") && moduleContainer.data("contentid") != '') {
    setTimeout(function () {
        loadForm(moduleContainer.data("contentid"));
    }, 100);
}

$(document).on("click", "#sensorTable .addBtn", function (e) {
    loadForm();
});

$(document).on("click", "#sensorTable .editBtn", function (e) {
    let rowId = $(this).closest(".tabulator-row").data('id');
    loadForm(rowId);
});

$(document).on("click", "#sensorTable .deleteBtn", function (e) {
    let rowId = $(this).closest(".tabulator-row").data('id');

    let tableEl = $("#sensorTable");
    let table = Tabulator.findTable(tableEl[0])[0];

    bootbox.dialog({
        title: LOCAL_VARIABLES.StaticText.Messages.DeleteQuestion,
        message: `<h5>"${table.getRow(rowId).getData()['SensorID']} - ${table.getRow(rowId).getData()['SensorName']}"</h5>`,
        centerVertical: true,
        onEscape: true,
        size: 'md',
        buttons: {
            yes: {
                label: LOCAL_VARIABLES.StaticText.Yes,
                className: 'btn-danger btn-sm me-2',
                callback: function () {
                    $.post(`/api/${module}/delete`, { ID: rowId }, function (jsonData) {
                        if (jsonData.Result) {
                            table.setData();
                            toastr.warning(jsonData.Message, jsonData.Title);
                        } else {
                            toastr.error(jsonData.Message, jsonData.Title);
                        }
                    }, "json").fail(function (jqXHR) {
                        if (jqXHR.responseJSON) {
                            toastr.error(jqXHR.responseJSON.Message, jqXHR.responseJSON.Title);
                        } else if (jqXHR.responseText) {
                            toastr.error(jqXHR.responseText);
                        } else {
                            toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoInternetConnection);
                        }
                    });
                }
            },
            no: {
                label: LOCAL_VARIABLES.StaticText.No,
                className: 'btn-secondary btn-sm'
            }
        }
    });
});