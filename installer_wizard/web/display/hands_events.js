(() => {
  function create(ops) {
    const st = ops.state;
    const toScreen = (e) => ({ x: e.x * window.innerWidth, y: e.y * window.innerHeight });

    function pointer(e) {
      const at = toScreen(e);
      st.x = at.x; st.y = at.y;
      if (e.phase === "hidden") { st.pinch = false; ops.hideCursor(); return; }
      if (e.phase === "down") { st.pinch = true; ops.press(at.x, at.y); }
      else if (e.phase === "drag") ops.drag(at.x, at.y);
      else if (e.phase === "up") { st.pinch = false; ops.release(at.x, at.y); }
      ops.showCursor();
    }

    function duo(e) {
      const at = toScreen(e);
      if (e.phase === "start") {
        st.duo = { x: at.x, y: at.y, el: ops.pointAt(at.x, at.y), span: 1 };
        ops.emit("start");
        return;
      }
      if (!st.duo) return;
      if (e.phase === "end") { ops.emit("end"); st.duo = null; st.spread = null; return; }
      st.duo.x = at.x; st.duo.y = at.y;
      st.duo.span *= e.scale;
      const d = { scale: e.scale, rotate: e.rotate, pan: { x: e.pan_x, y: e.pan_y } };
      if (ops.emit("update", d)) return;
      const target = st.duo.el && st.duo.el.closest(".v3-stage canvas");
      if (target && e.scale !== 1) {
        target.dispatchEvent(new WheelEvent("wheel", { bubbles: true, cancelable: true, deltaY: -Math.log(e.scale) * 900, clientX: at.x, clientY: at.y }));
      } else if (!target) ops.spread(st.duo.el, st.duo.span);
    }

    function announce(name, e) {
      window.dispatchEvent(new CustomEvent(name, { detail: e }));
    }

    return function handle(e) {
      if (e.type === "pointer") pointer(e);
      else if (e.type === "duo") duo(e);
      else if (e.type === "gesture") announce("nuxiva-hand-gesture", e);
      else if (e.type === "action") announce("nuxiva-hand-action", e);
      window.NuxivaDisplay.lastInteraction = Date.now();
    };
  }

  window.NuxivaHandsEvents = { create };
})();
