(() => {
  const ID = /^[A-Za-z0-9_-]{1,96}$/;

  const impl = {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const project = ctx.str(d.project_id, 96);
      const session = ctx.str(d.session_id, 96);
      if (!ID.test(project) || !ID.test(session)) {
        impl.destroy(el);
        el.innerHTML = `<div class="rw-state">${ctx.icon("chip")}<b>${ctx.esc(ctx.t("title"))}</b><span>${ctx.esc(ctx.t("missing"))}</span></div>`;
        return;
      }
      const src = `/repair-workbench?project=${encodeURIComponent(project)}&session=${encodeURIComponent(session)}`;
      const live = el._rw;
      if (live && live.src === src && live.frame.isConnected) {
        live.frame.title = ctx.t("title");
        live.label.textContent = ctx.t(live.slow ? "slow" : "loading");
        live.retry.lastChild.textContent = ctx.t("retry");
        return;
      }
      impl.destroy(el);
      const frame = document.createElement("iframe");
      frame.className = "repair-workbench-frame";
      frame.title = ctx.t("title");
      frame.referrerPolicy = "same-origin";
      frame.allow = "fullscreen";
      const veil = document.createElement("div");
      veil.className = "rw-veil";
      veil.setAttribute("role", "status");
      veil.innerHTML = `<span class="rw-spin" aria-hidden="true"></span><span class="rw-label"></span><button type="button" class="wk-btn rw-retry" hidden>${ctx.icon("refresh")}<span></span></button>`;
      const label = veil.querySelector(".rw-label");
      const retry = veil.querySelector(".rw-retry");
      label.textContent = ctx.t("loading");
      retry.lastChild.textContent = ctx.t("retry");
      el.classList.add("rw-host");
      el.replaceChildren(frame, veil);
      const state = { src, frame, label, retry, slow: false, closing: false, timer: 0 };
      const arm = () => {
        clearTimeout(state.timer);
        state.slow = false;
        retry.hidden = true;
        veil.hidden = false;
        label.textContent = ctx.t("loading");
        state.timer = setTimeout(() => { state.slow = true; label.textContent = ctx.t("slow"); retry.hidden = false; }, 20000);
      };
      frame.addEventListener("load", () => { clearTimeout(state.timer); veil.hidden = true; });
      retry.onclick = () => { arm(); frame.src = `${src}&r=${Date.now().toString(36)}`; };
      const onMessage = (event) => {
        if (event.origin !== location.origin || event.source !== frame.contentWindow || event.data?.type !== "nuxiva:repair-exit" || state.closing) return;
        state.closing = true;
        fetch("/api/desk/close", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" }, body: JSON.stringify({ key: `repair:${project}` }) })
          .then((r) => { if (!r.ok) throw new Error(String(r.status)); }).catch(() => { state.closing = false; });
      };
      window.addEventListener("message", onMessage);
      state.cleanup = () => { clearTimeout(state.timer); window.removeEventListener("message", onMessage); };
      el._rw = state;
      arm();
      frame.src = src;
    },
    update(el, d, ctx) { impl.render(el, d, ctx); },
    destroy(el) {
      if (el._rw) { el._rw.cleanup?.(); el._rw = null; }
      el.classList.remove("rw-host");
      el.replaceChildren();
    },
  };
  NuxivaDesk.register("repair_workbench", impl);
})();
