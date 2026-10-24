/* Search the native selectors; canonical identities are also resolved on the server. */
"use strict";
document.querySelectorAll("[data-player-picker]").forEach((picker) => {
    const search = picker.querySelector("[data-player-search]");
    const select = picker.querySelector("[data-player-select]");
    search.addEventListener("input", () => {
        const query = search.value.trim().toLocaleLowerCase();
        Array.from(select.options).forEach((option) => {
            option.hidden = Boolean(option.value && !option.selected &&
                !option.textContent.toLocaleLowerCase().includes(query));
        });
    });
    select.addEventListener("change", () => {
        const option = select.selectedOptions[0];
        if (option.value === "saved") return;
        const row = picker.closest("tr");
        ["name", "team", "position"].forEach((field) => {
            row.querySelector(`[data-player-field="${field}"]`).value = option.dataset[field] || "";
        });
        row.querySelector("[data-player-team]").textContent = option.dataset.team || "";
        row.querySelector("[data-player-position]").textContent = option.dataset.position || "—";
        row.querySelectorAll('input[type="number"]').forEach((input) => { input.value = ""; });
        row.querySelector('select[name$="_state"]').value = "not_started";
        picker.closest("form").querySelectorAll('.matchup-scoreboard input[name$="_actual"]')
            .forEach((input) => { input.value = ""; });
        search.value = "";
        Array.from(select.options).forEach((item) => { item.hidden = false; });
    });
});
