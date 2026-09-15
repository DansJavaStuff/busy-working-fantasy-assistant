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

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(
            ".yahoo-refresh-form, .js-busy-form"
        ).forEach(function (form) {
            form.addEventListener("submit", function () {
                showBusyOverlay(form);
            });
        });
    });

    window.addEventListener("pageshow", hideBusyOverlay);
})();
