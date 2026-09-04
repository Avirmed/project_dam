// Header notifications (templates/main/notification.html): the newest pending
// security events in the user's scope, from POST /api/eventlog/latest, refreshed
// every REFRESH_MS. Loaded on every page that renders the header (front + dashboard).
(function () {
    const REFRESH_MS = 60 * 1000;
    const box = $(".notification_item");
    if (!box.length || !LOCAL_VARIABLES.Authorization) {
        return;
    }
    const T = ((LOCAL_VARIABLES.StaticText || {}).FrontPage || {}).Notifications || {};
    const esc = (s) => $("<div>").text(s == null ? "" : String(s)).html();

    function load() {
        $.ajax({
            url: "/api/eventlog/latest",
            type: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify({}),
        }).done(function (res) {
            const pending = Number(res.pending || 0);
            const list = box.find(".notification-list").empty();
            // counter pill replaces the theme dot while something is pending
            box.find(".notification-status-dot").addClass("d-none");
            box.find(".notification-count").toggleClass("d-none", pending === 0).text(pending > 99 ? "99+" : pending);
            box.find(".notification-summary").text(pending ? `${pending} ${T.Pending || ""}` : "");
            box.find(".notification-empty").toggleClass("d-none", pending > 0);
            (res.data || []).forEach(function (ev) {
                list.append(`
                    <a class="noti-item" href="/events/${ev.ID}">
                        <img class="noti-thumb" src="${esc(ev.Image)}" alt="" onerror="this.onerror=null;this.src='${esc(LOCAL_VARIABLES.StaticText.Images.Blank)}'">
                        <div class="noti-body">
                            <div class="noti-row">
                                <span class="noti-title">${esc(ev.Event || "")}</span>
                                <span class="noti-time">${ev.EventTime ? moment(ev.EventTime).format("DD/MM HH:mm") : ""}</span>
                            </div>
                            <div class="noti-sub" title="${esc(ev.SiteName || "")}">${esc(ev.SiteCode || "")} · ${esc(ev.SiteName || "")}${ev.CameraName ? ` · ${esc(ev.CameraName)}` : ""}</div>
                        </div>
                    </a>`);
            });
        });
    }

    load();
    setInterval(load, REFRESH_MS);
})();
