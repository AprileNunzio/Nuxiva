export async function fetchUpdaterState() {
  try {
    const res = await fetch('/api/v5/updater/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'updater' };
}
