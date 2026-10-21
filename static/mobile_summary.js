document.addEventListener("DOMContentLoaded", function () {
    const button = document.getElementById("mobile-view-toggle");
    if (!button) return;
    const page = button.closest("main");
    const controls = button.closest(".mobile-view-controls");
    page.classList.add("mobile-summary");
    controls.hidden = false;
    button.addEventListener("click", function () {
        const summary = page.classList.toggle("mobile-summary");
        button.setAttribute("aria-pressed", String(!summary));
        button.textContent = summary ? "Show details" : "Show summary";
        controls.querySelector("span").textContent = summary
            ? "Summary view · decisions and key numbers"
            : "Full view · reasoning and comparisons";
    });
});
