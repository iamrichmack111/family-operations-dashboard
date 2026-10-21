(() => {
  "use strict";

  const STORAGE_KEY = "familyFocusMode";
  const VIEW_KEY = "familyFocusView";

  const focused = () =>
    localStorage.getItem(STORAGE_KEY) === "1";

  function sections() {
    return Array.from(
      document.querySelectorAll(
        "main .content-limit > section, main .content-limit > .row"
      )
    ).filter(el =>
      !el.classList.contains("dashboard-hero") &&
      !el.classList.contains("fruit-focus-controls")
    );
  }

  function setView(view) {
    localStorage.setItem(VIEW_KEY, view);

    document.querySelectorAll("[data-focus-view]").forEach(btn => {
      btn.classList.toggle(
        "active",
        btn.dataset.focusView === view
      );
    });

    sections().forEach(section => {
      const heading = (
        section.querySelector("h2,h3,.panel-heading")?.textContent || ""
      ).toLowerCase();

      let show = true;

      if (focused() && view === "tasks") {
        show = /task|chore|homework|assignment|schedule|today/i
          .test(heading);
      }

      if (focused() && view === "reviews") {
        show = /approval|review|pending|homework/i
          .test(heading);
      }

      section.dataset.focusHidden = show ? "false" : "true";
    });
  }

  function setFocus(enabled) {
    localStorage.setItem(STORAGE_KEY, enabled ? "1" : "0");

    document.body.classList.toggle("focus-mode", enabled);

    const button = document.getElementById("focusModeBtn");

    if (button) {
      button.textContent = enabled
        ? "✨ Exit Focus Mode"
        : "🎯 Focus Mode";
    }

    const controls = document.querySelector(".fruit-focus-controls");

    if (controls) {
      controls.hidden = !enabled;
    }

    if (document.body.classList.contains("dashboard-page")) {
      setView(localStorage.getItem(VIEW_KEY) || "tasks");
    }
  }

  function init() {
    if (!document.getElementById("focusModeBtn")) return;

    document.body.classList.add("dashboard-page");

    const oldButton = document.getElementById("focusModeBtn");

    // Replace the button to remove the old Focus Mode handler.
    const button = oldButton.cloneNode(true);
    oldButton.replaceWith(button);

    const controls = document.createElement("div");
    controls.className = "fruit-focus-controls";
    controls.innerHTML = `
      <button type="button" data-focus-view="tasks">✅ Tasks First</button>
      <button type="button" data-focus-view="reviews">📋 Reviews</button>
      <button type="button" data-focus-view="all">🌈 Full Overview</button>
    `;

    const hero = document.querySelector(".dashboard-hero");

    if (hero) hero.insertAdjacentElement("afterend", controls);

    button.addEventListener("click", () => {
      setFocus(!focused());
    });

    controls.querySelectorAll("[data-focus-view]").forEach(btn => {
      btn.addEventListener("click", () => {
        setView(btn.dataset.focusView);
      });
    });

    setFocus(focused());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
