export async function fetchVaultState() {
  try {
    const res = await fetch('/api/v5/vault/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'vault' };
}
