if (typeof Tabulator !== 'undefined' && Tabulator.defaultOptions && !Tabulator.defaultOptions.langs) {
    Tabulator.defaultOptions.langs = {};
}

Tabulator.defaultOptions.langs["mn"] = {
	pagination: {
        page_size: "Хуудсанд",
        page_title: "Хуудас",
        first: "&laquo;",
        first_title: "Эхний хуудас",
        last: "&raquo;",
        last_title: "Сүүлийн хуудас",
        prev: "&lsaquo;",
        prev_title: "Өмнөх хуудас",
        next: "&rsaquo;",
        next_title: "Дараагийн хуудас",
        all: "Бүгд",
        counter: {
            showing: "Дэлгэцэнд",
            of: "дээр",
            rows: "мөрүүд",
            pages: "хуудас",
        }
    },
    headerFilters: {
        default: "Шүүлтүүрийг оруулах...",
    },
    noData: "Мэдээлэл олдсонгүй.",
    loading: "Татаж байна...",
    columns: {
        freeze: "Мөрийг хөлдөөнө",
    },
    filters: {
        apply: "Шүүлтүүрийг хэрэглэх",
        clear: "Цэвэрлэх",
    },
    sorter: {
        ascending: "Өсөх",
        descending: "Буурах",
    },
    group: {
        group: "Бүлэглэх",
        remove: "Бүлгийг устгах",
    },
    clipboard: {
        copy: "Хуулах",
        paste: "Буулгах",
    },
    download: {
        download: "Татаж авах",
    },
    print: {
        print: "Хэвлэх",
    },
    edit: {
        edit: "Засварлах",
        save: "Хадгалах",
        cancel: "Цуцлах",
    },
    rowMenu: {
        edit: "Засварлах",
        delete: "Устгах",
    },
    data: {
        error: "Алдаа гарлаа",
        loading: "Ачаалж байна...",
    },
    validation: {
        invalid: "Буруу утга",
        required: "Энэ талбар шаардлагатай",
    }
};