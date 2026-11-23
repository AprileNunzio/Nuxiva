import { useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import * as api from './api';
import { toggleReaction } from './messageMutations';
import type { Message } from './types';

type Feedback = 'positive' | 'negative' | null;

const persisted = (id: string) => !id.startsWith('temp_') && !id.startsWith('stream_');

export function useMessageMarks(
  threadId: string | null,
  setMessages: Dispatch<SetStateAction<Message[]>>,
  onError: (err: unknown) => void,
) {
  const apply = useCallback((msgId: string, marks: api.MessageMarks) => {
    setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...m, reactions: marks.reactions, feedback: marks.feedback } : m)));
  }, [setMessages]);

  const react = useCallback(async (msgId: string, emoji: string) => {
    let snapshot: Message[] = [];
    setMessages((prev) => { snapshot = prev; return toggleReaction(prev, msgId, emoji); });
    if (!threadId || !persisted(msgId)) return;
    try {
      apply(msgId, await api.toggleMessageReaction(threadId, msgId, emoji));
    } catch (err) {
      setMessages(snapshot);
      onError(err);
    }
  }, [apply, onError, setMessages, threadId]);

  const rate = useCallback(async (msgId: string, value: Feedback) => {
    let snapshot: Message[] = [];
    setMessages((prev) => { snapshot = prev; return prev.map((m) => (m.id === msgId ? { ...m, feedback: value } : m)); });
    if (!threadId || !persisted(msgId)) return;
    try {
      apply(msgId, await api.setMessageFeedback(threadId, msgId, value));
    } catch (err) {
      setMessages(snapshot);
      onError(err);
    }
  }, [apply, onError, setMessages, threadId]);

  return { react, rate };
}
