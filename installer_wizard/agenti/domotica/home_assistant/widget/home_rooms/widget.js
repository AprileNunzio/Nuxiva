(() => {
  const ICONS = [
    [/cucin|kitchen|cocina|cuisine/i, "fire"], [/bagn|bath|toilet|wc|baño|bano|salle de bain|douche/i, "drop"],
    [/letto|camera|bed|dormitorio|habitaci|chambre/i, "moon"], [/soggiorn|salott|living|lounge|salón|salon|séjour|sejour/i, "home"],
    [/studio|ufficio|office|estudio|bureau|despacho/i, "code"], [/garage|box|garaje/i, "car"], [/giardin|terrazz|balcon|garden|patio|jardín|jardin|terrasse/i, "sun"],
    [/ingress|corridoi|hall|entr|pasillo|couloir|recibidor/i, "door"], [/cantin|cellar|bodega|cave|sótano|sotano/i, "server"],
  ];
  const iconOf = (name) => (ICONS.find(([re]) => re.test(name)) || [null, "door"])[1];

  function rooms(d, ctx) {
    return ctx.arr(d.rooms, 12).map((r) => {
      if (typeof r === "string" || typeof r === "number") return { name: ctx.str(r, 40), people: [], since: null };
      if (!r || typeof r !== "object") return null;
      const people = ctx.arr(r.people, 6).map((p) => ctx.str(typeof p === "object" && p ? p.name : p, 24)).filter(Boolean);
      return { name: ctx.pick(r, ["name", "room", "area"], 40), people, since: ctx.stamp(r.since ?? r.at) };
    }).filter((r) => r && r.name);
  }

  NuxivaDesk.register("home_rooms", {
    render(el, d, ctx) {
      const list = rooms(d && typeof d === "object" ? d : {}, ctx);
      const head = ctx.head({ icon: "home", label: ctx.t("label"), chip: list.length ? ctx.count("occupied", list.length) : "", live: list.length > 0 });
      if (!list.length) { el.innerHTML = `${head}${ctx.empty(ctx.t("none"))}`; return; }
      el.innerHTML = `${head}<ul class="hr-grid">${list.map((r, i) => {
        const sub = [r.people.join(", "), r.since && r.since <= ctx.now() ? ctx.ago(r.since) : ""].filter(Boolean).join(" · ");
        return `<li class="hr-room" style="--i:${i}" title="${ctx.esc(r.name)}"><span class="hr-ic">${ctx.icon(iconOf(r.name))}<i class="hr-dot" aria-hidden="true"></i></span>
          <span class="hr-txt"><b>${ctx.esc(r.name)}</b>${sub ? `<small>${ctx.esc(sub)}</small>` : ""}</span></li>`;
      }).join("")}</ul>`;
    },
  });
})();
