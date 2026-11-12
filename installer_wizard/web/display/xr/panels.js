(() => {
  const RADIUS = 1.6, HEIGHT = 1.45, ARC = Math.PI * 0.9, SIZE = [512, 256];

  function texture(THREE, panel) {
    const canvas = document.createElement("canvas");
    canvas.width = SIZE[0]; canvas.height = SIZE[1];
    const g = canvas.getContext("2d");
    g.clearRect(0, 0, SIZE[0], SIZE[1]);
    g.fillStyle = "rgba(41, 224, 255, 0.9)";
    g.font = "96px system-ui, sans-serif";
    g.textBaseline = "middle";
    g.fillText(String(panel.icon || "").slice(0, 4), 28, SIZE[1] / 2);
    g.fillStyle = "#dff6ff";
    g.font = "44px system-ui, sans-serif";
    g.fillText(String(panel.name || panel.id || "").slice(0, 28), 150, SIZE[1] / 2);
    const map = new THREE.CanvasTexture(canvas);
    if (THREE.sRGBEncoding) map.encoding = THREE.sRGBEncoding;
    return map;
  }

  function arrange(THREE, group, panels, immersive) {
    group.children.slice().forEach((child) => { group.remove(child); child.geometry.dispose(); child.material.map.dispose(); child.material.dispose(); });
    const list = panels.filter((p) => !p.molecule);
    list.forEach((panel, i) => {
      const t = list.length > 1 ? i / (list.length - 1) : 0.5, angle = -ARC / 2 + t * ARC;
      const mesh = new THREE.Mesh(new THREE.PlaneBufferGeometry(0.6, 0.3),
        new THREE.MeshBasicMaterial({ map: texture(THREE, panel), transparent: true, depthWrite: false }));
      if (immersive) {
        mesh.position.set(Math.sin(angle) * RADIUS, HEIGHT, -Math.cos(angle) * RADIUS);
        mesh.lookAt(0, HEIGHT, 0);
      } else {
        mesh.position.set((t - 0.5) * Math.min(3, list.length * 0.7), -1.25, 0);
      }
      mesh.userData.key = panel.key;
      group.add(mesh);
    });
  }

  window.NuxivaXrPanels = Object.freeze({ arrange });
})();
