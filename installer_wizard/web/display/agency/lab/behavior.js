(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const ACTIVE = new Set(["running", "review", "pending"]);

  function owners(agents) {
    const map = new Map();
    agents.forEach((a) => (a.tasks || []).forEach((t) => map.set(String(t.id), { agent: a.id, status: t.status })));
    return map;
  }

  function derive(agent, index) {
    const status = String(agent.status || "idle");
    if (status === "failed") return { mode: "error" };
    if (status === "running") return { mode: "work" };
    if (status === "review") return { mode: "review" };
    if (status === "done") return { mode: "done" };
    if (status === "paused") return { mode: "paused" };
    if (status === "pending") {
      for (const task of agent.tasks || []) {
        if (task.status !== "pending") continue;
        for (const dep of task.depends_on || []) {
          const owner = index.get(String(dep));
          if (owner && owner.agent !== agent.id && ACTIVE.has(owner.status)) return { mode: "consult", target: owner.agent };
        }
      }
      return { mode: "wait" };
    }
    return { mode: "idle" };
  }

  const LABEL = Object.freeze({
    work: "lab_state_working", wait: "lab_state_waiting", consult: "lab_state_consulting", review: "lab_state_review",
    error: "lab_state_error", done: "lab_state_done", paused: "lab_state_paused", idle: "lab_state_idle",
  });

  function plan(office) {
    const agents = (office.agents || []).filter((a) => a && a.seated !== false || a.tasks);
    const index = owners(agents);
    const out = new Map();
    agents.forEach((a) => out.set(a.id, derive(a, index)));
    return out;
  }

  function controller(person, home, ctx) {
    const L = LAB.layout;
    const seat = L.seatOf(home);
    const st = { mode: "idle", target: null, phase: "seat", timer: 0, spot: -1, busy: false };
    const exit = { x: seat.x, z: seat.z + 0.62 };

    function seatedPose(arms) {
      person.setSeated(true, 0.45);
      person.face(Math.PI);
      person.typing = arms === "type";
      if (arms === "type") person.mix(["sitLegs", "hold"]);
      else if (arms === "no") person.mix(["sitLegs", "no"]);
      else person.mix(["sitLegs", "sitArms"]);
    }

    function standPose(layers) {
      person.setSeated(false);
      person.typing = false;
      person.mix(layers);
    }

    function goTo(target, face, then, layersAfter) {
      person.setSeated(false);
      person.typing = false;
      person.mix(["walk"]);
      const here = { x: person.root.position.x, z: person.root.position.z };
      const nearSeat = Math.hypot(here.x - seat.x, here.z - seat.z) < 0.3;
      const from = nearSeat ? { ...here, exit, node: L.nodeBeside(home) } : { ...here };
      const path = L.pathBetween(from, target);
      st.busy = true;
      person.walk(path.slice(1), 1.1, () => {
        st.busy = false;
        if (face !== undefined) person.face(face);
        standPose(layersAfter || ["idle"]);
        if (then) then();
      });
    }

    function returnHome(then) {
      const here = { x: person.root.position.x, z: person.root.position.z };
      if (Math.hypot(here.x - seat.x, here.z - seat.z) < 0.25) { if (then) then(); return; }
      person.setSeated(false);
      person.mix(["walk"]);
      const path = L.pathBetween({ ...here }, { x: seat.x, z: seat.z, node: L.nodeBeside(home), entry: exit });
      st.busy = true;
      person.walk(path.slice(1), 1.1, () => {
        st.busy = false;
        if (then) then();
      });
    }

    function enter(mode, target) {
      st.mode = mode;
      st.target = target || null;
      st.timer = 0;
      st.phase = "start";
    }

    function apply() {
      const mode = st.mode;
      if (st.busy) return;
      if (mode === "work") return returnHome(() => seatedPose("type"));
      if (mode === "error") return returnHome(() => seatedPose("no"));
      if (mode === "paused" || mode === "wait" || mode === "idle") return returnHome(() => seatedPose("rest"));
      if (mode === "done") {
        return returnHome(() => {
          const spot = L.standBeside(home);
          goTo({ x: spot.x, z: spot.z }, 0.35, null, ["yes"]);
        });
      }
      if (mode === "review") {
        const spot = L.REVIEW[ctx.reviewSlot(person.id) % L.REVIEW.length];
        goTo(spot, Math.atan2(L.CEO.x - spot.x, L.CEO.z - spot.z), null, ["idle"]);
        return undefined;
      }
      if (mode === "consult") {
        const other = ctx.slotOf(st.target);
        if (!other) return returnHome(() => seatedPose("rest"));
        const spot = L.standBeside(other);
        goTo({ x: spot.x, z: spot.z }, spot.face, () => { st.phase = "talk"; st.timer = 0; }, ["talk"]);
      }
      return undefined;
    }

    function update(dt) {
      st.timer += dt;
      if (st.phase === "start") { st.phase = "run"; apply(); return; }
      if (st.mode === "consult" && !st.busy) {
        if (st.phase === "talk" && st.timer > 9) {
          st.phase = "rest";
          st.timer = 0;
          returnHome(() => seatedPose("rest"));
        } else if (st.phase === "rest" && st.timer > 16) {
          st.phase = "run";
          st.timer = 0;
          apply();
        }
      }
    }

    return { enter, update, state: st, home, seat };
  }

  LAB.behavior = Object.freeze({ plan, controller, derive, LABEL });
})();
