export async function fetchNodesState() {
  try {
    const res = await fetch('/api/v5/nodes/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'nodes' };
}
