import type { Message } from './types';

export function toggleReaction(messages: Message[], msgId: string, emoji: string): Message[] {
  return messages.map((m) => {
    if (m.id !== msgId) return m;
    const current = m.reactions || [];
    const idx = current.findIndex((r) => r.emoji === emoji);
    if (idx < 0) {
      return { ...m, reactions: [...current, { emoji, count: 1, authors: ['user'] }] };
    }
    const existing = current[idx];
    const hasUser = existing.authors.includes('user');
    const authors = hasUser ? existing.authors.filter((a) => a !== 'user') : [...existing.authors, 'user'];
    const count = hasUser ? existing.count - 1 : existing.count + 1;
    if (count <= 0) return { ...m, reactions: current.filter((_, i) => i !== idx) };
    const updated = [...current];
    updated[idx] = { ...existing, count, authors };
    return { ...m, reactions: updated };
  });
}

export function votePoll(
  messages: Message[],
  msgId: string,
  pollId: string,
  optionId: string,
  stepIndex?: number,
): Message[] {
  return messages.map((m) => {
    if (m.id !== msgId || !m.poll || m.poll.id !== pollId) return m;
    const p = m.poll;
    const bump = <T extends { id: string; votes: number }>(opts: T[]) =>
      opts.map((o) => (o.id === optionId ? { ...o, votes: o.votes + 1 } : o));
    if (stepIndex !== undefined && p.steps && p.steps[stepIndex]) {
      const steps = [...p.steps];
      steps[stepIndex] = { ...steps[stepIndex], userVotedId: optionId, options: bump(steps[stepIndex].options) };
      return { ...m, poll: { ...p, steps } };
    }
    return { ...m, poll: { ...p, userVotedId: optionId, options: bump(p.options) } };
  });
}
