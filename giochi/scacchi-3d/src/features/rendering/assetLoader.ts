import { GLTF, GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { ResourceLoadError } from '../errors/errorTypes';

export class AssetLoader {
  private static gltfLoader = new GLTFLoader();

  public static async loadModel(baseName: string): Promise<GLTF> {
    let arrayBuffer: ArrayBuffer | null = null;
    const sanitizedName = baseName.replace(/[^a-zA-Z0-9_-]/g, '');

    try {
      const resB64 = await fetch(`./assets/glb/${sanitizedName}.glb.gz.b64`);
      if (resB64.ok) {
        const b64Text = (await resB64.text()).trim();
        if (b64Text.length > 64) {
          const binStr = atob(b64Text);
          const gzBytes = new Uint8Array(binStr.length);
          for (let i = 0; i < binStr.length; i++) {
            gzBytes[i] = binStr.charCodeAt(i);
          }
          if (typeof DecompressionStream !== 'undefined') {
            const ds = new DecompressionStream('gzip');
            const stream = new Blob([gzBytes]).stream().pipeThrough(ds);
            arrayBuffer = await new Response(stream).arrayBuffer();
          }
        }
      }
    } catch {
      arrayBuffer = null;
    }

    if (!arrayBuffer) {
      try {
        const resGlb = await fetch(`./assets/glb/${sanitizedName}.glb`);
        if (resGlb.ok) {
          arrayBuffer = await resGlb.arrayBuffer();
        }
      } catch {
        arrayBuffer = null;
      }
    }

    if (!arrayBuffer) {
      throw new ResourceLoadError(`Failed to load 3D model asset for ${sanitizedName}`, sanitizedName);
    }

    return new Promise((resolve, reject) => {
      this.gltfLoader.parse(
        arrayBuffer!,
        './assets/glb/',
        (gltf) => resolve(gltf),
        (err) => reject(new ResourceLoadError(err.message, sanitizedName))
      );
    });
  }
}
