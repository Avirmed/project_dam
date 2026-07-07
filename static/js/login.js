let loginForm = $("#loginForm");
loginForm.validate();

let submitBtn = loginForm.find("button[type='submit']");
submitBtn.attr("data-text", submitBtn.html());

if (LOCAL_VARIABLES.Authorization) {
    delete LOCAL_VARIABLES.Authorization;
}
setLocalStorage(false);

loginForm.ajaxForm({
    url: "/api/users/login",
    type: "post",
    dataType: "json",
    beforeSubmit: function () {
        lockFormInputs(loginForm, true);
        submitBtn.html(`${LOCAL_VARIABLES.StaticText.Icon.LoadingCog} ${submitBtn.text()}`);
    },
    success: function (jsonData) {
        if (jsonData.Result) {
            if (jsonData.Data) {
                LOCAL_VARIABLES.Authorization = jsonData.Data;
                setLocalStorage();
            }

            toastr.success(jsonData.Message, jsonData.Title);
            setTimeout(function () {
                let url = new URL(window.location.href);
                let params = new URLSearchParams(url.search);
                let next = params.get('next');

                if (jsonData.Data.UserType == 4) {
                    window.location.href = '/';
                } else {
                    if (next && next != "/logout") {
                        window.location.href = next;
                    } else {
                        window.location.href = '/dashboard';
                    }
                }
            }, 1000);
        } else {
            toastr.error(jsonData.Message, jsonData.Title);
            lockFormInputs(loginForm, false, function () {
                submitBtn.html(submitBtn.data("text"));
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

        lockFormInputs(loginForm, false, function () {
            submitBtn.html(submitBtn.data("text"));
            $("input[name='content[UserName]']").focus();
        });
    }
});