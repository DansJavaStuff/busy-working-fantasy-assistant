(function () {
    function getOverlay() {
        return document.getElementById("busy-overlay");
    }

    function showBusyOverlay(form) {
        const overlay = getOverlay();

        if (!overlay) {
            return;
        }

        const message = overlay.querySelector(
            "[data-busy-message]"
        );
        const detail = overlay.querySelector(
            "[data-busy-detail]"
        );

        if (message) {
            message.textContent =
                form.dataset.busyMessage
                || "Updating data…";
        }

        if (detail) {
            detail.textContent =
                form.dataset.busyDetail
                || "Refreshing Yahoo data and rebuilding analysis.";
        }

        form.querySelectorAll(
            "button[type='submit'], input[type='submit']"
        ).forEach(function (button) {
            button.disabled = true;
        });

        document.body.classList.add("is-busy");
        overlay.classList.add("is-visible");
        overlay.setAttribute("aria-hidden", "false");
    }

    function hideBusyOverlay() {
        const overlay = getOverlay();

        if (!overlay) {
            return;
        }

        document.body.classList.remove("is-busy");
        overlay.classList.remove("is-visible");
        overlay.setAttribute("aria-hidden", "true");
    }

    function showYahooRefreshResult() {
        const params = new URLSearchParams(
            window.location.search
        );
        const error = params.get("refresh_error");

        if (!error) {
            return;
        }

        const form = document.querySelector(
            ".yahoo-refresh-form"
        );

        if (!form) {
            return;
        }

        const banner = document.createElement("div");
        banner.setAttribute("role", "alert");
        banner.style.margin = "0 0 16px";
        banner.style.padding = "12px 14px";
        banner.style.border = "1px solid #f0b8b8";
        banner.style.borderRadius = "10px";
        banner.style.background = "#fff0f0";
        banner.style.color = "#8a1c1c";
        banner.style.fontWeight = "700";

        if (error === "timeout") {
            banner.textContent =
                "Yahoo refresh timed out before the import finished. "
                + "The previous dataset is still in use. "
                + "Check the busy-working service log for details.";
        } else {
            banner.textContent =
                "Yahoo refresh failed, so the previous dataset is still in use. "
                + "Check the busy-working service log for details.";
        }

        form.insertAdjacentElement(
            "beforebegin",
            banner
        );
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(
            ".yahoo-refresh-form, .js-busy-form"
        ).forEach(function (form) {
            form.addEventListener("submit", function () {
                showBusyOverlay(form);
            });
        });

        showYahooRefreshResult();
    });

    window.addEventListener("pageshow", hideBusyOverlay);
})();
