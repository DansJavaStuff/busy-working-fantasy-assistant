// Keep desktop comparisons out of the card grid's row sizing. Mobile and
// browsers without dialog support retain the native inline details control.
document.addEventListener("click", function (event) {
    const summary = event.target.closest(".stream-comparison > summary");
    if (!summary || !window.matchMedia("(min-width: 701px)").matches) return;
    if (typeof HTMLDialogElement === "undefined") return;
    const body = summary.parentElement.querySelector(".stream-comparison-body");
    if (!body) return;
    event.preventDefault();

    const dialog = document.createElement("dialog");
    dialog.className = "stream-comparison-dialog";
    dialog.setAttribute("aria-labelledby", "stream-comparison-heading");
    const header = document.createElement("header");
    const heading = document.createElement("h2");
    heading.id = "stream-comparison-heading";
    heading.textContent = summary.textContent;
    const close = document.createElement("button");
    close.type = "button";
    close.className = "secondary-button";
    close.textContent = "Close";
    close.addEventListener("click", function () { dialog.close(); });
    header.append(heading, close);
    dialog.append(header, body.cloneNode(true));
    dialog.addEventListener("close", function () {
        dialog.remove();
        summary.focus();
    });
    document.body.append(dialog);
    dialog.showModal();
    close.focus();
});
