(function (factory) {
    if (typeof define === "function" && define.amd) {
        define(["jquery", "../jquery.validate"], factory);
    } else if (typeof module === "object" && module.exports) {
        module.exports = factory(require("jquery"));
    } else {
        factory(jQuery);
    }
}(function ($) {

    /*
     * Translated default messages for the jQuery validation plugin.
     * Locale: MN (Mongolian; Монгол хэл)
     */
    $.extend($.validator.messages, {
        required: "Өгөгдөл оруулна уу.",
        remote: "Тохирох утга оруулна уу.",
        email: "И-мэйлийн формат буруу байна.",
        url: "Холбоосын формат буруу байна.",
        date: "Огноо буруу оруулсан байна.",
        dateISO: "ISO форматтай огноо оруулна уу.",
        number: "Зөвхөн тоо оруулна уу.",
        digits: "Тоон тэмдэгт оруулна уу.",
        creditcard: "Картын дугаарыг зөв оруулна уу.",
        equalTo: "Баталгаажуулалт буруу оруулсан байна.",
        extension: "Зөв өргөтгөлтэй файлыг сонгоно уу.",
        maxlength: $.validator.format("{0}-с бага тэмдэгт байна."),
        minlength: $.validator.format("{0}-с их тэмдэгт байна."),
        rangelength: $.validator.format("{0}-с {1}-н хооронд тэмдэгт оруулна уу."),
        max: $.validator.format("Хамгийн ихдээ {0}-с ихгүй оруулна уу."),
        min: $.validator.format("Хамгийн багадаа {0}-с багагүй оруулна уу.")
    });
    return $;
}));