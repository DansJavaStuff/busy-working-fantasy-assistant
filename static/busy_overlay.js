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

    function text(cell) {
        return cell ? cell.textContent.trim() : "";
    }

    function number(cell) {
        const value = parseFloat(text(cell));
        return Number.isFinite(value) ? value : 0;
    }

    function weeklySections() {
        return Array.from(
            document.querySelectorAll(".weekly-section")
        );
    }

    function sectionNamed(name) {
        return weeklySections().find(function (section) {
            const heading = section.querySelector("h2");
            return heading && heading.textContent.trim() === name;
        });
    }

    function starterPosition(slotText) {
        const flex = slotText.match(/FLEX\s*\(([^)]+)\)/i);

        if (flex) {
            return flex[1].trim().toUpperCase();
        }

        return slotText.split(/\s+/)[0].toUpperCase();
    }

    function slotAccepts(slot, position) {
        const upperSlot = slot.toUpperCase();
        const upperPosition = position.toUpperCase();

        if (upperSlot.indexOf("FLEX") === 0) {
            return ["RB", "WR", "TE"].includes(upperPosition);
        }

        if (upperSlot === "DST" || upperSlot === "DEF") {
            return upperPosition === "DST" || upperPosition === "DEF";
        }

        return upperSlot === upperPosition;
    }

    function buildCloseStartSitDecisions() {
        const lineupSection = sectionNamed("Recommended Lineup");
        const benchSection = sectionNamed("Bench");

        if (!lineupSection || !benchSection) {
            return;
        }

        const starterRows = Array.from(
            lineupSection.querySelectorAll("tbody tr")
        ).map(function (row) {
            const cells = row.querySelectorAll("td");
            const slot = text(cells[0]);

            return {
                slot: slot,
                position: starterPosition(slot),
                name: text(cells[1]),
                projection: number(cells[4]),
                actual: text(cells[5]),
                status: text(cells[6])
            };
        }).filter(function (player) {
            return player.actual === "—" || player.actual === "";
        });

        const benchRows = Array.from(
            benchSection.querySelectorAll("tbody tr")
        ).map(function (row) {
            const cells = row.querySelectorAll("td");

            return {
                name: text(cells[0]),
                position: text(cells[1]).toUpperCase(),
                projection: number(cells[4]),
                actual: text(cells[5]),
                status: text(cells[6])
            };
        }).filter(function (player) {
            return player.actual === "—" || player.actual === "";
        });

        const decisions = [];

        benchRows.forEach(function (benchPlayer) {
            const eligibleStarters = starterRows.filter(function (starter) {
                return slotAccepts(starter.slot, benchPlayer.position);
            });

            if (!eligibleStarters.length) {
                return;
            }

            eligibleStarters.sort(function (left, right) {
                return left.projection - right.projection;
            });

            const starter = eligibleStarters[0];
            const edge = starter.projection - benchPlayer.projection;

            if (edge > 3.0) {
                return;
            }

            let label;
            let explanation;

            if (edge < -0.05) {
                label = "REVIEW";
                explanation =
                    benchPlayer.name
                    + " projects "
                    + Math.abs(edge).toFixed(2)
                    + " points higher. Check status or lineup-lock constraints.";
            } else if (edge <= 0.5) {
                label = "TOSS-UP";
                explanation =
                    "Only "
                    + Math.max(edge, 0).toFixed(2)
                    + " projected points separate them.";
            } else if (edge <= 1.5) {
                label = "CLOSE";
                explanation =
                    starter.name
                    + " has a small "
                    + edge.toFixed(2)
                    + " point projected edge.";
            } else {
                label = "LEAN START";
                explanation =
                    starter.name
                    + " leads by "
                    + edge.toFixed(2)
                    + " projected points.";
            }

            if (benchPlayer.status) {
                explanation += " " + benchPlayer.name
                    + " status: " + benchPlayer.status + ".";
            }

            if (starter.status) {
                explanation += " " + starter.name
                    + " status: " + starter.status + ".";
            }

            decisions.push({
                label: label,
                start: starter,
                sit: benchPlayer,
                edge: edge,
                explanation: explanation
            });
        });

        decisions.sort(function (left, right) {
            return left.edge - right.edge;
        });

        const section = document.createElement("section");
        section.className = "weekly-section";

        const heading = document.createElement("h2");
        heading.textContent = "Close Start / Sit Decisions";
        section.appendChild(heading);

        if (!decisions.length) {
            const note = document.createElement("p");
            note.className = "weekly-card-detail";
            note.textContent =
                "No unlocked bench player is within 3 projected points of an eligible starter.";
            section.appendChild(note);
            lineupSection.insertAdjacentElement("afterend", section);
            return;
        }

        const table = document.createElement("table");
        table.className = "weekly-table";
        table.innerHTML =
            "<thead><tr>"
            + "<th>Call</th>"
            + "<th>Start</th>"
            + "<th>Sit</th>"
            + "<th>Edge</th>"
            + "<th>Why</th>"
            + "</tr></thead><tbody></tbody>";

        const body = table.querySelector("tbody");

        decisions.forEach(function (decision) {
            const row = document.createElement("tr");
            const displayEdge = decision.edge >= 0
                ? "+" + decision.edge.toFixed(2)
                : decision.edge.toFixed(2);

            [
                decision.label,
                decision.start.name + " (" + decision.start.slot + ")",
                decision.sit.name + " (" + decision.sit.position + ")",
                displayEdge,
                decision.explanation
            ].forEach(function (value, index) {
                const cell = document.createElement("td");
                cell.textContent = value;

                if (index === 0) {
                    const strong = document.createElement("strong");
                    strong.textContent = value;
                    cell.textContent = "";
                    cell.appendChild(strong);
                }

                row.appendChild(cell);
            });

            body.appendChild(row);
        });

        section.appendChild(table);
        lineupSection.insertAdjacentElement("afterend", section);
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(
            ".yahoo-refresh-form, .js-busy-form"
        ).forEach(function (form) {
            form.addEventListener("submit", function () {
                showBusyOverlay(form);
            });
        });

        buildCloseStartSitDecisions();
    });

    window.addEventListener("pageshow", hideBusyOverlay);
})();
