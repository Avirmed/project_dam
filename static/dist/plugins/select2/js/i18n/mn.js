!(function () {
    if (jQuery && jQuery.fn && jQuery.fn.select2 && jQuery.fn.select2.amd) var n = jQuery.fn.select2.amd;
    n.define("select2/i18n/mn", [], function () {
        function n(n, e, r, u) {
            return (n % 10 < 5 && n % 10 > 0 && n % 100 < 5) || n % 100 > 20 ? (n % 10 > 1 ? r : e) : u;
        }
        return {
            errorLoading: function () {
                return "Үр дүнг ачаалж чадсангүй.";
            },
            inputTooLong: function (e) {
                var r = e.input.length - e.maximum,
                    u = r + " тэмдэгтийг устгана уу.";
                return u;
            },
            inputTooShort: function (e) {
                var r = e.minimum - e.input.length,
                    u = "Дор хаяж " + r + " тэмдэгт оруулна уу.";
                return u;
            },
            loadingMore: function () {
                return "Илүү өгөгдөл ачаалж байна....";
            },
            maximumSelected: function (e) {
                var r = "Та зөвхөн " + e.maximum + " сонголт хийж болно.";
                return r;
            },
            noResults: function () {
                return "Тохирох өгөгдөл олдсонгүй.";
            },
            searching: function () {
                return "Хайж байна....";
            },
            removeAllItems: function () {
                return "Бүгдийг арилгах.";
            },
            removeItem: function () {
                return "Элементийг устгах.";
            },
            search: function () {
                return "Хайх...";
            },
        };
    }),
        n.define,
        n.require;
})();