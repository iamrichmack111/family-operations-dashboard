
(() => {
  const icons = {
    "Dashboard":"⌂","Planner":"▦","Household HQ":"◇","Approvals":"✓","Reports":"▥",
    "Messages":"✉","Grievances":"⚑","Violations":"!","Family News":"◫","Points":"★",
    "Alerts":"•","Parent Center":"⌘","Exports":"⇩","Point Requests":"＋"
  };

  function pathMatch(link) {
    try {
      const u = new URL(link.href, location.origin);
      const p = location.pathname;
      if (u.pathname === "/") return p === "/";
      return p === u.pathname || p.startsWith(u.pathname + "/");
    } catch (_) { return false; }
  }

  function polishNav() {
    const links = [...document.querySelectorAll(".navbar .nav-link")];
    links.forEach(link => {
      const label = link.textContent.trim().replace(/\s+/g, " ");
      if (pathMatch(link)) link.classList.add("v66-active");
      if (!link.dataset.v66Icon && icons[label]) {
        link.dataset.v66Icon = "1";
        link.innerHTML = `<span style="width:22px;display:inline-grid;place-items:center;margin-right:7px;opacity:.9">${icons[label]}</span><span>${label}</span>`;
      }
    });
  }

  function mobileDock() {
    if (document.querySelector(".v66-mobile-dock")) return;
    const wanted = [["Dashboard","⌂"],["Household HQ","◇"],["Points","★"],["Grievances","⚑"]];
    const navLinks = [...document.querySelectorAll(".navbar .nav-link")];
    const dock = document.createElement("nav");
    dock.className = "v66-mobile-dock";
    dock.setAttribute("aria-label", "Quick navigation");

    wanted.forEach(([name, icon]) => {
      const source = navLinks.find(a => a.textContent.trim().includes(name));
      if (!source) return;
      const a = document.createElement("a");
      a.href = source.href;
      a.innerHTML = `<span>${icon}</span><small>${name === "Household HQ" ? "Household" : name}</small>`;
      if (pathMatch(a)) a.classList.add("v66-active");
      dock.appendChild(a);
    });

    if (dock.children.length) document.body.appendChild(dock);
  }

  function run() {
    polishNav();
    mobileDock();
  }

  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", run) : run();
})();
