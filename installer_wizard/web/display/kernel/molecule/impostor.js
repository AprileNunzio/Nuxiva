(() => {
  const vertex = `
    attribute vec4 atom;
    attribute vec4 tint;
    uniform float uScale;
    varying vec3 vCenter;
    varying vec3 vPoint;
    varying float vRadius;
    varying vec4 vTint;
    void main() {
      vec4 center = modelViewMatrix * vec4(atom.xyz, 1.0);
      float radius = atom.w * uScale;
      vec3 point = center.xyz + vec3(position.xy * radius * 3.0, radius);
      vCenter = center.xyz;
      vPoint = point;
      vRadius = radius;
      vTint = tint;
      gl_Position = projectionMatrix * vec4(point, 1.0);
    }`;
  const fragment = `
    uniform mat4 projectionMatrix;
    varying vec3 vCenter;
    varying vec3 vPoint;
    varying float vRadius;
    varying vec4 vTint;
    void main() {
      vec3 ray = normalize(vPoint);
      float b = dot(ray, vCenter);
      float c = dot(vCenter, vCenter) - vRadius * vRadius;
      float h = b * b - c;
      if (h < 0.0) discard;
      vec3 hit = ray * (b - sqrt(h));
      vec3 normal = normalize(hit - vCenter);
      vec3 light = normalize(vec3(0.4, 0.7, 0.6));
      float diffuse = max(dot(normal, light), 0.0);
      float rim = pow(1.0 - max(dot(normal, -ray), 0.0), 2.5);
      float spec = pow(max(dot(reflect(-light, normal), -ray), 0.0), 32.0);
      vec3 color = vTint.rgb * (0.28 + 0.72 * diffuse) + vec3(0.6) * spec + vec3(0.16, 0.88, 1.0) * rim * 0.35;
      vec4 clip = projectionMatrix * vec4(hit, 1.0);
      gl_FragDepthEXT = 0.5 * (clip.z / clip.w) + 0.5;
      gl_FragColor = vec4(color, vTint.a);
    }`;
  function decode(buffer) {
    const view = new DataView(buffer);
    if (buffer.byteLength < 8) throw new Error("data");
    const atoms = view.getUint32(0, true), bonds = view.getUint32(4, true);
    const need = 8 + atoms * 20 + bonds * 8;
    if (need !== buffer.byteLength) throw new Error("data");
    return { atoms, bonds, positions: new Float32Array(buffer, 8, atoms * 4),
      colors: new Uint8Array(buffer, 8 + atoms * 16, atoms * 4), pairs: new Uint32Array(buffer, 8 + atoms * 20, bonds * 2) };
  }

  function build(data, THREE) {
    const quad = new THREE.PlaneBufferGeometry(1, 1);
    const geometry = new THREE.InstancedBufferGeometry();
    geometry.index = quad.index;
    geometry.setAttribute("position", quad.getAttribute("position"));
    geometry.setAttribute("atom", new THREE.InstancedBufferAttribute(data.positions, 4));
    geometry.setAttribute("tint", new THREE.InstancedBufferAttribute(data.colors, 4, true));
    geometry.instanceCount = data.atoms;
    const material = new THREE.ShaderMaterial({ vertexShader: vertex, fragmentShader: fragment,
      uniforms: { uScale: { value: 1 } }, transparent: false });
    material.extensions.fragDepth = true;
    const atoms = new THREE.Mesh(geometry, material);
    atoms.frustumCulled = false;
    const group = new THREE.Group();
    group.add(atoms);
    if (data.bonds) {
      const lines = new THREE.BufferGeometry();
      lines.setAttribute("position", new THREE.InterleavedBufferAttribute(new THREE.InterleavedBuffer(data.positions, 4), 3, 0));
      lines.setAttribute("color", new THREE.InterleavedBufferAttribute(new THREE.InterleavedBuffer(data.colors, 4), 3, 0, true));
      lines.setIndex(new THREE.BufferAttribute(data.pairs, 1));
      group.add(new THREE.LineSegments(lines, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.75 })));
    }
    let radius = 1;
    for (let i = 0; i < data.atoms; i++) {
      const p = i * 4;
      radius = Math.max(radius, Math.hypot(data.positions[p], data.positions[p + 1], data.positions[p + 2]));
    }
    return { group, radius };
  }

  async function fetchScene(id, lod, scheme) {
    const url = `/api/molecules/${encodeURIComponent(id)}/scene?lod=${encodeURIComponent(lod)}&scheme=${encodeURIComponent(scheme)}`;
    const res = await fetch(url, { credentials: "same-origin" });
    if (res.status === 503) throw new Error("engine");
    if (!res.ok) throw new Error("data");
    return decode(await res.arrayBuffer());
  }

  function release(object) {
    object.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
  }

  window.NuxivaMolecule = Object.freeze({ decode, build, fetchScene, release });
})();
