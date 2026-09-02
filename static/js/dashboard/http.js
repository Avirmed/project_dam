let pagePermission = [1, 2, 3];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}

let moduleContainer = $("#module-container");
let moduleTitle = $(".page-breadcrumb h2 span.text").text();
$(".form-tmp form").attr("form-title", moduleTitle);
let formTmp = $(".form-tmp").html();
$(".form-tmp").remove();

const module = "http";
let moduleForm = null;
let submitBtn = null;

// Render a Datetime mapping value (e.g. "yyyymmddHHMM") for the preview.
// Case matters as on the design: mm = month, MM = minutes.
function formatDateToken(date, format) {
    let p = (n) => String(n).padStart(2, "0");
    return (format || "yyyymmddHHMM")
        .replace("yyyy", date.getFullYear())
        .replace("yy", String(date.getFullYear()).slice(-2))
        .replace("mm", p(date.getMonth() + 1))
        .replace("dd", p(date.getDate()))
        .replace("HH", p(date.getHours()))
        .replace("MM", p(date.getMinutes()))
        .replace("ss", p(date.getSeconds()));
}

// Preview the outbound payload built from the Parameter Mapping rows:
// Static Value as-is, Sensor Data shown as <key> placeholder, Datetime rendered
// with the current time. JSON or key=value pairs depending on Content Type.
function renderHttpExample(form) {
    let block = form.find(".app-json-data[data-field='Request']");
    let pre = block.find(".http-example");
    if (!pre.length) {
        return;
    }

    let contentType = block.find(":input[name='ContentType']").val() || "json";
    let payload = {};

    // cells: 0 = row number, then source_type | param | value, last = delete
    block.find(".table-configure[data-field='Mapping'] tbody tr").each(function () {
        let cells = $(this).find("td");
        let type = cells.eq(1).find("select").val() || "";
        let param = cells.eq(2).text().trim();
        let value = cells.eq(3).text().trim();
        if (!param) {
            return;
        }
        if (type === "datetime") {
            payload[param] = formatDateToken(new Date(), value);
        } else if (type === "sensor") {
            payload[param] = value ? `<${value}>` : "";
        } else {
            payload[param] = value;
        }
    });

    if (contentType === "text") {
        pre.text(Object.keys(payload).map((k) => `${k}=${payload[k]}`).join("&"));
    } else {
        pre.text(JSON.stringify(payload));
    }
}

$(document).on("input change click", ".app-json-data[data-field='Request']", function () {
    if (moduleForm) {
        renderHttpExample(moduleForm);
    }
});

function loadForm(cid = '') {
    if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
        return;
    }

    let tableEl = $("#httpTable");
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
                    renderHttpExample(moduleForm);
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

                moduleForm.find(`[type='checkbox'][name='Status']`).prop('checked', true);

                CKEDITOR.replace("Remark");
                renderHttpExample(moduleForm);
            }

            select2Ajax($("#StationID"), "StationID", "SiteName");

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

$(document).on("click", "#httpTable .addBtn", function (e) {
    loadForm();
});

$(document).on("click", "#httpTable .editBtn", function (e) {
    let rowId = $(this).closest(".tabulator-row").data('id');
    loadForm(rowId);
});

$(document).on("click", "#httpTable .deleteBtn", function (e) {
    let rowId = $(this).closest(".tabulator-row").data('id');

    let tableEl = $("#httpTable");
    let table = Tabulator.findTable(tableEl[0])[0];

    bootbox.dialog({
        title: LOCAL_VARIABLES.StaticText.Messages.DeleteQuestion,
        message: `<h5>"${table.getRow(rowId).getData()['URL']}"</h5>`,
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
