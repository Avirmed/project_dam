const ROOT_INDEX = $("body").attr("app");
const APP_AUTH = document.currentScript.getAttribute("data-auth");
const LOCAL_VARIABLES = localStorage.getItem(ROOT_INDEX) && localStorage.getItem(ROOT_INDEX) !== null && isJSON(localStorage.getItem(ROOT_INDEX)) ? JSON.parse(localStorage.getItem(ROOT_INDEX)) : {};
const defaultMapCenter = {
    latitude: 13.791193929946434,
    longitude: 100.52070982812401,
    zoom: 6
};
const svgPin = "M16,3.5c-4.1,0-7.5,3.4-7.5,7.5c0,5.6,7.5,13.5,7.5,13.5s7.5-7.9,7.5-13.5C23.5,6.9,20.1,3.5,16,3.5z M16,13c-1.1,0-2-0.9-2-2s0.9-2,2-2s2,0.9,2,2S17.1,13,16,13z";

$.validator.setDefaults({
    ignore: '',
    errorElement: "span",
    errorPlacement: function (error, element) {
        error.addClass("invalid-feedback");
        element.closest("div").append(error);
    },
    highlight: function (element, errorClass, validClass) {
        $(element).addClass("is-invalid");
    },
    unhighlight: function (element, errorClass, validClass) {
        $(element).removeClass("is-invalid");
    }
});

toastr.options.positionClass = "toast-bottom-left";
toastr.options.progressBar = true;
toastr.options.timeOut = 2000;

let tmpDate = new Date();
$.extend($.fn.datepicker.defaults, {
    language: document.documentElement.lang,
    format: "yyyy-mm-dd",
    todayBtn: "linked",
    todayHighlight: true,
    autoclose: true
});

function isObject(val) {
    return Object.prototype.toString.call(val) === '[object Object]';
}

function isNumeric(val) {
    return (typeof val === 'number' || (typeof val === 'string' && val.trim() !== '')) && !isNaN(val);
}

function getHashParams() {
    const hash = window.location.hash.substring(1);
    if (!hash) return null;

    const params = {};
    const searchParams = new URLSearchParams(hash);

    for (const [key, value] of searchParams.entries()) {
        params[key] = value;
    }

    return params;
}

function removeHashParam(paramKey) {
    const hash = window.location.hash.substring(1);
    if (!hash) return;

    const searchParams = new URLSearchParams(hash);

    searchParams.delete(paramKey);

    let newHash = decodeURIComponent(searchParams.toString());

    newHash = newHash.replace(/=(?=&|$)/g, '');

    const baseUrl = window.location.pathname + window.location.search;

    if (newHash) {
        history.replaceState(null, null, baseUrl + "#" + newHash);
    } else {
        history.replaceState(null, null, baseUrl);
    }
}

function checkHashParams() {
    const params = getHashParams();
    if (!params) return;

    if ("logout" in params) {
        if (typeof logout === "function") {
            logout();
        } else {
            console.warn("logout функц тодорхойлогдоогүй байна!");
        }
    }

    if ("settings" in params) {
        if (typeof userSettings === "function") {
            userSettings();
        }
    }
}

window.addEventListener('hashchange', checkHashParams, false);
document.addEventListener('DOMContentLoaded', checkHashParams);

$.ajax({
    url: `/main/init`,
    type: 'POST',
    async: false,
    dataType: "json",
    success: function (jsonData) {
        LOCAL_VARIABLES.StaticText = jsonData;
        setLocalStorage();
    }
});

let isUserChecking = false;
function initProject() {
    if (LOCAL_VARIABLES.StaticText === undefined) {
        $.ajax({
            url: `/main/init`,
            type: 'POST',
            async: false,
            dataType: "json",
            success: function (jsonData) {
                LOCAL_VARIABLES.StaticText = jsonData;
                setLocalStorage();
            }
        });
    } else {
        if ($("body").attr("app-dashboard") != undefined && LOCAL_VARIABLES.Authorization == undefined) {
            window.location.href = '/logout';
            throw new Error("Authorization is undefined");
        }

        if (
            !isUserChecking
            && $("body").attr("app-login") == undefined 
        ) {
            isUserChecking = true;

            $.ajax({
                url: `/api/users/check`,
                method: "POST",
                data: LOCAL_VARIABLES.Authorization,
                async: false,
                dataType: "json",
                success: function (jsonData) {
                    if ($("body").attr("app-dashboard") != undefined) {
                        if (jsonData.Result) {
                            if (
                                LOCAL_VARIABLES.Authorization.UserType != jsonData.UserType
                            ) {
                                LOCAL_VARIABLES.Authorization.UserType = jsonData.UserType;
                                LOCAL_VARIABLES.Authorization.Permission = jsonData.Permission;
                                setLocalStorage();
                                location.reload();
                            }
                        } else {
                            delete LOCAL_VARIABLES.Authorization;
                            setLocalStorage();
                            window.location.href = '/logout';
                        }
                    }else{
                        if (jsonData.Result) {
                            LOCAL_VARIABLES.Authorization.UserType = jsonData.UserType;
                            LOCAL_VARIABLES.Authorization.Permission = jsonData.Permission;
                            LOCAL_VARIABLES.Authorization.Theme = jsonData.Theme;
                            setLocalStorage(false);
                        }
                    }
                },
                error: function (jqXHR) {
                    setTimeout(function () {
                        delete LOCAL_VARIABLES.Authorization;
                        setLocalStorage(false);
                        if ($("body").attr("app-dashboard") != undefined) {
                            window.location.href = '/logout';
                        }
                    }, 200);
                }
            });
        }

        if (LOCAL_VARIABLES.StaticText.APP_SETTINGS) {
            let settings = LOCAL_VARIABLES.StaticText.APP_SETTINGS;
            for (let key in settings) {
                switch (key) {
                    case 'APP_TITLE':
                        if ($("body").attr("app-dashboard") == undefined) {
                            $(".header .header-left > a span").text(settings[key]);
                            document.title = settings[key];
                        }
                        break;
                    case 'APP_DASHBOARD_TITLE':
                        if ($("body").attr("app-dashboard") != undefined) {
                            $("#sidebar .sidebar-logo span").text(settings[key]);
                            document.title = settings[key];
                        }
                        break;
                    case 'APP_FOOTER':
                        $(`#${key}`).text(settings[key]);
                        break;
                    case 'APP_COLOR':
                        $("#app-style").html(`
                            :root {
                                --app-base-color: ${settings[key]};
                            }    
                        `);
                        break;
                }
            }
        }

        if (LOCAL_VARIABLES.Authorization && 'Theme' in LOCAL_VARIABLES.Authorization) {
            let theme = LOCAL_VARIABLES.Authorization.Theme == 1 ? "light" : "dark";
            if (theme != $("html").attr("data-theme") && $("body").attr("app-login") == undefined) {
                $("html").attr("data-theme", theme);
            }
        }
    }
}

window.addEventListener("storage", function () {
    if (
        localStorage.getItem(ROOT_INDEX)
        && localStorage.getItem(ROOT_INDEX) !== null
        && isJSON(localStorage.getItem(ROOT_INDEX))
    ) {
        let tmpJSON = JSON.parse(localStorage.getItem(ROOT_INDEX));

        Object.keys(LOCAL_VARIABLES).forEach(key => delete LOCAL_VARIABLES[key]);
        Object.assign(LOCAL_VARIABLES, tmpJSON);
    }

    initProject();
});

function setLocalStorage(dispatchEvent = true) {
    LOCAL_VARIABLES.timeStamp = Date.now();
    localStorage.setItem(ROOT_INDEX, JSON.stringify(LOCAL_VARIABLES));

    if (!dispatchEvent) return;

    const event = new CustomEvent("storage", { LOCAL_VARIABLES });
    window.dispatchEvent(event);
}

async function clearAllCaches() {
    const keys = await caches.keys();
    for (const key of keys) {
        await caches.delete(key);
    }
}

$(document).keydown(function (event) {
    if (event.altKey && event.code == "KeyR") {
        delete LOCAL_VARIABLES.StaticText;
        setLocalStorage(false);
        clearAllCaches();
        location.reload();
    }
});

initProject();

$.validator.addMethod("lettersonly", function (value, element) {
    return this.optional(element) || /^[a-z]+$/i.test(value);
}, LOCAL_VARIABLES.StaticText.Messages.LettersOnly);

function lockFormInputs(container, lock, callback) {
    if (typeof container !== 'undefined' && typeof lock !== 'undefined') {
        if (lock) {
            $(":input", container).addClass("disabled");
            $(":input", container).prop("disabled", true);
        } else {
            setTimeout(function () {
                $(":input:not([blocked])", container).removeClass("disabled");
                $(":input:not([blocked])", container).prop("disabled", false);
                if (callback) {
                    callback();
                }
            }, 500);
        }
    }
}

function getParentMenus(item) {
    let parentTag = [];

    return parentTag;
}

if ($(".page-breadcrumb").length > 0) {
    let breadcrumb = $(".page-breadcrumb .breadcrumb");
    let selectedMenu = $("#sidebar-menu a.active").length ? $("#sidebar-menu a.active") : $("#sidebar-menu a.open");

    if (selectedMenu.length == 0) {
        selectedMenu = $("#sidebar-menu li.active a");
    }

    if (selectedMenu.length > 0) {
        $(".page-breadcrumb").find("h2 span.text").text(selectedMenu.text().trim());

        let parentTag = [];

        function up2ParentMenu(item) {
            parentTag.unshift(item.children("a"));

            if (item.parent().closest(".submenu").length) {
                up2ParentMenu(item.parent().closest(".submenu"));
            }
        }

        up2ParentMenu(selectedMenu.closest(".submenu"));

        parentTag.forEach(element => {
            if (element.text().trim() == '') return;

            breadcrumb.append(`<li class="breadcrumb-item">${element.text().trim()}</li>`);
        });

        breadcrumb.append(`<li class="breadcrumb-item"><a href="${selectedMenu.attr("href")}">${selectedMenu.text().trim()}</a></li>`);

        if (breadcrumb.find("li").length > 0 && breadcrumb.find("li").eq(0).text().trim() == '') {
            if ($("body").attr("app-dashboard") != undefined) {
                breadcrumb.find("li").eq(0).find("a").attr("href", "/dashboard");
            }
        }

        if (breadcrumb.find("li").length > 1 && ["Home", "Dashboard"].includes(breadcrumb.find("li").eq(1).text().trim())) {
            breadcrumb.closest(".page-breadcrumb").remove();
        }
    }
}

if ($("#sidebar-menu a.active").length > 0) {
    let parentTag = [];

    function up2ParentMenu(item) {
        parentTag.unshift(item.children("a"));

        if (item.parent().closest(".submenu").length) {
            up2ParentMenu(item.parent().closest(".submenu"));
        }
    }

    up2ParentMenu($("#sidebar-menu a.active").closest(".submenu"));

    parentTag.forEach(element => {
        element.click();
    });
}

if ($("#sidebar-menu a.open").length > 0) {
    $("#sidebar-menu a.open").click().removeClass("open");
}

let tmpAxisDataRow = `
    <tr>
        <td class="drag-btn">*</td>
        <td><span class="deleteBtn" role="button">${LOCAL_VARIABLES.StaticText.Icon['-']}</span></td>
    </tr>
`;

$(document).on("click", "table.table-configure .addBtn", function (e) {
    let table = $(this).closest("table");
    let inputFieldNumber = table.find("thead th").length - 2;
    let tmpRow = $(tmpAxisDataRow);

    for (let i = 0; i < inputFieldNumber; i++) {
        tmpRow.find(".drag-btn").after(`<td contenteditable="true" class="text-${table.data("align")}"></td>`);
    }

    table.find("tbody").append(tmpRow);
});

$(document).on("click", "table.table-configure .deleteBtn", function (e) {
    $(this).closest("tr").remove();
});

function initForm(form) {
    form.find("label").each(function (i, el) {
        let label = $(el);
        let parentEl = label.closest(".row");
        let required = "";

        if (parentEl.find("[type='checkbox'], [type='radio']").length > 0) {
            return;
        }

        if (parentEl.find("input[required]").length > 0) {
            required = `<small class="text-danger" title="${LOCAL_VARIABLES.StaticText.RequiredField}">*</small> `
        }

        if (label.length && label.text().trim() !== '') {
            label.html(`${required}${label.text().trim()}`);
        }
    });

    $(".datepicker", form).datepicker({
        container: form.closest(".modal"),
        onSelect: function (dateText, inst) {
            $(this).focus();
        }
    });

    $("table.table-configure tbody", form).sortable({
        handle: ".drag-btn",
        start: function (event, ui) {
            ui.placeholder.height(ui.item.height());
        },
        update: function (event, ui) { }
    });
}

function updateEditForm(tmpForm, jsonData, updateIMG = false) {
    if (tmpForm.length == 0 || jsonData == undefined) {
        return;
    }

    $.each(jsonData, function (k, v) {
        const $input = tmpForm.find(`[name='${k}']`);

        if (k.includes("ImageSource")) {
            let deleteBtn = $input.parent().find("input:checkbox");

            if (
                deleteBtn.length
                && deleteBtn.attr("name").includes("delete")
            ) {
                if (v == null || v == '') {
                    deleteBtn.parent().addClass("d-none");
                } else {
                    deleteBtn.parent().removeClass("d-none");
                }
                deleteBtn.prop("checked", false);

                return;
            }
        }

        if (k == "self" && v == true && "UserID" in jsonData && "UserName" in jsonData) {
            let profileDropdown = $(".profile-dropdown");
            profileDropdown.find("img").attr("src", jsonData.Image);
            profileDropdown.find(".card-header h6").text(jsonData.UserName);
            profileDropdown.find(".card-header p").text(LOCAL_VARIABLES.StaticText.UserTypes[jsonData.UserType]);

            if (LOCAL_VARIABLES.Authorization.Theme != jsonData.Theme) {
                LOCAL_VARIABLES.Authorization.Theme = jsonData.Theme;
                setLocalStorage();
            }
        }

        if (k == "Latitude") {
            if (
                jsonData.Latitude != null && jsonData.Latitude != ""
                && "Longitude" in jsonData && jsonData.Longitude != null && jsonData.Longitude != ""
                && "Zoom" in jsonData && jsonData.Zoom != null && jsonData.Zoom != ""
            ) {
                $input.change();
            }
        }

        if (
            updateIMG
            && k.endsWith("Image")
            && v != null && v != ""
        ) {
            let imagePreview = tmpForm.find(`.image-preview .${k}`);

            if (imagePreview.length) {
                imagePreview.attr("src", v);

                if (`${k}MD` in jsonData) {
                    imagePreview.attr("src", jsonData[`${k}MD`]);
                } else if (`${k}SM` in jsonData) {
                    imagePreview.attr("src", jsonData[`${k}SM`]);
                }

                if (`${k}XL` in jsonData) {
                    imagePreview.attr("data-href", jsonData[`${k}XL`]);
                } else if (`${k}LG` in jsonData) {
                    imagePreview.attr("data-href", jsonData[`${k}LG`]);
                } else if (`${k}MD` in jsonData) {
                    imagePreview.attr("data-href", jsonData[`${k}MD`]);
                } else if (`${k}SM` in jsonData) {
                    imagePreview.attr("data-href", jsonData[`${k}SM`]);
                } else {
                    imagePreview.attr("data-href", v);
                }
            }
        }

        if (
            $input.is(`input[type="hidden"]`)
            && $input.index() == 0
            && k.includes("ID")
            && v != null && v != ""
            && typeof tmpForm.attr("data-url") !== 'undefined' && tmpForm.attr("data-url") !== false
        ) {
            window.history.replaceState("", "", tmpForm.attr("data-url").replace("#", v));

            if (typeof tmpForm.attr("form-title") !== 'undefined' && tmpForm.attr("form-title") !== false) {
                tmpForm.closest(".modal").find(".modal-title").html(`${tmpForm.attr("form-title")} - ${LOCAL_VARIABLES.StaticText.Edit}`);
            }
        }

        if ($input.is(":checkbox")) {
            $input.prop('checked', v == $input.last().val() || v === true);
            $input.prop("disabled", false);

            return;
        }

        $input.val(v);

        if ($input.hasClass("datepicker")) {
            $input.datepicker("setDate", v);
        }

        if ($input.hasClass("selectTwo") || $input.is("select")) {
            $input.attr("data-selectid", v);
            $input.trigger("change");
        }
    });

    tmpForm.find(".app-json-data").each(function () {
        let configContainer = $(this);
        let jsonField = configContainer.data("field");

        if (jsonField in jsonData) {
            if (!isJSON(jsonData[jsonField])) {
                return;
            }

            let jsonFields = jsonData[jsonField];

            if ('status' in jsonFields) {
                configContainer.find(`input[name="status"]`).prop("checked", jsonFields.status);
            }

            if ('color' in jsonFields) {
                configContainer.find(`input[name="color"]`).prop("checked", jsonFields.color);
            }

            if ('configs' in jsonFields) {
                $.each(jsonFields['configs'], function (key, value) {
                    if (isObject(value)) {
                        let groupTag = configContainer.find(`.field-check[data-field="${key}"]`);
                        if (groupTag.length) {
                            groupTag.find(":checkbox").prop("checked", value.checked);
                            groupTag.find(":text").val(value.text);

                            if ('radio' in value && value.radio != null && value.radio !== '') {
                                groupTag.find(`:radio[value="${value.radio}"]`).prop("checked", true);
                            }
                        }
                    } else if (Array.isArray(value)) {
                        let configTable = configContainer.find(`.table-configure[data-field="${key}"]`);
                        let configTableHeader = configTable.find("thead");
                        let configTableBody = configTable.find("tbody");
                        configTableBody.empty();

                        let columns = [];
                        configTableHeader.find("th[data-value]").each(function () {
                            columns.push($(this).data("value"));
                        });

                        $.each(value, function (i, rowData) {
                            let tmpRow = $(`<tr/>`);

                            tmpRow.append(`<td class="drag-btn">${i + 1}</td>`);

                            $.each(columns, function (idx, colKey) {
                                let cellValue = rowData[colKey] !== undefined ? rowData[colKey] : "";
                                tmpRow.append(`<td contenteditable="true" class="text-${configTable.data("align")}">${cellValue}</td>`);
                            });

                            tmpRow.append(`<td><span class="deleteBtn" role="button">${LOCAL_VARIABLES.StaticText.Icon['-']}</span></td>`);

                            configTableBody.append(tmpRow);
                        });
                    } else {
                        configContainer.find(`:input[name="${key}"]`).val(value);

                        if (configContainer.find(`:input[name="${key}"]`).hasClass("selectTwo") || configContainer.find(`:input[name="${key}"]`).is("select")) {
                            configContainer.find(`:input[name="${key}"]`).attr("data-selectid", value);
                            configContainer.find(`:input[name="${key}"]`).trigger("change");
                        }

                        if (configContainer.find(`:input[name="${key}"]`).is(":checkbox")) {
                            configContainer.find(`:input[name="${key}"]`).prop("checked", !!value);
                        }
                    }
                });
            }
        }
    });
}

function serializeEditForm(form) {
    form.find(":checkbox").each(function () {
        let checkbox = $(this);
        let checkboxHidden = checkbox.parent().find(`input[type='hidden'][name='${checkbox.attr("name")}']`);

        if (checkboxHidden.length) {
            if (checkbox.prop("checked")) {
                checkboxHidden.prop("disabled", true);
            } else {
                checkbox.prop("disabled", true);
            }
        }
    });

    for (let instance in CKEDITOR.instances) {
        CKEDITOR.instances[instance].updateElement();
    }
}

function initTabulators() {
    $(".app-tabulator-table:not(.init-column)").each(function () {
        if (!this.hasAttribute("cfg-ajax-url")) {
            toastr.error(LOCAL_VARIABLES.StaticText.Messages.TableNotFound);
            return;
        }

        let tableTag = $(this);
        let tablePageSize = tableTag.attr("cfg-page-size") ? parseInt(tableTag.attr("cfg-page-size")) : 50;
        let tablePageSizeSelector = tableTag.attr("cfg-page-size-selector") ? tableTag.attr("cfg-page-size-selector").split(",").map(item => parseInt(item)) : [25, 50, 100, 200];

        let searchInput = tableTag.closest(".tabulator-container").find(".tabulator-search-input");
        let searchFilters = tableTag.closest(".tabulator-container").find(".tabulator-filters");

        let tmpMenu = tableTag.closest(".tabulator-container").find(".tmp-menu").html();
        let tmpControl = tableTag.closest(".tabulator-container").find(".tmp-control").html();
        tableTag.closest(".tabulator-container").find(".tmp-menu").remove();
        tableTag.closest(".tabulator-container").find(".tmp-control").remove();

        let debounceTimer = null;

        let tableGroups = [];
        if (this.hasAttribute("cfg-groupBy")) {
            tableGroups = tableTag.attr("cfg-groupBy").split(",");
        }

        let extraParams = {};
        if (this.hasAttribute("cfg-extra-params")) {
            let rawData = tableTag.attr("cfg-extra-params");
            try {
                let validJsonString = rawData.replace(/'/g, '"');
                extraParams = JSON.parse(validJsonString);
            } catch (e) {
                console.error("JSON parsing failed. Invalid data format:", e);
            }
        }

        if (!tablePageSizeSelector.includes(tablePageSize)) {
            tablePageSize = tablePageSizeSelector[0];
        }

        function appendControl(arr) {
            if (arr && arr.length > 0) {
                arr.forEach(item => {
                    let controlHTML = tmpControl;

                    if (tableTag.attr("cfg-control-depth") !== undefined) {
                        let controlTexts = tableTag.attr("cfg-control-depth").split(",");
                        let depthIndex = null;
                        for (let key in item) {
                            if (key.includes("Depth")) {
                                depthIndex = key;
                                break
                            }
                        }

                        if (depthIndex) {
                            let tmp = $(controlHTML);
                            let btn = tmp.find(".addBtn");
                            btn.html(`${LOCAL_VARIABLES.StaticText.Icon.Add} ${controlTexts[item[depthIndex]]}`);

                            if (item[depthIndex] == tableTag.attr("cfg-control-depth-level")) {
                                btn.html(`${LOCAL_VARIABLES.StaticText.Icon.List} ${controlTexts[item[depthIndex]]}`);
                                btn.removeClass("addBtn");
                                btn.addClass(`addBtn${item[depthIndex]}`);
                            }

                            controlHTML = tmp.prop('outerHTML');
                        }
                    }

                    item['control'] = controlHTML;

                    if (item.children != undefined) {
                        appendControl(item.children)
                    }
                });
            }
        }

        let tableConfiguration = {
            layout: "fitColumns",
            resizableColumnFit: true,
            sortMode: "remote",
            pagination: this.hasAttribute("cfg-pagination"),
            paginationMode: "remote",
            paginationSize: tablePageSize,
            paginationSizeSelector: tablePageSizeSelector,
            paginationCounter: function (pageSize, currentRow, currentPage, totalRows, totalPages) {
                if (totalRows === 0) {
                    return `${totalRows} rows`;
                }

                let startRow = (currentPage - 1) * pageSize + 1;
                let endRow = Math.min(currentPage * pageSize, totalRows);

                return `Showing ${startRow} - ${endRow} of ${totalRows} rows`;
            },

            placeholder: LOCAL_VARIABLES.StaticText.EmptyData,
            movableRows: this.hasAttribute("cfg-movable-rows"),
            selectableRows: this.hasAttribute("cfg-selectable-rows"),
            columnDefaults: {
                headerTooltip: true,
            },

            groupBy: tableGroups,

            rowFormatter: function (row) {
                let element = row.getElement();
                element.setAttribute("data-id", row.getIndex());
            },

            index: this.getAttribute("cfg-index"),
            ajaxURL: this.getAttribute("cfg-ajax-url"),
            ajaxContentType: "json",
            ajaxConfig: {
                method: "POST",
            },
            ajaxParams: function () {
                let params = {
                    filters: {}
                };

                if (extraParams !== undefined && Object.keys(extraParams).length > 0) {
                    params = { ...params, ...extraParams };
                }

                if (searchFilters.length > 0) {
                    searchFilters.find(":input").serializeArray().forEach(function (item) {
                        if (item.value.trim() != '') {
                            params.filters[item.name] = item.value;
                        }
                    });
                    if (Object.keys(params.filters).length == 0) {
                        delete params.filters;
                    }
                }

                if (searchInput.length && searchInput.val().trim() != '') {
                    params['search'] = searchInput.val().trim();
                }

                return params;
            },
            ajaxResponse: function (url, params, response) {
                if (!tableTag.hasClass("init-column")) {
                    tableTag.addClass("init-column");

                    response.column.forEach(function (col) {
                        if (col.formatter === "rownum") {
                            col.formatter = function (cell) {
                                let row = cell.getRow();
                                let table = row.getTable();
                                let pageSize = table.getPageSize();
                                let page = table.getPage();
                                let rowIndex = row.getPosition(true);
                                return (page - 1) * pageSize + rowIndex;
                            };
                            col.hozAlign = "center";
                            col.headerHozAlign = "center";
                            col.width = col.width || 50;
                        }

                        if (col.formatter === "customStatus") {
                            col.formatter = function (cell) {
                                let value = cell.getValue();
                                return `<span class="${LOCAL_VARIABLES.StaticText.StatusLabel[value].class}">${LOCAL_VARIABLES.StaticText.StatusLabel[value].text}</span>`;
                            };
                        }

                        if (col.field.includes("Image")) {
                            col.formatter = function (cell) {
                                let url = cell.getValue();
                                return `<img src="${url}" width="${col.width || 80}" class="img-thumbnail">`;
                            };
                            col.hozAlign = "center";
                            col.headerHozAlign = "center";
                        }

                        if (col.field.includes("checkbox")) {
                            col.formatter = function (cell) {
                                let value = cell.getValue();
                                let input = document.createElement("input");
                                input.type = "checkbox";
                                input.checked = !!value;
                                input.className = "form-check-input";

                                input.addEventListener("change", function () {
                                    cell.setValue(this.checked);
                                });

                                return input;
                            };
                            col.hozAlign = "center";
                            col.headerHozAlign = "center";
                        }

                        if (tableTag.attr("cfg-include-link") !== undefined) {
                            if (col.field.includes(tableTag.attr("cfg-include-link"))) {
                                col.formatter = function (cell) {
                                    let data = cell.getData();

                                    return `<a href="${data[tableTag.attr("cfg-link-index")]}">${cell.getValue()}</a>`;
                                };
                            }
                        }
                    });

                    if (tableTag.attr("cfg-menu") !== undefined) {
                        response.column.push({
                            field: "control",
                            width: 60,
                            headerSort: false,
                            resizable: false,
                            headerHozAlign: "right",
                            hozAlign: "right",
                            vertAlign: "middle",
                            download: false,
                            titleFormatter: function () {
                                return tmpMenu;
                            },
                            formatter: function (cell) {
                                return cell.getValue();
                            }
                        });
                    }

                    table.setColumns(response.column);

                    setTimeout(function () {
                        table.options.sortMode = false;
                        table.setSort(response.sort);
                        table.options.sortMode = "remote";
                    }, 10);
                }

                setTimeout(function () {
                    tableTag.removeClass("loading");
                }, 200);

                if (tableTag.attr("cfg-control") !== undefined) {
                    appendControl(response.data);
                }

                tableTag.data("total", response.last_row).attr("data-total", response.last_row);

                if ($(".page-breadcrumb").length > 0 && typeof response.filtered !== 'undefined' && tableTag.closest(".tabulator-container").parent().hasClass("content")) {
                    jQuery({ Counter: 0 }).animate({ Counter: response.filtered }, {
                        duration: 200,
                        easing: 'swing',
                        step: function () {
                            $(".page-breadcrumb").find("h2 span.content-counter").text(`(${Math.ceil(this.Counter)})`);
                        }
                    });
                }

                if (!table.options.pagination) {
                    return response.data;
                }

                return response;
            }
        };

        if (this.hasAttribute("cfg-data-tree")) {
            tableConfiguration['dataTree'] = true;
            tableConfiguration['dataTreeChildIndent'] = 25;
            tableConfiguration['dataTreeStartExpanded'] = false;
            tableConfiguration['dataTreeChildField'] = "children";
            tableConfiguration['dataTreeElementColumn'] = tableTag.attr("cfg-data-tree");
        }

        if (this.hasAttribute("cfg-minHeight")) {
            tableConfiguration['minHeight'] = tableTag.attr("cfg-minHeight");
        }

        if (this.hasAttribute("cfg-height")) {
            tableConfiguration['height'] = tableTag.attr("cfg-height");
        }

        let table = new Tabulator(`#${tableTag.attr("id")}`, tableConfiguration);

        table.loading = false;
        table.on("dataLoading", () => table.loading = true);
        table.on("dataLoaded", () => table.loading = false);

        if (searchFilters.length > 0) {
            searchFilters.find(":input").on("change", function () {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    if (!table.loading) {
                        table.setData();
                    }
                }, 200);
            });
        }

        if (this.hasAttribute("cfg-data-tree")) {
            table.on("dataTreeRowExpanded", function (row) {
                let rowData = row.getData();

                if (rowData.children && rowData.children.length) {
                    return;
                }

                let parentId = rowData[tableTag.attr("cfg-index")];

                fetch(`${tableTag.attr("cfg-ajax-url")}/${parentId}`)
                    .then((res) => res.json())
                    .then((data) => {
                        if (data.length === 0) {
                            row.update({ children: null });
                            row.getElement().classList.remove("tabulator-tree-branch");
                        } else {
                            if (tableTag.attr("cfg-control") !== undefined) {
                                appendControl(data);
                            }
                            let updateData = { children: data };

                            let tmpData = row.getData();
                            let counterIndex = null;
                            for (let key in tmpData) {
                                if (key.includes("ChildCount") || key.includes("CountChild")) {
                                    counterIndex = key;
                                    break
                                }
                            }

                            if (counterIndex && "children" in tmpData) {
                                updateData[counterIndex] = data.length
                            }

                            row.update(updateData);
                        }
                    });
            });

            table.on("rowDeleted", function (row) {
                let parentRow = row.getTreeParent();

                if (!parentRow) {
                    return;
                }

                let tmpData = parentRow.getData();
                let counterIndex = null;
                for (let key in tmpData) {
                    if (key.includes("ChildCount") || key.includes("CountChild")) {
                        counterIndex = key;
                        break
                    }
                }

                if (counterIndex && "children" in tmpData) {
                    parentRow.update({ [counterIndex]: tmpData.children.length - 1 });
                }
            });
        }
    });
}
initTabulators();

function loadImageAsBase64(url) {
    return new Promise((resolve) => {
        const img = new Image();
        img.setAttribute("crossOrigin", "anonymous");
        img.onload = function () {
            const canvas = document.createElement("canvas");
            canvas.width = this.naturalWidth || 32;
            canvas.height = this.naturalHeight || 32;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(this, 0, 0);
            const dataURL = canvas.toDataURL("image/jpeg");
            resolve(dataURL);
        };
        img.onerror = function () {
            console.warn("Image load failed:", url);
            resolve(null);
        };
        img.src = url;
    });
}

async function exportPdfWithImages(table, tableName, imageSize = 20) {
    let imageField = "Image";

    const columns = table.getColumnDefinitions();
    const visibleCols = columns.filter(col => col.visible !== false && col.title !== undefined);
    const headers = visibleCols.map(col => ({ header: col.title, dataKey: col.field }));

    const rows = table.getRows();
    const data = [];
    let i = 1;

    for (const row of rows) {
        const rowData = row.getData();
        const rowElement = row.getElement();
        const imgEl = rowElement.querySelector("img");

        let processedRow = {};

        for (const col of headers) {
            const field = col.dataKey;

            if (field === imageField && imgEl) {
                const canvas = document.createElement("canvas");
                canvas.width = imgEl.naturalWidth;
                canvas.height = imgEl.naturalHeight;
                const ctx = canvas.getContext("2d");
                ctx.drawImage(imgEl, 0, 0);
                const base64 = canvas.toDataURL("image/png");
                processedRow[field] = { content: base64 };
            } else {
                if (field === "rownum") {
                    processedRow[field] = i++;
                } else {
                    processedRow[field] = rowData[field];
                }
            }
        }

        data.push(processedRow);
    }

    const doc = new jsPDF({ orientation: "landscape" });

    doc.autoTable({
        styles: {
            font: "Arial",
            fontStyle: "normal",
        },
        bodyStyles: {
            minCellHeight: imageSize + 4,
        },
        columnStyles: {
            [imageField]: {
                cellWidth: imageSize + 8,
            }
        },
        columns: headers,
        body: data,
        didParseCell: function (data) {
            if (data.column.dataKey === imageField && !data.cell.text.includes("Image")) {
                data.cell.text = "";
            }
        },
        didDrawCell: function (data) {
            if (data.column.dataKey === imageField) {
                const base64 = data.cell.raw?.content;
                if (base64) {
                    const imgHeight = imageSize;
                    const imgWidth = imageSize;

                    data.doc.addImage(base64, "PNG", data.cell.x + 2, data.cell.y + 2, imgWidth, imgHeight);

                    if (data.row.height < imageSize + 4) {
                        data.row.height = imageSize + 4;
                    }
                }
            }
        }
    });

    doc.save(`${tableName}.pdf`);
}

$(document).on("click", ".tabulator-export button", function (e) {
    let type = $(this).data("type");
    let tableEl = $(this).closest(".tabulator-container").find(".app-tabulator-table");
    let tableName = "table";

    if (tableEl.length == 0) {
        toastr.error(LOCAL_VARIABLES.StaticText.Messages.TableNotFound);
        return;
    }

    if (typeof tableEl.attr("data-name") !== "undefined") {
        tableName = tableEl.data("name")
    }

    let table = Tabulator.findTable(tableEl[0])[0];

    switch (type) {
        case "csv":
            table.download("csv", `${tableName}.csv`, {
                bom: true
            });
            break;
        case "xlsx":
            table.download("xlsx", `${tableName}.xlsx`, { sheetName: "Sheet" });
            break;
        case "pdf":
            exportPdfWithImages(table, tableName);
            break;
        case "print":
            table.print(false, {
                printStyled: true,
                printAsHtml: true,
            });
            break
    }
});

function reloadTabulator(input) {
    let tableEl = $(input).closest(".tabulator-container").find(".app-tabulator-table");
    let tableName = "table";

    if (tableEl.length == 0) {
        toastr.error(LOCAL_VARIABLES.StaticText.Messages.TableNotFound);
        return;
    }

    if (tableEl.hasClass("loading")) {
        return;
    }

    if (typeof tableEl.attr("data-name") !== "undefined") {
        tableName = tableEl.data("name")
    }

    let table = Tabulator.findTable(tableEl[0])[0];
    table.setData();
    tableEl.addClass("loading");
}

function updateTabulatorDataTree(tableEl, rowData, mode = '', data = null) {
    if (mode == '') {
        return;
    }

    let table = Tabulator.findTable(tableEl[0])[0];
    let index = tableEl.attr("cfg-index");

    if (mode == "self") {
        let row = tabulatorFindRow(table.getRows(), rowData.row[index]);
        if (row) {
            row.update(data);
        }

        return;
    }

    if (mode == "parent") {
        if (rowData.level == -1) {
            table.setData();
        } else {
            let row = tabulatorFindRow(table.getRows(), rowData.row[index]);
            if (row) {
                row.update({ children: [] });
                row.treeExpand();
            }
        }

        return;
    }
}

$(document).on("keydown", ".tabulator-search-input", function (e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        reloadTabulator(this);
    }
});

$(document).on("click", ".tabulator-search-btn", function (e) {
    reloadTabulator(this);
});

function tabulatorFindData(data, field, targetID, level = 0) {
    for (let row of data) {
        if (row[field] === targetID) return { row, level };

        if (row.children && Array.isArray(row.children)) {
            const result = tabulatorFindData(row.children, field, targetID, level + 1);
            if (result) return result;
        }
    }
    return null;
}

function tabulatorFindRow(rows, targetID) {
    for (let row of rows) {
        if (row.getIndex() == targetID) {
            return row;
        }

        let children = row.getTreeChildren();
        if (children && children.length > 0) {
            const found = tabulatorFindRow(children, targetID);
            if (found) return found;
        }
    }

    return null;
}

let prevImg;
$(document).on("change", ".image-file-choose", function () {
    let thumbnailTag = $(this).parent().find("img");
    if (prevImg == undefined) {
        prevImg = thumbnailTag.attr("src");
    }
    if (this.files && this.files[0]) {
        let reader = new FileReader();
        reader.onload = function (e) {
            thumbnailTag.attr("src", e.target.result);
            thumbnailTag.attr("data-href", e.target.result);
        };
        reader.readAsDataURL(this.files[0]);
    } else {
        thumbnailTag.attr("src", prevImg);
        thumbnailTag.attr("data-href", prevImg);
    }
});

document.addEventListener("DOMContentLoaded", function () {
    document.addEventListener('hide.bs.modal', function (event) {
        if (document.activeElement) {
            document.activeElement.blur();
        }
    });
});

$(document).on("click", ".closeBtn", function (e) {
    $(this).closest('.modal').modal('hide');
});

function isDarkColor(hexColor, percent = 0.7) {
    let r = parseInt(hexColor.substr(1, 2), 16);
    let g = parseInt(hexColor.substr(3, 2), 16);
    let b = parseInt(hexColor.substr(5, 2), 16);

    let brightness = 0.2126 * r + 0.7152 * g + 0.0722 * b;

    return brightness < 255 * percent;
}

function fileSizeConverter(bytes, decimals = 2) {
    if (!bytes) return '0 байт';

    let k = 1024;
    let dm = decimals < 0 ? 0 : decimals;

    let sizes = ['бт', 'кб', 'мб', 'гб', 'тб', 'пб'];

    let i = Math.floor(Math.log(bytes) / Math.log(k));
    let size = parseFloat((bytes / Math.pow(k, i)).toFixed(dm));

    return `${size} ${sizes[i]}`;
}

$(document).on("click", ".fileType", function (e) {
    e.preventDefault();

    if ($(this).data("url")) {
        let url = $(this).data("url");
        let ext = $(this).data("type");
        let title = `${LOCAL_VARIABLES.StaticText.Icon.File} ${LOCAL_VARIABLES.StaticText.File}`;
        let html = '';
        let dialogSize = 'xl';

        switch (ext) {
            case 'mp4':
            case 'mkv':
            case 'mov':
                title = `${LOCAL_VARIABLES.StaticText.Icon.Video} ${LOCAL_VARIABLES.StaticText.Video}`;
                html = `
                    <video
                        src="${url}"
                        class="mw-100 d-block mx-auto border border-1 rounded"
                        controls controlsList="nodownload noplaybackrate" disablePictureInPicture
                        playsinline
                        autoplay
                    ></video>
                `;
                break;
            case 'mp3':
                title = `${LOCAL_VARIABLES.StaticText.Icon.Audio} ${LOCAL_VARIABLES.StaticText.Audio}`;
                dialogSize = 'md';
                html = `
                    <audio
                        src="${url}"
                        class="mw-100 d-block mx-auto border border-1 rounded"
                        controls controlsList="nodownload"
                        autoplay
                    ></audio>
                `;
                break;
            case 'pdf':
                html = `
                    <embed
                        src="${url}"
                        type="application/pdf"
                        frameBorder="0"
                        scrolling="auto"
                        height="100%"
                        width="100%"
                        class="mw-100 d-block mx-auto border border-1 rounded"
                        style="height: 600px"
                    ></embed>
                `;
                break;
        }

        if (html == '') {
            return;
        }

        let scrollTop = $(".bootbox").scrollTop();
        bootbox.dialog({
            title: title,
            message: html,
            centerVertical: true,
            size: dialogSize,
            buttons: {
                close: {
                    label: LOCAL_VARIABLES.StaticText.Close,
                    className: 'btn-secondary btn-sm'
                }
            },
            onShown: function () {
                $(".bootbox").scrollTop(scrollTop);
            },
            onHidden: function () {
            }
        });
    }

});

function select2Ajax(inputEl, valueField, textField, targetEl = null, targetField = '') {
    if (inputEl.length == 0) {
        return;
    }

    let firstOptionText = `-- ${LOCAL_VARIABLES.StaticText.Choose} --`;
    if (inputEl.find("option:first").length > 0 && inputEl.find("option:first").text().trim() != '') {
        firstOptionText = inputEl.find("option:first").text().trim();
    }

    if (targetEl == null) {
        $.post(inputEl.data("url"), function (jsonData) {
            inputEl.html('');
            inputEl.append(new Option(firstOptionText, '', false, false));
            jsonData.data.map((data, i) => {
                inputEl.append(new Option(data[textField], data[valueField], false, false));
            });
            inputEl.select2();
            if (inputEl.attr("data-selectid")) {
                inputEl.val(inputEl.attr("data-selectid")).trigger("change");
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
    } else {
        if (targetEl.length == 0) {
            return;
        }

        targetEl.change(function () {
            if (targetEl.val() == null || targetEl.val() == '') {
                inputEl.html('');
                inputEl.append(new Option(firstOptionText, '', false, false)).trigger("change");
                return;
            } else {
                let params = {
                    filters: {}
                };
                params.filters[targetField] = targetEl.val().trim();

                $.ajax({
                    url: inputEl.data("url"),
                    method: "POST",
                    data: JSON.stringify(params),
                    contentType: "application/json",
                    success: function (jsonData) {
                        inputEl.html('');
                        inputEl.append(new Option(firstOptionText, '', false, false));
                        jsonData.data.map((data, i) => {
                            inputEl.append(new Option(data[textField], data[valueField], false, false));
                        });

                        inputEl.select2();

                        let selectId = inputEl.attr("data-selectid");
                        if (selectId) {
                            let exists = inputEl.find('option[value="' + selectId + '"]').length > 0;
                            inputEl.val(exists ? selectId : '').trigger("change");
                        } else {
                            inputEl.val('').trigger("change");
                        }
                    },
                    error: function (jqXHR) {
                        if (jqXHR.responseJSON) {
                            toastr.error(jqXHR.responseJSON.Message, jqXHR.responseJSON.Title);
                        } else if (jqXHR.responseText) {
                            toastr.error(jqXHR.responseText);
                        } else {
                            toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoInternetConnection);
                        }
                    }
                });
            }
        });

        inputEl.select2();
        inputEl.val('').trigger("change");
    }
}

function initArcGIS(mapContainerID, latitudeEl, longitudeEl, zoomEl) {
    const ICON_SIZE = 30;
    const TOUCH_MOVE_THRESHOLD = 20;
    const ZOOM_UPDATE_DELAY = 200;

    const lat = parseFloat(latitudeEl.val());
    const lon = parseFloat(longitudeEl.val());
    const zoom = parseInt(zoomEl.val());

    if (!lat || !lon || !zoom) {
        latitudeEl.val(defaultMapCenter.latitude);
        longitudeEl.val(defaultMapCenter.longitude);
        zoomEl.val(defaultMapCenter.zoom);
    }

    require([
        "esri/Map",
        "esri/views/MapView",
        "esri/Graphic",
        "esri/widgets/Expand",
        "esri/widgets/BasemapGallery",
        "esri/widgets/BasemapGallery/support/LocalBasemapsSource",
        "esri/Basemap"
    ], (EsriMap, MapView, Graphic, Expand, BasemapGallery, LocalBasemapsSource, Basemap) => {

        const view = new MapView({
            container: mapContainerID,
            map: new EsriMap({ basemap: "topo-vector" }),
            zoom: defaultMapCenter.zoom,
            center: [defaultMapCenter.longitude, defaultMapCenter.latitude],
            constraints: { rotationEnabled: false },
            navigation: { browserTouchPanEnabled: false },
            popup: {
                visibleElements: { collapseButton: false },
                dockEnabled: false,
                dockOptions: { buttonEnabled: false },
                viewModel: { includeDefaultActions: false }
            }
        });

        const basemapGallery = new BasemapGallery({
            view,
            source: new LocalBasemapsSource({
                basemaps: [
                    Basemap.fromId("topo-vector"),
                    Basemap.fromId("hybrid"),
                    Basemap.fromId("streets-vector")
                ]
            })
        });

        view.ui.add(new Expand({
            view,
            content: basemapGallery,
            expandIconClass: "esri-icon-basemap",
            expanded: false
        }), "bottom-left");

        const hasValidCoords = () => {
            const la = parseFloat(latitudeEl.val());
            const lo = parseFloat(longitudeEl.val());
            return la && lo; // 0 болон хоосон утгыг хоёуланг нь шүүнэ
        };

        const markerSymbol = {
            type: "simple-marker",
            style: "path",
            path: svgPin,
            color: "#0d6efd",
            outline: { color: "#ffffff", width: 2 },
            size: ICON_SIZE,
            xoffset: 0,
            yoffset: ICON_SIZE / 2
        };

        const pointGraphic = new Graphic({
            geometry: {
                type: "point",
                latitude: parseFloat(latitudeEl.val()),
                longitude: parseFloat(longitudeEl.val())
            },
            symbol: markerSymbol
        });

        if (hasValidCoords()) {
            view.graphics.add(pointGraphic);
        }

        let mouseWheelEvt = view.on("mouse-wheel", stopEvtPropagation);

        function stopEvtPropagation(event) {
            event.stopPropagation();
        }

        function enableMouseWheel() {
            if (!mouseWheelEvt) {
                mouseWheelEvt = view.on("mouse-wheel", stopEvtPropagation);
            }
        }

        function disableMouseWheel() {
            if (mouseWheelEvt) {
                mouseWheelEvt.remove();
                mouseWheelEvt = null;
            }
        }

        view.on("drag", ["Shift"], stopEvtPropagation);
        view.on("drag", ["Shift", "Control"], stopEvtPropagation);

        view.on("key-down", (event) => {
            const prohibited = ["+", "-", "Shift", "_", "="];
            if (prohibited.includes(event.key)) event.stopPropagation();
            event.key === "Control" ? disableMouseWheel() : enableMouseWheel();
        });

        view.on("key-up", enableMouseWheel);

        const pointers = new Map();

        view.on("pointer-down", (event) => {
            if (event.pointerType === "touch") {
                pointers.set(event.pointerId, { x: event.x, y: event.y });
            }
        });

        view.on(["pointer-up", "pointer-leave"], (event) => {
            if (event.pointerType === "touch") {
                pointers.delete(event.pointerId);
            }
        });

        view.on("pointer-move", (event) => {
            if (event.pointerType !== "touch" || pointers.size !== 1) return;
            const prev = pointers.get(event.pointerId);
            if (!prev) return;
            const dist = Math.hypot(event.x - prev.x, event.y - prev.y);
            if (dist < TOUCH_MOVE_THRESHOLD) return;
        });

        let zoomTimer = null;
        function scheduleZoomUpdate() {
            clearTimeout(zoomTimer);
            zoomTimer = setTimeout(() => {
                zoomEl.val(Math.round(view.zoom));
            }, ZOOM_UPDATE_DELAY);
        }

        view.on("drag", scheduleZoomUpdate);
        view.on("mouse-wheel", scheduleZoomUpdate);
        $(document).on("click", ".esri-widget--button[title='Zoom in']", scheduleZoomUpdate);
        $(document).on("click", ".esri-widget--button[title='Zoom out']", scheduleZoomUpdate);

        function gotoCenterLocation() {
            const z = parseInt(zoomEl.val());
            const lo = parseFloat(longitudeEl.val());
            const la = parseFloat(latitudeEl.val());
            if (isNaN(z) || isNaN(lo) || isNaN(la)) return;

            view.goTo({ zoom: z, center: [lo, la] })
                .catch((err) => {
                    if (err.name !== "AbortError") console.error(err);
                });
        }

        view.when(gotoCenterLocation);

        view.on("click", (evt) => {
            const newPoint = pointGraphic.geometry.clone();
            newPoint.longitude = evt.mapPoint.longitude;
            newPoint.latitude = evt.mapPoint.latitude;
            pointGraphic.geometry = newPoint;

            if (!view.graphics.includes(pointGraphic)) {
                view.graphics.add(pointGraphic);
            }

            latitudeEl.val(evt.mapPoint.latitude);
            longitudeEl.val(evt.mapPoint.longitude);
        });

        function updateMarkerFromInputs() {
            const la = parseFloat(latitudeEl.val());
            const lo = parseFloat(longitudeEl.val());
            if (isNaN(la) || isNaN(lo)) return;

            const newPoint = pointGraphic.geometry.clone();
            newPoint.latitude = la;
            newPoint.longitude = lo;
            pointGraphic.geometry = newPoint;
            gotoCenterLocation();
        }

        latitudeEl.on("change", updateMarkerFromInputs);
        longitudeEl.on("change", updateMarkerFromInputs);
        zoomEl.on("change", gotoCenterLocation);
    });
}

function mapMonitor(mapContainerID) {
    const RELOAD_TIME_INTERVAL = 15 * 60 * 1000;
    const ICON_SIZE = 30;
    const TOUCH_MOVE_THRESHOLD = 20;

    const mapContainer = $(`#${mapContainerID}`).parent();
    let reloadInterval = null;

    require([
        "esri/Map",
        "esri/views/MapView",
        "esri/Graphic",
        "esri/widgets/Expand",
        "esri/widgets/BasemapGallery",
        "esri/widgets/BasemapGallery/support/LocalBasemapsSource",
        "esri/Basemap"
    ], (EsriMap, MapView, Graphic, Expand, BasemapGallery, LocalBasemapsSource, Basemap) => {

        const view = new MapView({
            container: mapContainerID,
            map: new EsriMap({ basemap: "topo-vector" }),
            zoom: defaultMapCenter.zoom,
            center: [defaultMapCenter.longitude, defaultMapCenter.latitude],
            constraints: { rotationEnabled: false },
            navigation: { browserTouchPanEnabled: false },
            popup: {
                visibleElements: { collapseButton: false },
                dockEnabled: false,
                dockOptions: { buttonEnabled: false },
                viewModel: { includeDefaultActions: false }
            }
        });

        view.ui.add(new Expand({
            view,
            content: new BasemapGallery({
                view,
                source: new LocalBasemapsSource({
                    basemaps: [
                        Basemap.fromId("topo-vector"),
                        Basemap.fromId("hybrid"),
                        Basemap.fromId("streets-vector")
                    ]
                })
            }),
            expandIconClass: "esri-icon-basemap",
            expanded: false
        }), "bottom-left");

        let mouseWheelEvt = view.on("mouse-wheel", stopEvtPropagation); // local болгов

        function stopEvtPropagation(event) {
            event.stopPropagation();
        }

        function enableMouseWheel() {
            if (!mouseWheelEvt) {
                mouseWheelEvt = view.on("mouse-wheel", stopEvtPropagation);
            }
        }

        function disableMouseWheel() {
            if (mouseWheelEvt) {
                mouseWheelEvt.remove();
                mouseWheelEvt = null;
            }
        }

        view.on("drag", ["Shift"], stopEvtPropagation);
        view.on("drag", ["Shift", "Control"], stopEvtPropagation);

        view.on("key-down", (event) => {
            const prohibited = ["+", "-", "Shift", "_", "="];
            if (prohibited.includes(event.key)) event.stopPropagation();
            event.key === "Control" ? disableMouseWheel() : enableMouseWheel();
        });

        view.on("key-up", enableMouseWheel);

        const pointers = new Map();

        view.on("pointer-down", (event) => {
            if (event.pointerType === "touch") {
                pointers.set(event.pointerId, { x: event.x, y: event.y });
            }
        });

        view.on(["pointer-up", "pointer-leave"], (event) => {
            if (event.pointerType === "touch") pointers.delete(event.pointerId);
        });

        view.on("pointer-move", (event) => {
            if (event.pointerType !== "touch" || pointers.size !== 1) return;
            const prev = pointers.get(event.pointerId);
            if (!prev) return;
            if (Math.hypot(event.x - prev.x, event.y - prev.y) < TOUCH_MOVE_THRESHOLD) return;
        });

        function buildPopupContent(e) {
            const data = e.graphic.attributes;
            const content = $(`<div class="map-popup-info" />`);

            content.html(`
                <img class="img-thumbnail object-fit-cover rounded-1 mb-2 p-0" src="${data.ImageMD}" style="width: 100%; height: 160px;">
                <p>${data.Address || ''}</p>
            `);

            return content.get(0);
        }

        function createGraphic(data) {
            return new Graphic({
                geometry: {
                    type: "point",
                    longitude: data.Longitude,
                    latitude: data.Latitude
                },
                symbol: {
                    type: "simple-marker",
                    style: "path",
                    path: svgPin,
                    color: LOCAL_VARIABLES.StaticText.WaterLevelTypes[data.WaterLevelType].color,
                    outline: { color: "#ffffff", width: 2 },
                    size: ICON_SIZE,
                    xoffset: 0,
                    yoffset: ICON_SIZE / 2
                },
                attributes: data,
                popupTemplate: {
                    title: `<i class="bi bi-circle-fill info-color info-color-${data.WaterLevelType}"></i> ${data.SiteName} (${data.SiteCode})`,
                    content: buildPopupContent
                }
            });
        }

        function animateWaterLevelInfo(waterLevelInfo) {
            waterLevelInfo.forEach((count, i) => {
                $({ Counter: 0 }).animate({ Counter: count }, {
                    duration: 500,
                    easing: "swing",
                    step: function () {
                        $("#WaterLevelInfo .col").eq(i).find("h6").text(`(${Math.round(this.Counter)})`);
                    },
                    complete: function () {
                        $("#WaterLevelInfo .col").eq(i).find("h6").text(`(${count})`);
                    }
                });
            });
        }

        function siteDataUpdate(initLocation = true) {
            const postData = { filters: {} };
            const projectID = $("#ProjectIDFilter").val();
            const riverBasinID = $("#RiverBasinIDFilter").val();
            const region = $("#RegionFilter").val();

            if (projectID) postData.filters.ProjectID = projectID;
            if (riverBasinID) postData.filters.RiverBasinID = riverBasinID;
            if (region) postData.filters.Region = region;

            $.ajax({
                url: "/api/stations/sites",
                type: "POST",
                data: JSON.stringify(postData),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                beforeSend: () => {
                    mapContainer.find(".map-loader").removeClass("d-none");
                    lockFormInputs(mapContainer.find(".stations-filters"), true);
                },
                complete: () => {
                    mapContainer.find(".map-loader").addClass("d-none");
                    lockFormInputs(mapContainer.find(".stations-filters"), false);
                },
                success: (jsonData) => {
                    view.closePopup();
                    view.graphics.removeAll();

                    const graphicsArray = [];
                    const waterLevelInfo = [0, 0, 0, 0];
                    let sumLat = 0, sumLon = 0, counter = 0;

                    (jsonData.data || []).forEach((data) => {
                        sumLat += parseFloat(data.Latitude) || 0;
                        sumLon += parseFloat(data.Longitude) || 0;
                        counter++;
                        waterLevelInfo[data.WaterLevelType]++;
                        graphicsArray.push(createGraphic(data));
                    });

                    if (graphicsArray.length > 0) {
                        view.graphics.addMany(graphicsArray);

                        if (initLocation && counter > 0) {
                            const hasBasin = "RiverBasinID" in postData.filters;
                            const isHybrid = view.map.basemap.id === "hybrid";
                            view.goTo({
                                zoom: hasBasin ? (isHybrid ? 8 : 7) : 6,
                                center: [sumLon / counter, sumLat / counter]
                            }).catch((err) => {
                                if (err.name !== "AbortError") console.error(err);
                            });
                        }
                    }

                    animateWaterLevelInfo(waterLevelInfo);
                },
                error: (jqXHR) => {
                    const res = jqXHR.responseJSON;
                    if (res) {
                        toastr.error(res.Message, res.Title);
                    } else if (jqXHR.responseText) {
                        toastr.error(jqXHR.responseText);
                    } else {
                        toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoInternetConnection);
                    }
                }
            });
        }

        view.when(() => {
            if (reloadInterval) clearInterval(reloadInterval);
            reloadInterval = setInterval(() => siteDataUpdate(false), RELOAD_TIME_INTERVAL);
            siteDataUpdate();
        });

        $("#ProjectIDFilter, #RiverBasinIDFilter, #RegionFilter").on("change", () => siteDataUpdate());
    });
}

if ($(".stations-filters").length > 0) {
    select2Ajax($("#ProjectIDFilter"), "ProjectID", "ProjectName");
    select2Ajax($("#RiverBasinIDFilter"), "RiverBasinID", "WatershedName");
}

function noPermission() {
    toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoPermission);
    $("#module-container").empty();

    setTimeout(function () {
        window.location.href = '/dashboard';
    }, 2500);
}

$(document).on("click", "[data-close-dropdown]", function (e) {
    const dropdownMenu = $(this).closest('.dropdown-menu');
    const toggleButton = dropdownMenu.get(0).parentElement.querySelector('[data-bs-toggle="dropdown"]');

    if (toggleButton) {
        const bsDropdown = bootstrap.Dropdown.getOrCreateInstance(toggleButton);
        bsDropdown.hide();
    }
});