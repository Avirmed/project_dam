let pagePermission = [1, 2, 3];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}

let moduleContainer = $("#module-container");
let moduleTitle = $(".page-breadcrumb h2 span.text").text();
$(".form-tmp form").attr("form-title", moduleTitle);
let formTmp = $(".form-tmp").html();
$(".form-tmp").remove();

const module = "cameras";
let moduleForm = null;
let submitBtn = null;

function loadForm(cid = '') {
    if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
        return;
    }

    let tableEl = $("#cameraTable");
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

                    let jsonFields = {};
                    $(".app-json-data").each(function () {
                        let _this = $(this);
                        let jsonField = _this.data("field");


                        jsonFields[jsonField] = {
                            'status': false,
                            'configs': {}
                        };

                        if (_this.find(`input[name="status"]`).length) {
                            jsonFields[jsonField]['status'] = _this.find(`input[name="status"]`).is(":checked");
                            _this.find(`input[name="status"]`).prop('disabled', true);
                        }

                        if (_this.find(`input[name="color"]`).length) {
                            jsonFields[jsonField]['color'] = _this.find(`input[name="color"]`).is(":checked");
                            _this.find(`input[name="color"]`).prop('disabled', true);
                        }

                        _this.find(".field-basic :input").each(function () {
                            let name = $(this).attr("name");
                            let value = $(this).val();

                            jsonFields[jsonField]['configs'][name] = (typeof value === 'string') ? value.trim() : (value || '');

                            if ($(this).is(":checkbox")) {
                                jsonFields[jsonField]['configs'][name] = $(this).is(":checked");
                            }
                        });

                        _this.find(".field-check").each(function () {
                            let fieldGroup = $(this);
                            let fieldName = fieldGroup.data("field");
                            let checked = fieldGroup.find(":checkbox").is(":checked");
                            let text = fieldGroup.find(":text").val();
                            let radio = null;

                            if (fieldGroup.find(":radio").length) {
                                fieldGroup.find(":radio").each(function () {
                                    if ($(this).is(":checked")) {
                                        radio = $(this).val();
                                    }
                                });
                            }

                            jsonFields[jsonField]['configs'][fieldName] = {
                                'checked': checked,
                                'text': text,
                                'radio': radio
                            };
                        });

                        _this.find(".table-configure").each(function () {
                            let table = $(this);
                            let fieldName = table.data("field");
                            let columns = {};
                            let rowData = [];

                            table.find(`thead th[data-value]`).each(function () {
                                columns[$(this).index()] = $(this).data("value");
                            });

                            table.find(`tbody tr`).each(function () {
                                let rows = $(this).find("td");
                                let obj = {}
                                let filled = false;

                                $.each(columns, function (key, value) {
                                    obj[value] = rows.eq(key).text().trim();

                                    if (rows.eq(key).text().trim() != '') {
                                        filled = true;
                                    }
                                });

                                filled && rowData.push(obj);
                            });

                            jsonFields[jsonField]['configs'][fieldName] = rowData;
                        });

                        jsonFields[jsonField] = JSON.stringify(jsonFields[jsonField]);
                    });

                    options.data = $.extend({}, options.data, jsonFields);

                    $form.find('.app-json-data :input').prop('disabled', true);
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

$(document).on("click", "#cameraTable .addBtn", function (e) {
    loadForm();
});

$(document).on("click", "#cameraTable .editBtn", function (e) {
    let rowId = $(this).closest(".tabulator-row").data('id');
    loadForm(rowId);
});

$(document).on("click", "#cameraTable .deleteBtn", function (e) {
    let rowId = $(this).closest(".tabulator-row").data('id');

    let tableEl = $("#cameraTable");
    let table = Tabulator.findTable(tableEl[0])[0];

    bootbox.dialog({
        title: LOCAL_VARIABLES.StaticText.Messages.DeleteQuestion,
        message: `<h5>"${table.getRow(rowId).getData()['CameraID']} - ${table.getRow(rowId).getData()['CameraName']}"</h5>`,
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