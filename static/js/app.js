let appLoginForm = $(".appLoginForm");

if (appLoginForm.length > 0) {
    appLoginForm.each(function () {
        let form = $(this);
        form.validate();
    });

    let submitAppLoginFormBtn = appLoginForm.first().find("button[type='submit']");
    submitAppLoginFormBtn.attr("data-text", submitAppLoginFormBtn.html());

    appLoginForm.ajaxForm({
        url: "/api/users/login",
        type: "post",
        dataType: "json",
        beforeSubmit: function () {
            lockFormInputs(appLoginForm, true);
            submitAppLoginFormBtn.html(`${LOCAL_VARIABLES.StaticText.Icon.LoadingCog} ${submitAppLoginFormBtn.text()}`);
        },
        success: function (jsonData) {
            if (jsonData.Result) {
                if (jsonData.Data) {
                    LOCAL_VARIABLES.Authorization = jsonData.Data;
                    setLocalStorage();
                }

                toastr.success(jsonData.Message, jsonData.Title);
                setTimeout(function () {
                    location.reload();
                }, 1000);
            } else {
                toastr.error(jsonData.Message, jsonData.Title);
                lockFormInputs(appLoginForm, false, function () {
                    submitAppLoginFormBtn.html(submitAppLoginFormBtn.data("text"));
                });
            }
        },
        error: function (jqXHR) {
            if (jqXHR.responseJSON) {
                toastr.error(jqXHR.responseJSON.Message, jqXHR.responseJSON.Title);
            } else if (jqXHR.responseText) {
                toastr.error(jqXHR.responseText);
            } else {
                toastr.error(jqXHR.statusText);
            }

            lockFormInputs(appLoginForm, false, function () {
                submitAppLoginFormBtn.html(submitAppLoginFormBtn.data("text"));
                $("input[name='content[UserName]']").focus();
            });
        }
    });
}

function logout() {
    $.post("/api/users/logout", function (jsonData) {
        toastr.warning(jsonData.Message, jsonData.Title);
        if (LOCAL_VARIABLES.Authorization) {
            delete LOCAL_VARIABLES.Authorization;
        }
        setLocalStorage(false);
        setTimeout(function () {
            removeHashParam("logout");
            location.reload();
        }, 1000);
    }, "json").fail(function (jqXHR) {
        if (jqXHR.responseJSON) {
            toastr.error(jqXHR.responseJSON.Message, jqXHR.responseJSON.Title);
        } else if (jqXHR.responseText) {
            toastr.error(jqXHR.responseText);
        } else {
            toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoInternetConnection);
        }
        removeHashParam("logout");
    });
}

let userFormTmp = $(".user-form-tmp").html();
$(".user-form-tmp").remove();
let userModuleForm = null;
let submitUserBtn = null;
let userFileUploader = null;

function userSettings() {
    let dialog = bootbox.dialog({
        size: "lg",
        title: LOCAL_VARIABLES.StaticText.Settings,
        message: " ",
        centerVertical: true,
        onShown: function () {
            dialog.find(".bootbox-body").html(userFormTmp);

            userModuleForm = dialog.find(".bootbox-body").find("form");
            submitUserBtn = userModuleForm.find("button[type='submit']");
            submitUserBtn.attr("data-text", submitUserBtn.html());
            initForm(userModuleForm);

            userModuleForm.validate({
                rules: {
                    'Email': {
                        email: true
                    },
                    'Password': {
                        minlength: 6
                    },
                    'PasswordConfirm': {
                        minlength: 6,
                        equalTo: "#Password"
                    }
                }
            });

            $.get(`/api/users/${userModuleForm.find("input[name='UserID']").val()}`, function (jsonData) {
                dialog.find(".bootbox-body").find(".form-processing").remove();
                userModuleForm.removeClass("invisible");

                updateEditForm(userModuleForm, jsonData, true);
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

            $(".selectTwo").select2();

            userModuleForm.validate();
            userModuleForm.ajaxForm({
                url: `/api/users/save`,
                type: "POST",
                dataType: "json",
                beforeSerialize: function ($form, options) {
                    serializeEditForm($form);
                    userFileUploader = new FileUploader("#ImageSource", `/api/users/fileupload`, userFileUploaderDone);
                },
                beforeSubmit: function () {
                    lockFormInputs(userModuleForm, true);
                    submitUserBtn.html(LOCAL_VARIABLES.StaticText.Icon.LoadingCog + " " + submitUserBtn.data("text").replace(/<\/?[^>]+(>|$)/g, ''));
                },
                error: function (jqXHR) {
                    if (jqXHR.responseJSON) {
                        toastr.error(jqXHR.responseJSON.Message, jqXHR.responseJSON.Title);
                    } else if (jqXHR.responseText) {
                        toastr.error(jqXHR.responseText);
                    } else {
                        toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoInternetConnection);
                    }

                    lockFormInputs(userModuleForm, false, function () {
                        submitUserBtn.html(submitUserBtn.data("text"));
                    });
                },
                success: function (jsonData) {
                    userModuleForm.find(`[type='password']`).val('');
                    userModuleForm.find(`[type='password']`).removeAttr("required");

                    if (jsonData.Data.UserID == null || jsonData.Data.UserID == '') {
                        dialog.modal("hide");
                        return;
                    }

                    updateEditForm(userModuleForm, jsonData.Data, userFileUploader.Files.length == 0);

                    if (userFileUploader.Files.length > 0) {
                        userFileUploader.targetId = jsonData.Data.UserID;
                        userFileUploader.upload();
                        return;
                    }

                    toastr.success(jsonData.Message, jsonData.Title);

                    lockFormInputs(userModuleForm, false, function () {
                        submitUserBtn.html(submitUserBtn.data("text"));
                    });
                }
            });

            $(userModuleForm).on("click", ".user-image .rotateBtn:not(.disabled) > span", function (e) {
                let _this = $(this)
                _this.parent(".rotateBtn").addClass("disabled");
                lockFormInputs(userModuleForm, true);

                $.post(`/api/users/imgrotate`, { UserID: $(`[name='UserID']`).val(), direction: $(this).data("direction") }, function (jsonData) {
                    if (jsonData.Result) {
                        updateEditForm(userModuleForm, jsonData.Data, true);

                        toastr.success(jsonData.Message, jsonData.Title);
                    } else {
                        toastr.error(jsonData.Message, jsonData.Title);
                    }

                    lockFormInputs(userModuleForm, false);
                    _this.parent(".rotateBtn").removeClass("disabled");
                }, "json").fail(function (jqXHR) {
                    if (jqXHR.responseJSON) {
                        toastr.error(jqXHR.responseJSON.Message, jqXHR.responseJSON.Title);
                    } else if (jqXHR.responseText) {
                        toastr.error(jqXHR.responseText);
                    } else {
                        toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoInternetConnection);
                    }

                    lockFormInputs(userModuleForm, false);
                    _this.parent(".rotateBtn").removeClass("disabled");
                });
            });
        },
        onHidden: function () {
            removeHashParam("settings");
        }
    });
}

function userFileUploaderDone(progress, isDone) {
    if (progress.statusOk) {
        progress.el.parent().children('.file-progress-bar').text(`${progress.percent}%`);
        progress.el.parent().children('.file-progress-bar').width(`${progress.percent}%`);
        if (progress.percent == 100 && isDone) {
            updateEditForm(userModuleForm, progress.jsonData, true);

            toastr.success(LOCAL_VARIABLES.StaticText.Messages.SuccessSaved, LOCAL_VARIABLES.StaticText.Messages.Title);
            lockFormInputs(userModuleForm, false, function () {
                submitUserBtn.html(submitUserBtn.data("text"));
                setTimeout(function () {
                    progress.el.parent().children('.file-progress-bar').text('');
                    progress.el.parent().children('.file-progress-bar').width(0);
                }, 500);
            });
        }
    } else {
        toastr.error(LOCAL_VARIABLES.StaticText.Messages.userFileUploaderror, LOCAL_VARIABLES.StaticText.Messages.Title);
        lockFormInputs(userModuleForm, false, function () {
            submitUserBtn.html(submitUserBtn.data("text"));
            setTimeout(function () {
                progress.el.parent().children('.file-progress-bar').text('');
                progress.el.parent().children('.file-progress-bar').width(0);
            }, 500);
        });
    }
}