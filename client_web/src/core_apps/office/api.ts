export async function fetchOfficeState() {
  try {
    const res = await fetch('/api/v5/office/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'office' };
}
