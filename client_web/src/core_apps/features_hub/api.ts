export async function fetchFeatures_hubState() {
  try {
    const res = await fetch('/api/v5/features_hub/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'features_hub' };
}
