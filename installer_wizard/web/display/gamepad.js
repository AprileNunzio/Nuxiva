(() => {
  const BUTTONS = { a: 0, b: 1, x: 2, y: 3, lb: 4, rb: 5, select: 8, start: 9, up: 12, down: 13, left: 14, right: 15 };
  let profiles = [], rev = null, loading = null, signature = "";

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const lower = (text) => String(text || "").toLowerCase();

  function shape(value, profile) {
    const dead = clamp(Number(profile.deadzone) || 0, 0, 40) / 100;
    const magnitude = Math.abs(value);
    if (magnitude <= dead) return 0;
    const scaled = (magnitude - dead) / (1 - dead);
    const exponent = 1 + (5 - clamp(Number(profile.sensitivity) || 5, 1, 10)) * 0.15;
    return Math.sign(value) * clamp(Math.pow(scaled, exponent), 0, 1);
  }

  function pads() {
    if (!navigator.getGamepads) return [];
    return Array.from(navigator.getGamepads()).filter((gp) => gp && gp.connected);
  }

  function assign() {
    const free = pads();
    const taken = new Set();
    const bound = profiles.map((profile) => {
      const name = lower(profile.name);
      const gp = free.find((g) => !taken.has(g.index) && name && lower(g.id).includes(name));
      if (gp) taken.add(gp.index);
      return { profile, gp };
    });
    bound.forEach((entry) => {
      if (entry.gp) return;
      const gp = free.find((g) => !taken.has(g.index));
      if (gp) { taken.add(gp.index); entry.gp = gp; }
    });
    free.filter((g) => !taken.has(g.index)).forEach((gp, i) => {
      bound.push({ profile: { name: gp.id, label: gp.id, slot: profiles.length + i + 1, deadzone: 8, sensitivity: 5, invert_y: false, vibration: true }, gp });
    });
    return bound;
  }

  function read(entry) {
    const { gp, profile } = entry;
    const axis = (i) => shape(gp.axes[i] || 0, profile);
    const pressed = (i) => !!(gp.buttons[i] && gp.buttons[i].pressed);
    const value = (i) => clamp(gp.buttons[i] ? gp.buttons[i].value : 0, 0, 1);
    const invert = profile.invert_y ? -1 : 1;
    const buttons = {};
    Object.entries(BUTTONS).forEach(([key, i]) => { buttons[key] = pressed(i); });
    return {
      slot: profile.slot, label: profile.label || profile.name, connected: true,
      x: axis(0), y: axis(1) * invert, rx: axis(2), ry: axis(3) * invert,
      steer: axis(0), throttle: Math.max(value(7), buttons.a ? 1 : 0), brake: Math.max(value(6), buttons.b ? 1 : 0),
      buttons,
    };
  }

  function announce() {
    const list = assign().map((e) => ({ slot: e.profile.slot, label: e.profile.label || e.profile.name }));
    const next = JSON.stringify(list);
    if (next === signature) return;
    signature = next;
    window.dispatchEvent(new CustomEvent("nuxiva:gamepads", { detail: list }));
  }

  async function load() {
    try {
      const r = await fetch("/api/bluetooth/gamepads", { cache: "no-store", credentials: "same-origin" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      profiles = Array.isArray(data.gamepads) ? data.gamepads.slice(0, 8) : [];
    } catch (e) {
      console.warn("Profili dei controller non letti", e);
    } finally {
      loading = null;
      announce();
    }
  }

  window.addEventListener("gamepadconnected", announce);
  window.addEventListener("gamepaddisconnected", announce);

  window.NuxivaGamepad = {
    sync(next) {
      if (next === rev) return;
      rev = next;
      if (!loading) loading = load();
    },
    players() { return assign().map(read); },
    read(slot) {
      const entry = assign().find((e) => e.profile.slot === slot);
      return entry ? read(entry) : { slot, connected: false };
    },
    rumble(slot, ms = 200, strength = 0.6) {
      const entry = assign().find((e) => e.profile.slot === slot);
      const actuator = entry && entry.profile.vibration !== false && entry.gp.vibrationActuator;
      if (!actuator || !actuator.playEffect) return Promise.resolve(false);
      const power = clamp(strength, 0, 1);
      return actuator.playEffect("dual-rumble", { duration: clamp(ms, 0, 2000), strongMagnitude: power, weakMagnitude: power })
        .then(() => true, (e) => { console.warn("Vibrazione del controller non riuscita", e); return false; });
    },
  };
})();
