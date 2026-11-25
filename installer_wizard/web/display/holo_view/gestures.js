(() => {
  const PINCH = 0.33;
  const RELEASE = 0.48;
  const FIST_MS = 700;
  const SMOOTH = 0.35;
  const ROTATE = 5.2;
  const PAN = 2.4;

  const dist = (a, b) => Math.hypot((a.x || 0) - (b.x || 0), (a.y || 0) - (b.y || 0));
  const mid = (a, b) => ({ x: ((a.x || 0) + (b.x || 0)) / 2, y: ((a.y || 0) + (b.y || 0)) / 2 });

  function pose(lm, pinched) {
    const palm = Math.max(0.05, dist(lm[0], lm[9]));
    const ratio = dist(lm[4], lm[8]) / palm;
    let extended = 0;
    for (const [tip, pip] of [[8, 6], [12, 10], [16, 14], [20, 18]]) {
      if (dist(lm[0], lm[tip]) > dist(lm[0], lm[pip]) * 1.12) extended += 1;
    }
    const pinch = pinched ? ratio < RELEASE : ratio < PINCH;
    if (pinch) return { kind: "pinch", at: mid(lm[4], lm[8]) };
    if (extended >= 4) return { kind: "open", at: lm[9] };
    if (extended <= 1) return { kind: "fist", at: lm[9] };
    return { kind: "other", at: lm[9] };
  }

  function create() {
    const st = { prev: null, pinched: [false, false], fistSince: 0, fistFired: false, span: 0, palms: 0, smooth: { yaw: 0, pitch: 0, zoom: 1, px: 0, py: 0 } };

    function blend(key, value) {
      st.smooth[key] = st.smooth[key] * SMOOTH + value * (1 - SMOOTH);
      return st.smooth[key];
    }

    function reset() {
      st.prev = null;
      st.span = 0;
      st.palms = 0;
      st.fistSince = 0;
      st.fistFired = false;
      st.pinched = [false, false];
    }

    function feed(hands, now) {
      const list = Array.isArray(hands) ? hands.filter((h) => Array.isArray(h) && h.length >= 21) : [];
      const out = { gesture: "idle", yaw: 0, pitch: 0, zoom: 1, px: 0, py: 0, explode: null, toggle: false };
      if (!list.length) { reset(); return out; }
      const poses = list.slice(0, 2).map((lm, i) => pose(lm, st.pinched[i]));
      st.pinched = poses.map((p) => p.kind === "pinch");
      if (poses.length === 2 && poses.every((p) => p.kind === "pinch")) {
        const span = Math.max(0.04, dist(poses[0].at, poses[1].at));
        const center = mid(poses[0].at, poses[1].at);
        if (st.prev && st.prev.kind === "duo") {
          out.zoom = blend("zoom", Math.max(0.8, Math.min(1.25, span / st.span)));
          out.px = blend("px", (st.prev.at.x - center.x) * PAN);
          out.py = blend("py", (center.y - st.prev.at.y) * PAN);
          out.gesture = Math.abs(out.zoom - 1) > 0.01 ? "zoom" : "pan";
        }
        st.span = span;
        st.prev = { kind: "duo", at: center };
        return out;
      }
      if (poses.length === 2 && poses.every((p) => p.kind === "open")) {
        const span = dist(poses[0].at, poses[1].at);
        if (!st.palms) st.palms = span;
        out.explode = Math.max(0, Math.min(1, (span - st.palms) * 2.2 + 0.5));
        out.gesture = "explode";
        st.prev = null;
        return out;
      }
      st.palms = 0;
      const first = poses[0];
      if (first.kind === "pinch") {
        if (st.prev && st.prev.kind === "pinch") {
          out.yaw = blend("yaw", (st.prev.at.x - first.at.x) * ROTATE);
          out.pitch = blend("pitch", (first.at.y - st.prev.at.y) * ROTATE);
        }
        out.gesture = "rotate";
        st.prev = { kind: "pinch", at: first.at };
        st.fistSince = 0;
        return out;
      }
      st.prev = null;
      if (first.kind === "fist") {
        if (!st.fistSince) { st.fistSince = now; st.fistFired = false; }
        if (!st.fistFired && now - st.fistSince >= FIST_MS) {
          st.fistFired = true;
          out.toggle = true;
          out.gesture = "toggle";
        }
        return out;
      }
      st.fistSince = 0;
      return out;
    }

    return { feed, reset };
  }

  window.NuxivaHoloGestures = Object.freeze({ create });
})();
