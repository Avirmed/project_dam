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

// Live preview of the RTSP stream / ISAPI snapshot links built from the camera
// settings (mirrors Camera.build_links() on the server).
function renderCameraLinks(form) {
    let block = form.find(".app-json-data[data-field='CameraConfigures']");
    if (!block.length) {
        return;
    }
    let val = (name) => (block.find(`:input[name='${name}']`).val() || "").trim();
    let host = val("RSTP_IP").split("://").pop().split("/")[0].split("@").pop().split(":")[0];
    let user = encodeURIComponent(val("Username"));
    let pass = encodeURIComponent(val("Password"));
    let auth = user ? `${user}:${pass}@` : "";
    let channel = val("ChannelsID") || "101";
    let rtspPort = parseInt(val("Port"), 10) || 554;
    let isapiPort = parseInt(val("ISAPI_Port"), 10) || 80;

    let links = host
        ? {
            StreamURL: `rtsp://${auth}${host}:${rtspPort}/Streaming/Channels/${channel}`,
            SnapshotURL: `http://${auth}${host}:${isapiPort}/ISAPI/Streaming/channels/${channel}/picture`,
        }
        : { StreamURL: "", SnapshotURL: "" };

    block.find(".camera-link").each(function () {
        $(this).val(links[$(this).data("link")] || "");
    });
}

// Latest picture stored by the worker (Camera.snapshot()); hidden until one exists.
function renderCameraSnapshot(form, jsonData) {
    let box = form.find(".camera-snapshot");
    if (!box.length || !jsonData || !jsonData.SnapshotTime) {
        return;
    }
    box.find(".camera-snapshot-img").attr("src", jsonData.SnapshotImage);
    box.find(".camera-snapshot-time").text(jsonData.SnapshotTime);
    box.removeClass("d-none");
}

$(document).on("input change", ".app-json-data[data-field='CameraConfigures'] :input", function () {
    if (moduleForm) {
        renderCameraLinks(moduleForm);
    }
});

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
                    renderCameraLinks(moduleForm);
                    renderCameraSnapshot(moduleForm, jsonData);
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
                renderCameraLinks(moduleForm);
            }

            // design slide 11: "<SiteCode> – <SiteName> (<DeviceID>)"
            select2Ajax($("#StationID"), "StationID", (s) => `${s.SiteCode} – ${s.SiteName}${s.DeviceID ? ` (${s.DeviceID})` : ""}`);

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