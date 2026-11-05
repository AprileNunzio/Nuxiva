(() => {
  const KINDS = new Set(["holo_quilt", "holo_pyramid"]);
  const clampInt = (v, lo, hi, d) => (Number.isInteger(v) ? Math.min(hi, Math.max(lo, v)) : d);
  const clampNum = (v, lo, hi, d) => (Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : d);

  function calibration(raw) {
    const c = raw && typeof raw === "object" ? raw : {};
    const cols = clampInt(c.cols, 1, 16, 8), rows = clampInt(c.rows, 1, 16, 6);
    return { cols, rows, views: Math.min(cols * rows, clampInt(c.views, 1, 256, cols * rows)),
      cone: clampNum(c.view_cone_deg, 10, 60, 40), aspect: clampNum(c.aspect, 0.25, 4, 0.75), size: clampInt(c.quilt, 512, 8192, 4096) };
  }

  function create(THREE, renderer, kind, raw) {
    if (!KINDS.has(kind)) return null;
    const cal = calibration(raw);
    const eye = new THREE.PerspectiveCamera(14, cal.aspect, 0.01, 100);
    const target = kind === "holo_quilt" ? new THREE.WebGLRenderTarget(cal.size, cal.size) : null;
    const blit = target ? new THREE.Mesh(new THREE.PlaneBufferGeometry(2, 2), new THREE.MeshBasicMaterial({ map: target.texture })) : null;
    const flat = new THREE.Scene(), ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    if (blit) flat.add(blit);
    const size = new THREE.Vector2();

    function quilt(scene, camera) {
      const distance = camera.position.length() || 4, w = cal.size / cal.cols, h = cal.size / cal.rows;
      const half = THREE.MathUtils.degToRad(cal.cone) / 2;
      renderer.setRenderTarget(target);
      renderer.setScissorTest(true);
      renderer.clear();
      for (let i = 0; i < cal.views; i++) {
        const t = cal.views > 1 ? i / (cal.views - 1) : 0.5, angle = -half + t * 2 * half;
        eye.position.set(Math.sin(angle) * distance, camera.position.y, Math.cos(angle) * distance);
        eye.lookAt(0, 0, 0);
        const x = (i % cal.cols) * w, y = Math.floor(i / cal.cols) * h;
        renderer.setViewport(x, y, w, h); renderer.setScissor(x, y, w, h);
        renderer.render(scene, eye);
      }
      renderer.setScissorTest(false);
      renderer.setRenderTarget(null);
      renderer.getSize(size);
      renderer.setViewport(0, 0, size.x, size.y);
      renderer.render(flat, ortho);
    }

    function pyramid(scene, camera) {
      renderer.getSize(size);
      const side = Math.min(size.x, size.y) / 3, cx = size.x / 2, cy = size.y / 2, distance = camera.position.length() || 4;
      eye.aspect = 1; eye.fov = 30; eye.updateProjectionMatrix();
      renderer.setScissorTest(true);
      renderer.setClearColor(0x000000, 1);
      renderer.clear();
      [[0, 0, -1, Math.PI], [Math.PI / 2, 1, 0, Math.PI / 2], [Math.PI, 0, 1, 0], [-Math.PI / 2, -1, 0, -Math.PI / 2]].forEach(([turn, dx, dy, roll]) => {
        eye.position.set(Math.sin(turn) * distance, 0, Math.cos(turn) * distance);
        eye.up.set(0, 1, 0); eye.lookAt(0, 0, 0); eye.rotateZ(roll);
        const x = cx - side / 2 + dx * side, y = cy - side / 2 + dy * side;
        renderer.setViewport(x, y, side, side); renderer.setScissor(x, y, side, side);
        renderer.render(scene, eye);
      });
      renderer.setScissorTest(false);
      renderer.setViewport(0, 0, size.x, size.y);
    }

    return {
      kind, calibration: cal,
      render(scene, camera) { (kind === "holo_quilt" ? quilt : pyramid)(scene, camera); },
      dispose() { if (target) target.dispose(); if (blit) { blit.geometry.dispose(); blit.material.dispose(); } },
    };
  }

  window.NuxivaMultiview = Object.freeze({ create, calibration, KINDS });
})();
