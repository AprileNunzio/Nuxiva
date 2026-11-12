(() => {
  const ROLES = new Set(["agent", "work", "visual"]);
  const st = { sig: "", list: null, roles: [] };

  const valid = (s) => s && Number.isInteger(s.n) && s.n >= 0 && s.n <= 16;
  const roleOf = (roles, n) => {
    const r = roles && typeof roles === "object" ? roles[n] ?? roles[String(n)] : "";
    return ROLES.has(r) ? r : "";
  };

  function render(screens, roles, current) {
    const list = (Array.isArray(screens) ? screens : []).filter(valid).slice(0, 17);
    const sig = JSON.stringify([list.map((s) => s.n), roles || {}, current]);
    if (sig === st.sig) return;
    st.sig = sig;
    const mine = roleOf(roles, current);
    document.body.dataset.screenRole = mine || "agent";
    st.roles.forEach((el) => (mine ? PageText.bind(el, `role_${mine}`) : PageText.plain(el, "")));
    st.list.hidden = list.length < 2;
    st.list.replaceChildren(...list.map((s) => {
      const li = document.createElement("li");
      const role = roleOf(roles, s.n) || "agent";
      li.className = `sm-dot role-${role}${s.n === current ? " on" : ""}`;
      if (s.n === current) li.setAttribute("aria-current", "true");
      PageText.attr(li, { title: `role_${role}` });
      return li;
    }));
  }

  function mount(list, roleEls) {
    st.list = list;
    st.roles = roleEls.filter(Boolean);
  }

  window.NuxivaScreenMap = Object.freeze({ mount, render });
})();
