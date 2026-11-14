(() => {
  const webgl = () => {
    try {
      const c = document.createElement("canvas");
      return Boolean(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
    } catch (err) {
      return false;
    }
  };

  function create(host, callbacks = {}) {
    let impl = null;
    let queued = null;
    let flat = false;

    function fallback() {
      if (flat || !window.NuxivaAgencyOffice2D) return;
      flat = true;
      if (impl && impl.dispose) impl.dispose();
      host.replaceChildren();
      impl = window.NuxivaAgencyOffice2D.create(host, callbacks);
      if (queued) impl.update(queued.office);
    }

    const lab = window.NuxivaLab && window.NuxivaLab.scene;
    if (lab && webgl()) {
      impl = lab.create(host, { ...callbacks, onFail: fallback });
    } else {
      fallback();
    }

    return {
      update(office, meta) {
        queued = { office, meta };
        impl.update(office, meta);
      },
      stop() { if (impl) impl.stop(); },
      select(id) { if (impl) impl.select(id); },
      advance(seconds) { if (impl && impl.advance) impl.advance(seconds); },
      setView(pos, target) { if (impl && impl.setView) impl.setView(pos, target); },
      dispose() { if (impl && impl.dispose) impl.dispose(); },
    };
  }

  window.NuxivaAgencyOffice3D = { create };
})();
