// Public CCTV page (front design slides 4-7). One POST /api/stations/cameras
// (stations in scope + their cameras + latest snapshot), refreshed every
// REFRESH_MS; the list is filtered client-side, the camera type server-side.
(function () {
    const REFRESH_MS = 60 * 1000;
    const ST = LOCAL_VARIABLES.StaticText;
    const T = (ST.FrontPage || {}).CCTV || {};
    const page = $(".cctv-page");
    if (!page.length) {
        return;
    }

    let stations = [];
    let selectedId = Number(page.data("station")) || null;

    const esc = (s) => $("<div>").text(s == null ? "" : String(s)).html();
    const when = (v) => (v ? moment(v).format("DD/MM/YYYY HH:mm") : "-");
    const typeOf = (row) => (ST.WaterLevelTypes || {})[row.WaterLevelType] || {};

    function load(initial) {
        $.ajax({
            url: "/api/stations/cameras",
            type: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify({ filters: { CameraType: page.find(".cctv-type").val() || "" } }),
        }).done(function (res) {
            stations = res.data || [];
            renderList();
            if (selectedId && stations.some((s) => s.StationID === selectedId)) {
                renderDetail(selectedId);
            } else if (initial && stations.length && !selectedId) {
                // nothing chosen yet: show the first station so the page is not empty
                selectedId = stations[0].StationID;
                renderDetail(selectedId);
            }
        }).fail(ajaxFailToast);
    }

    function renderList() {
        const list = page.find(".cctv-list").empty();
        const q = (page.find(".cctv-search").val() || "").trim().toLowerCase();
        let basin = null;
        let shown = 0;
        stations.forEach(function (s) {
            const text = `${s.SiteCode} ${s.SiteName} ${s.WatershedName || ""}`.toLowerCase();
            if (q && text.indexOf(q) === -1) {
                return;
            }
            if (s.WatershedName !== basin) {
                basin = s.WatershedName;
                list.append(`<div class="small fw-semibold text-muted mt-2 mb-1 cctv-basin">${esc(basin || "-")}</div>`);
            }
            const type = typeOf(s);
            list.append(`
                <a href="javascript:;" class="list-group-item list-group-item-action px-2 py-2 cctv-item ${s.StationID === selectedId ? "active" : ""}" data-id="${s.StationID}">
                    <div class="d-flex align-items-center gap-2">
                        <span class="status-dot flex-shrink-0" style="background:${type.color || "#7f7f7f"}"></span>
                        <div class="flex-fill min-w-0">
                            <div class="fw-semibold text-truncate">${esc(s.SiteCode)} - ${esc(s.SiteName)}</div>
                            <div class="small text-muted d-flex justify-content-between">
                                <span>${when(s.SnapshotTime || s.RecordTime)}</span>
                                <span>${s.Cameras.length} ${esc(T.Cameras)}</span>
                            </div>
                        </div>
                    </div>
                </a>`);
            shown++;
        });
        page.find(".cctv-count").text(`(${shown})`);
    }

    function renderDetail(id) {
        const s = stations.find((x) => x.StationID === id);
        if (!s) {
            page.find(".cctv-detail").addClass("d-none");
            page.find(".cctv-empty").removeClass("d-none");
            return;
        }
        const type = typeOf(s);
        page.find(".cctv-empty").addClass("d-none");
        page.find(".cctv-detail").removeClass("d-none");
        page.find(".cctv-title").text(`${s.SiteCode} - ${s.SiteName}`);
        page.find(".cctv-status").css("background", type.color || "#7f7f7f");
        page.find(".cctv-subtitle").text(`${s.WatershedName || ""} · ${when(s.SnapshotTime || s.RecordTime)}`);
        page.find(".cctv-station-link").attr("href", `/station/${s.StationID}`);
        page.find(".cctv-item").removeClass("active").filter(`[data-id='${id}']`).addClass("active");

        const grid = page.find(".cctv-cameras").empty();
        page.find(".cctv-nocameras").toggleClass("d-none", s.Cameras.length > 0);
        s.Cameras.forEach(function (cam) {
            const hasSnap = !!cam.SnapshotTime;
            grid.append(`
                <div class="col-md-6 col-xxl-4">
                    <div class="border rounded-2 h-100 cctv-card">
                        <div class="cctv-image bg-light rounded-top ${hasSnap ? "cctv-zoom" : ""}" data-image="${esc(cam.SnapshotImage)}" data-title="${esc(cam.CameraName)}" data-time="${hasSnap ? when(cam.SnapshotTime) : ""}" title="${hasSnap ? esc(T.Enlarge) : ""}">
                            <img src="${esc(cam.SnapshotImage)}" alt="" loading="lazy">
                            <span class="badge text-bg-dark cctv-type-badge">${esc(cam.CameraTypeText || "")}${cam.CCTV_NO ? " #" + esc(cam.CCTV_NO) : ""}</span>
                        </div>
                        <div class="p-2 d-flex align-items-center justify-content-between gap-2">
                            <div class="min-w-0">
                                <div class="fw-semibold text-truncate">${esc(cam.CameraName)}</div>
                                <small class="text-muted">${hasSnap ? `${esc(T.TakenAt)}: ${when(cam.SnapshotTime)}` : esc(T.NoSnapshot)}</small>
                            </div>
                        </div>
                    </div>
                </div>`);
        });
    }

    // Lightbox: the animation (newest snapshots) full size in a modal.
    page.on("click", ".cctv-zoom", function () {
        const box = $(this);
        const modal = page.find(".cctv-lightbox");
        modal.find(".cctv-lightbox-title").text(box.data("title"));
        modal.find(".cctv-lightbox-time").text(box.data("time") ? `${T.TakenAt}: ${box.data("time")}` : "");
        modal.find(".cctv-lightbox-img").attr("src", box.data("image"));
        modal.modal("show");
    });
    page.find(".cctv-lightbox").on("hidden.bs.modal", function () {
        $(this).find(".cctv-lightbox-img").attr("src", "");  // stop the animation when closed
    });

    page.on("click", ".cctv-item", function () {
        selectedId = Number($(this).data("id"));
        renderDetail(selectedId);
        window.history.replaceState("", "", `/cctv/${selectedId}`);
    });
    page.on("input", ".cctv-search", renderList);
    page.on("change", ".cctv-type", () => load(false));
    page.on("click", ".cctv-print", () => window.print());

    load(true);
    setInterval(() => load(false), REFRESH_MS);
})();
