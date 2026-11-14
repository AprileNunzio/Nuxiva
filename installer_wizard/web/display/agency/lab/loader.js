(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const BASE = "/static/display/agency/lab/assets";
  const LIBS = [
    "/vendor/three.min.js",
    "/vendor/OrbitControls.js",
    "/vendor/GLTFLoader.js",
    "/vendor/RoomEnvironment.js",
    `${BASE}/vendor/meshopt_decoder.js`,
  ];
  const CHARACTERS = Object.freeze([
    "mini_male_a", "mini_female_a", "mini_male_b", "mini_female_b", "mini_male_c", "mini_female_c",
    "mini_male_d", "mini_female_d", "mini_male_e", "mini_female_e", "mini_male_f", "mini_female_f",
  ]);
  const V = window.NUXIVA_ASSET_V ? `?v=${window.NUXIVA_ASSET_V}` : "";

  const script = (src) => new Promise((ok, ko) => {
    const el = document.createElement("script");
    el.src = src + V;
    el.async = false;
    el.onload = ok;
    el.onerror = () => ko(new Error(`${src} non caricato`));
    document.head.appendChild(el);
  });

  let ready = null;
  const buffers = new Map();

  function libs() {
    if (ready) return ready;
    ready = (async () => {
      for (const src of LIBS) {
        const name = src.split("/").pop();
        const have = (name === "three.min.js" && window.THREE)
          || (name === "OrbitControls.js" && window.THREE && window.THREE.OrbitControls)
          || (name === "GLTFLoader.js" && window.THREE && window.THREE.GLTFLoader)
          || (name === "RoomEnvironment.js" && window.THREE && window.THREE.RoomEnvironment)
          || (name === "meshopt_decoder.js" && window.MeshoptDecoder);
        if (!have) await script(src);
      }
      if (!window.THREE || !window.THREE.GLTFLoader || !window.MeshoptDecoder) throw new Error("librerie 3D incomplete");
    })().catch((err) => { ready = null; throw err; });
    return ready;
  }

  async function buffer(name) {
    if (!CHARACTERS.includes(name)) throw new Error("personaggio non ammesso");
    if (buffers.has(name)) return buffers.get(name);
    const task = fetch(`${BASE}/characters/${name}.glb${V}`, { cache: "force-cache" }).then((r) => {
      if (!r.ok) throw new Error(`${name} non caricato`);
      return r.arrayBuffer();
    });
    buffers.set(name, task);
    task.catch(() => buffers.delete(name));
    return task;
  }

  async function character(name) {
    await libs();
    const data = await buffer(name);
    const loader = new THREE.GLTFLoader();
    loader.setMeshoptDecoder(MeshoptDecoder);
    return new Promise((ok, ko) => loader.parse(data.slice(0), "", ok, ko));
  }

  LAB.assets = Object.freeze({ libs, character, CHARACTERS });
})();
