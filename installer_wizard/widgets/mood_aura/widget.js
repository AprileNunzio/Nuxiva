(() => {
  const MOODS = { felice: "62,255,168", sereno: "61,220,200", entusiasta: "190,255,90", innamorato: "255,110,190", grato: "120,255,190", neutro: "150,170,190",
    stanco: "120,120,255", annoiato: "130,140,160", stressato: "255,181,71", preoccupato: "255,140,70", triste: "70,150,255", arrabbiato: "255,77,106", malato: "179,107,255" };
  const AREAS = { tension: "255,140,70", exhaustion: "120,120,255", receptive: "62,255,168", relief: "61,220,200" };

  NuxivaDesk.register("mood_aura", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const who = data.person && typeof data.person === "object" ? ctx.str(data.person.name, 40) : "";
      const m = data.mood && typeof data.mood === "object" && Object.hasOwn(MOODS, data.mood.mood) ? data.mood : null;
      const f = data.face && typeof data.face === "object" && Object.hasOwn(AREAS, data.face.area) ? data.face : null;
      const head = ctx.head({ icon: "sparkle", label: ctx.t("label"), title: who, chip: f ? ctx.t("face_live") : "", live: !!f });
      if (!m && !f) { el.innerHTML = `${head}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const tone = m ? MOODS[m.mood] : AREAS[f.area];
      const level = m ? Math.max(1, Math.min(5, Math.round(ctx.num(m.intensity) || 1))) : 0;
      const arousal = f ? ctx.pct(ctx.num(f.arousal)) : 0;
      const week = ctx.arr(data.week, 7).map((day) => {
        const mood = day && Object.hasOwn(MOODS, day.mood) ? day.mood : "";
        const lvl = day ? ctx.num(day.level) : null;
        return `<li${mood ? ` style="--c:${MOODS[mood]};--h:${Math.round(((lvl || 1) / 5) * 100)}%"` : ""} title="${ctx.esc(mood ? ctx.t(`m_${mood}`) : "")}"><i aria-hidden="true"></i></li>`;
      }).join("");
      el.innerHTML = `${head}
        <div class="ma-core" style="--c:${tone};--a:${(0.6 + arousal / 100).toFixed(2)}">
          <div class="ma-aura" aria-hidden="true"><i></i><i></i><i></i></div>
          <div class="ma-txt">
            <b>${ctx.esc(m ? ctx.t(`m_${m.mood}`) : ctx.t(`a_${f.area}`))}</b>
            ${m ? `<span class="ma-dots" aria-label="${ctx.esc(ctx.t("intensity", { n: level }))}">${Array.from({ length: 5 }, (_, i) => `<i class="${i < level ? "on" : ""}"></i>`).join("")}</span>` : ""}
            ${f ? `<small>${ctx.esc(ctx.t("face", { area: ctx.t(`a_${f.area}`) }))}</small><span class="ma-bar"><i style="width:${arousal}%"></i></span>` : ""}
          </div>
        </div>
        ${week ? `<ul class="ma-week" aria-label="${ctx.esc(ctx.t("week"))}">${week}</ul>` : ""}`;
    },
  });
})();
