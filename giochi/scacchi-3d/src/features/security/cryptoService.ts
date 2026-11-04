export class CryptoService {
  private static masterKeyPromise: Promise<CryptoKey> | null = null;

  private static async getMasterKey(): Promise<CryptoKey> {
    if (!this.masterKeyPromise) {
      this.masterKeyPromise = (async () => {
        const rawEntropy = 'sanctum_vault_secure_key_3d_material_token';
        const enc = new TextEncoder();
        const hash = await crypto.subtle.digest('SHA-256', enc.encode(rawEntropy));
        return crypto.subtle.importKey(
          'raw',
          hash,
          { name: 'AES-GCM' },
          false,
          ['encrypt', 'decrypt']
        );
      })();
    }
    return this.masterKeyPromise;
  }

  public static async encrypt(plainText: string): Promise<string> {
    const key = await this.getMasterKey();
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(plainText);
    const cipherBuffer = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      key,
      encoded
    );
    const cipherArray = new Uint8Array(cipherBuffer);
    const combined = new Uint8Array(iv.length + cipherArray.length);
    combined.set(iv);
    combined.set(cipherArray, iv.length);
    return btoa(String.fromCharCode(...combined));
  }

  public static async decrypt(cipherBase64: string): Promise<string> {
    const key = await this.getMasterKey();
    const binary = atob(cipherBase64);
    const combined = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      combined[i] = binary.charCodeAt(i);
    }
    const iv = combined.slice(0, 12);
    const ciphertext = combined.slice(12);
    const decryptedBuffer = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      key,
      ciphertext
    );
    return new TextDecoder().decode(decryptedBuffer);
  }
}
