(() => {
  NuxivaDesk.register("clipboard_sync", {
    render(el, d, ctx) {
      const text = ctx.plain(d.content, 4000).trim();
      el.innerHTML = `${ctx.head({ icon: "clipboard", label: ctx.t("label"), chip: text ? ctx.count("chars", text.length) : "" })}
        ${text ? `<pre class="wk-pre">${ctx.esc(text)}</pre>` : ctx.empty(ctx.t("empty"))}`;
    },
  });
})();
