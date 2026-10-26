(() => {
  NuxivaDesk.register("active_tasks", {
    render(el, d, ctx) {
      const tasks = (Array.isArray(d.tasks) ? d.tasks : []).slice(0, 10);
      const rows = tasks.map((t, i) => `<div class="wk-task${i === 0 ? " on" : ""}">${ctx.esc(t)}</div>`).join("");
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label"), chip: tasks.length ? ctx.count("active", tasks.length) : "", live: tasks.length > 0 })}
        ${rows || ctx.empty(ctx.t("idle"))}`;
    },
  });
})();
