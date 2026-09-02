let pagePermission = [1];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}

// Settings stored as "1" / "0" and shown as a switch (statictext.BooleanSettings,
// plus the *_ENABLED naming convention so a stale StaticText cache still works).
function isBooleanSetting(fieldName) {
    let names = LOCAL_VARIABLES.StaticText.BooleanSettings || [];
    return names.includes(fieldName) || fieldName.endsWith("_ENABLED");
}

let tableSystemSettings = new Tabulator("#tableSystemSettings", {
    columnDefaults: {
        resizable: false
    },
    initialSort: [
        { column: "field", dir: "desc" }
    ],
    columns: [
        { title: LOCAL_VARIABLES.StaticText.Field, field: "field", sorter: "string", headerSortStartingDir: "asc" },
        {
            title: LOCAL_VARIABLES.StaticText.Value,
            field: "value",
            editable: function (cell) {
                let fieldName = cell.getData().field || "";
                return !fieldName.includes("COLOR") && !isBooleanSetting(fieldName);
            },
            formatter: function (cell) {
                let fieldName = cell.getData().field || "";
                if (fieldName.includes("COLOR")) {
                    return `
                        <div class="d-flex align-items-center">
                            <input type="color" class="form-control form-control-color form-control-color-input me-2" value="${cell.getValue()}">
                            <small class="text-muted">${cell.getValue()}</small>
                        </div>
                    `;
                }
                if (isBooleanSetting(fieldName)) {
                    let on = !["0", "false", "off", "no", ""].includes(String(cell.getValue() || "").trim().toLowerCase());
                    return `
                        <div class="form-check form-switch">
                            <label class="form-check-label">
                                <input type="checkbox" class="form-check-input form-control-switch-input" ${on ? "checked" : ""}>
                                <small>${on ? LOCAL_VARIABLES.StaticText.Yes : LOCAL_VARIABLES.StaticText.No}</small>
                            </label>
                        </div>
                    `;
                }
                return cell.getValue();
            }
        }
    ]
});

$(document).on("change", ".form-control-color-input", function (e) {
    let newValue = $(this).val();
    let cell = tableSystemSettings.getRow(this.closest(".tabulator-row")).getCell("value");
    cell.setValue(newValue);
});

// Switch -> "1" / "0"; setValue fires cellEdited, which saves the row.
$(document).on("change", ".form-control-switch-input", function (e) {
    let newValue = this.checked ? "1" : "0";
    let cell = tableSystemSettings.getRow(this.closest(".tabulator-row")).getCell("value");
    cell.setValue(newValue);
});

tableSystemSettings.isReverting = false;

tableSystemSettings.on("cellEdited", function (cell) {
    if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
        return;
    }

    if (tableSystemSettings.isReverting) return;

    let oldValue = cell.getOldValue();
    let rowData = cell.getData();
    let data = { 'Name': rowData.field.trim(), 'Value': rowData.value.trim() };

    $.post(`/dashboard/settings/save`, data, function (jsonData) {
        if (jsonData.Result) {
            toastr.success(jsonData.Message, jsonData.Title);
            cell.edit(true);

            LOCAL_VARIABLES.StaticText.APP_SETTINGS[data.Name] = data.Value;
            setLocalStorage();
        } else {
            toastr.error(jsonData.Message, jsonData.Title);

            tableSystemSettings.isReverting = true;
            cell.setValue(oldValue);
            tableSystemSettings.isReverting = false;
        }
        cell.cancelEdit();
    }, "json").fail(function (jqXHR) {
        if (jqXHR.responseJSON) {
            toastr.error(jqXHR.responseJSON.Message, jqXHR.responseJSON.Title);
        } else if (jqXHR.responseText) {
            toastr.error(jqXHR.responseText);
        } else {
            toastr.error(LOCAL_VARIABLES.StaticText.Messages.NoInternetConnection);
        }

        tableSystemSettings.isReverting = true;
        cell.setValue(oldValue);
        tableSystemSettings.isReverting = false;
        cell.cancelEdit();
    });
});