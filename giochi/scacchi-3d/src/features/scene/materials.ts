import * as THREE from 'three';

export class MaterialFactory {
  private static whiteMarble: THREE.MeshStandardMaterial | null = null;
  private static blackObsidian: THREE.MeshStandardMaterial | null = null;
  private static antiqueGoldWhite: THREE.MeshStandardMaterial | null = null;
  private static antiqueGoldBlack: THREE.MeshStandardMaterial | null = null;
  private static forgedSteelWhite: THREE.MeshStandardMaterial | null = null;
  private static forgedSteelBlack: THREE.MeshStandardMaterial | null = null;
  private static runeGlowWhite: THREE.MeshStandardMaterial | null = null;
  private static runeGlowBlack: THREE.MeshStandardMaterial | null = null;

  public static getWhiteMarbleMaterial(): THREE.MeshStandardMaterial {
    if (!this.whiteMarble) {
      this.whiteMarble = new THREE.MeshStandardMaterial({
        color: new THREE.Color(0xf6f3ec),
        roughness: 0.22,
        metalness: 0.04
      });
    }
    return this.whiteMarble;
  }

  public static getBlackObsidianMaterial(): THREE.MeshStandardMaterial {
    if (!this.blackObsidian) {
      this.blackObsidian = new THREE.MeshStandardMaterial({
        color: new THREE.Color(0x1a1e27),
        roughness: 0.24,
        metalness: 0.22
      });
    }
    return this.blackObsidian;
  }

  public static getAntiqueGoldMaterial(isBlackSide = false): THREE.MeshStandardMaterial {
    if (isBlackSide) {
      if (!this.antiqueGoldBlack) {
        this.antiqueGoldBlack = new THREE.MeshStandardMaterial({
          color: new THREE.Color(0xb8922c),
          roughness: 0.28,
          metalness: 0.88
        });
      }
      return this.antiqueGoldBlack;
    }
    if (!this.antiqueGoldWhite) {
      this.antiqueGoldWhite = new THREE.MeshStandardMaterial({
        color: new THREE.Color(0xd4af37),
        roughness: 0.24,
        metalness: 0.90
      });
    }
    return this.antiqueGoldWhite;
  }

  public static getForgedSteelMaterial(isBlackSide = false): THREE.MeshStandardMaterial {
    if (isBlackSide) {
      if (!this.forgedSteelBlack) {
        this.forgedSteelBlack = new THREE.MeshStandardMaterial({
          color: new THREE.Color(0x424a58),
          roughness: 0.22,
          metalness: 0.88
        });
      }
      return this.forgedSteelBlack;
    }
    if (!this.forgedSteelWhite) {
      this.forgedSteelWhite = new THREE.MeshStandardMaterial({
        color: new THREE.Color(0xdce4ee),
        roughness: 0.18,
        metalness: 0.94
      });
    }
    return this.forgedSteelWhite;
  }

  public static getRuneGlowMaterial(isBlackSide = false): THREE.MeshStandardMaterial {
    if (isBlackSide) {
      if (!this.runeGlowBlack) {
        this.runeGlowBlack = new THREE.MeshStandardMaterial({
          color: new THREE.Color(0xff6622),
          emissive: new THREE.Color(0xcc3300),
          emissiveIntensity: 1.6,
          roughness: 0.45,
          metalness: 0.05
        });
      }
      return this.runeGlowBlack;
    }
    if (!this.runeGlowWhite) {
      this.runeGlowWhite = new THREE.MeshStandardMaterial({
        color: new THREE.Color(0xf5d76e),
        emissive: new THREE.Color(0xd4af37),
        emissiveIntensity: 1.5,
        roughness: 0.45,
        metalness: 0.05
      });
    }
    return this.runeGlowWhite;
  }
}
