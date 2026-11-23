import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import * as api from './api';
import type { Attachment, Message, ModelMode } from './types';

export interface StreamRequest {
  threadId: string;
  content: string;
  attachments: Attachment[];
  presetId: string | null;
  mode: ModelMode;
}

const draft = (id: string, threadId: string, role: Message['role'], content: string, attachments: Attachment[]): Message => ({
  id,
  thread_id: threadId,
  role,
  content,
  thought: '',
  artifacts: [],
  attachments,
  memory_recalls: [],
  created_at: Math.floor(Date.now() / 1000),
});

export function useStreamingReply(setMessages: Dispatch<SetStateAction<Message[]>>) {
  const [isThinking, setIsThinking] = useState(false);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []);

  const stop = useCallback(() => controller.current?.abort(), []);

  const run = useCallback(async (req: StreamRequest): Promise<Message | null> => {
    const stamp = Date.now();
    const streamingId = `stream_${stamp}`;
    const patch = (fn: (m: Message) => Message) =>
      setMessages((prev) => prev.map((m) => (m.id === streamingId ? fn(m) : m)));
    controller.current?.abort();
    const ctrl = new AbortController();
    controller.current = ctrl;
    setMessages((prev) => [
      ...prev,
      draft(`temp_${stamp}`, req.threadId, 'user', req.content, req.attachments),
      draft(streamingId, req.threadId, 'assistant', '', []),
    ]);
    setIsThinking(true);
    try {
      const message = await api.streamMessage(
        req.threadId, req.content, req.attachments, req.presetId, req.mode,
        {
          signal: ctrl.signal,
          onToken: (token) => patch((m) => ({ ...m, content: m.content + token })),
          onThoughtDelta: (delta) => patch((m) => ({ ...m, thought: (m.thought || '') + delta })),
          onReset: () => patch((m) => ({ ...m, content: '', thought: '' })),
        },
      );
      patch(() => message);
      return message;
    } catch (err) {
      if (ctrl.signal.aborted) return null;
      setMessages((prev) => prev.filter((m) => m.id !== streamingId));
      throw err;
    } finally {
      if (controller.current === ctrl) {
        controller.current = null;
        setIsThinking(false);
      }
    }
  }, [setMessages]);

  return { isThinking, run, stop };
}
