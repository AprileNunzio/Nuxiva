(() => {
  const REFRESH_MS = 10000;

  async function check() {
    let allowed = false;
    try {
      const r = await fetch("/api/display/privileges", { cache: "no-store", credentials: "same-origin" });
      allowed = r.ok && (await r.json()).super_admin === true;
    } catch (err) {
      console.info("Privilegi del display non letti:", err.message);
    }
    document.body.classList.toggle("super-admin", allowed);
    const D = window.NuxivaDisplay;
    if (!allowed && D && ["brain", "flow"].includes(D.mode) && D.setMode) D.setMode("face");
  }

  check();
  setInterval(check, REFRESH_MS);
})();
