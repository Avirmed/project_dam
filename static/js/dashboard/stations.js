let pagePermission = [1, 2, 3];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}

let moduleContainer = $("#module-container");
let moduleTitle = $(".page-breadcrumb h2 span.text").text();
$(".form-tmp form").attr("form-title", moduleTitle);
let formTmp = $(".form-tmp").html();
$(".form-tmp").remove();

const module = "stations";
let moduleForm = null;
let submitBtn = null;
let fileUploader = null;

function loadForm(cid = '') {
    if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
        return;
    }

    let tableEl = $("#stationTable");
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

                    updateEditForm(moduleForm, jsonData, true);
                    CKEDITOR.replace("Remark");
                    initArcGIS("mapArcGIS", moduleForm.find("#Latitude"), moduleForm.find("#Longitude"), moduleForm.find("#Zoom"));
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
                initArcGIS("mapArcGIS", moduleForm.find("#Latitude"), moduleForm.find("#Longitude"), moduleForm.find("#Zoom"));
            }

            select2Ajax($("#ProjectID"), "ProjectID", "ProjectName");
            select2Ajax($("#RiverBasinID"), "RiverBasinID", "WatershedName");

            $(".selectTwo").select2();
            initForm(moduleForm);

            moduleForm.validate();
            moduleForm.ajaxForm({
                url: `/api/${module}/save`,
                type: "POST",
                dataType: "json",
                beforeSerialize: function ($form, options) {
                    serializeEditForm($form);
                    fileUploader = new FileUploader("#ImageSource", `/api/${module}/fileupload`, fileUploadDone);

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
                    if (jsonData.Data.StationID == null || jsonData.Data.StationID == '') {
                        table.setData();
                        dialog.modal("hide");
                        return;
                    }

                    updateEditForm(moduleForm, jsonData.Data, fileUploader.Files.length == 0);

                    if (fileUploader.Files.length > 0) {
                        fileUploader.targetId = jsonData.Data.StationID;
                        fileUploader.upload();
                        return;
                    }

                    table.setData();
                    toastr.success(jsonData.Message, jsonData.Title);

                    lockFormInputs(moduleForm, false, function () {
                        submitBtn.html(submitBtn.data("text"));
                    });
                }
            });

            $(moduleForm).on("click", ".form-image .rotateBtn:not(.disabled) > span", function (e) {
                let _this = $(this)
                _this.parent(".rotateBtn").addClass("disabled");
                lockFormInputs(moduleForm, true);

                $.post(`/api/${module}/imgrotate`, { StationID: $(`[name='StationID']`).val(), direction: $(this).data("direction") }, function (jsonData) {
                    if (jsonData.Result) {
                        updateEditForm(moduleForm, jsonData.Data, true);

                        let tableEl = $("#stationTable");
                        let table = Tabulator.findTable(tableEl[0])[0];
                        table.setData();

                        toastr.success(jsonData.Message, jsonData.Title);
                    } else {
                        toastr.error(jsonData.Message, jsonData.Title);
                    }

                    lockFormInputs(moduleForm, false);
                    _this.parent(".rotateBtn").removeClass("disabled");
                }, "json").fail(function (jqXHR) {
                    if (jqXHR.responseJSON) {
                        toastr.error(jqXHR.responseJSON.Message, jqXHR.responseJSON.Title);
                    } else if (jqXHR.responseText) {
                        toastr.error(jqXHR.responseText);
                    } else {
                        toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoInternetConnection);
                    }

                    lockFormInputs(moduleForm, false);
                    _this.parent(".rotateBtn").removeClass("disabled");
                });
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

$(document).on("click", "#stationTable .addBtn", function (e) {
    loadForm();
});

$(document).on("click", "#stationTable .editBtn", function (e) {
    let rowId = $(this).closest(".tabulator-row").data('id');
    loadForm(rowId);
});

$(document).on("click", "#stationTable .deleteBtn", function (e) {
    let rowId = $(this).closest(".tabulator-row").data('id');

    let tableEl = $("#stationTable");
    let table = Tabulator.findTable(tableEl[0])[0];

    bootbox.dialog({
        title: LOCAL_VARIABLES.StaticText.Messages.DeleteQuestion,
        message: `<h5>"${table.getRow(rowId).getData()['SiteCode']} - ${table.getRow(rowId).getData()['SiteName']}"</h5>`,
        centerVertical: true,
        onEscape: true,
        size: 'md',
        buttons: {
            yes: {
                label: LOCAL_VARIABLES.StaticText.Yes,
                className: 'btn-danger btn-sm me-2',
                callback: function () {
                    $.post(`/api/${module}/delete`, { StationID: rowId }, function (jsonData) {
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

function fileUploadDone(progress, isDone) {
    if (progress.statusOk) {
        progress.el.parent().children('.file-progress-bar').text(`${progress.percent}%`);
        progress.el.parent().children('.file-progress-bar').width(`${progress.percent}%`);
        if (progress.percent == 100 && isDone) {
            updateEditForm(moduleForm, progress.jsonData, true);

            let tableEl = $("#stationTable");
            let table = Tabulator.findTable(tableEl[0])[0];
            table.setData();

            toastr.success(LOCAL_VARIABLES.StaticText.Messages.SuccessSaved, LOCAL_VARIABLES.StaticText.Messages.Title);
            lockFormInputs(moduleForm, false, function () {
                submitBtn.html(submitBtn.data("text"));
                setTimeout(function () {
                    progress.el.parent().children('.file-progress-bar').text('');
                    progress.el.parent().children('.file-progress-bar').width(0);
                }, 500);
            });
        }
    } else {
        toastr.error(LOCAL_VARIABLES.StaticText.Messages.FileUploadError, LOCAL_VARIABLES.StaticText.Messages.Title);
        lockFormInputs(moduleForm, false, function () {
            submitBtn.html(submitBtn.data("text"));
            setTimeout(function () {
                progress.el.parent().children('.file-progress-bar').text('');
                progress.el.parent().children('.file-progress-bar').width(0);
            }, 500);
        });
    }
}