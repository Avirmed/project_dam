let pagePermission = [1];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}

let tableSystemSettings = new Tabulator("#tableSystemSettings", {
    columnDefaults: {
        resizable: false
    },
    initialSort: [
        { column: "field", dir: "desc" }
    ],
    columns: [
        { title: LOCAL_VARIABLES.StaticText.Field, field: "field", sorter: "string" },
        {
            title: LOCAL_VARIABLES.StaticText.Value,
            field: "value",
            editable: function (cell) {
                let fieldName = cell.getData().field || "";
                return !fieldName.includes("COLOR");
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