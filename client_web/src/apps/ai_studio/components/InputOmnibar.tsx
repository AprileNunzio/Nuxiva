import React, { useState, useRef, useEffect } from 'react';
import { useStudioI18n } from '../scope';
import type { Attachment, ModelMode } from '../types';
import { uploadFile } from '../api';

interface InputOmnibarProps {
  onSendMessage: (content: string, attachments: Attachment[]) => void;
  onOpenSmbPicker: () => void;
  selectedMode: ModelMode;
  onChangeMode: (mode: ModelMode) => void;
  disabled?: boolean;
}

export const InputOmnibar: React.FC<InputOmnibarProps> = ({
  onSendMessage,
  onOpenSmbPicker,
  selectedMode,
  onChangeMode,
  disabled = false,
}) => {
  const { t } = useStudioI18n();
  const [text, setText] = useState('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isListening, setIsListening] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [text]);

  const handleSend = () => {
    if ((!text.trim() && attachments.length === 0) || disabled) return;
    onSendMessage(text.trim(), attachments);
    setText('');
    setAttachments([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const att = await uploadFile(file);
        setAttachments((prev) => [...prev, att]);
      } catch (err) {
        console.error(err);
      }
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const toggleVoice = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setIsListening((prev) => !prev);
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'it-IT';

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setText((prev) => (prev ? `${prev} ${transcript}` : transcript));
        }
      };
      recognition.start();
    } catch {
      setIsListening(false);
    }
  };

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  return (
    <div className="w-full p-3 bg-slate-950/90 border-t border-slate-800/80 backdrop-blur-md flex flex-col gap-2">
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 pb-1">
          {attachments.map((att) => (
            <div
              key={att.id}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/90 border border-slate-700 text-xs text-slate-200"
            >
              <span>📎</span>
              <span className="max-w-[150px] truncate">{att.name}</span>
              <button
                type="button"
                onClick={() => removeAttachment(att.id)}
                className="hover:text-red-400 p-0.5 text-slate-400"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between gap-2 px-1 text-xs">
        <div className="flex items-center gap-1 bg-slate-900/90 p-1 rounded-lg border border-slate-800">
          {(['fast', 'reasoning', 'creative', 'code'] as ModelMode[]).map((mode) => {
            const isCurrent = selectedMode === mode;
            const modeLabels: Record<ModelMode, string> = {
              fast: `⚡ ${t('mode_fast')}`,
              reasoning: `🧠 ${t('mode_reasoning')}`,
              creative: `✨ ${t('mode_creative')}`,
              code: `💻 ${t('mode_code')}`,
            };
            return (
              <button
                key={mode}
                type="button"
                onClick={() => onChangeMode(mode)}
                className={`px-2 py-1 rounded-md transition-all font-medium ${
                  isCurrent
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-xs'
                    : 'text-slate-400 hover:text-slate-200 border border-transparent'
                }`}
              >
                {modeLabels[mode]}
              </button>
            );
          })}
        </div>

        {isListening && (
          <div className="flex items-center gap-2 text-cyan-400 text-xs font-medium animate-pulse">
            <span className="h-2 w-2 rounded-full bg-cyan-400" />
            <span>{t('voice_listening')}</span>
          </div>
        )}
      </div>

      <div className="relative flex items-end gap-2 bg-slate-900/90 border border-slate-800 rounded-2xl p-2 focus-within:border-cyan-500/60 transition-colors shadow-inner">
        <div className="flex items-center gap-1 pb-1">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
            multiple
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition-colors"
            title={t('attach_file')}
          >
            📎
          </button>
          <button
            type="button"
            onClick={onOpenSmbPicker}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition-colors"
            title={t('browse_smb')}
          >
            🗄️
          </button>
          <button
            type="button"
            onClick={toggleVoice}
            className={`p-2 rounded-xl transition-colors ${
              isListening
                ? 'bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/80'
            }`}
            title={isListening ? t('voice_stop') : t('voice_start')}
          >
            🎙️
          </button>
        </div>

        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('input_placeholder')}
          className="flex-1 bg-transparent border-0 text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none max-h-40 py-2"
        />

        <button
          type="button"
          disabled={(!text.trim() && attachments.length === 0) || disabled}
          onClick={handleSend}
          className="p-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white disabled:opacity-40 disabled:hover:from-cyan-600 disabled:hover:to-blue-600 transition-all shadow-md active:scale-95 flex items-center justify-center mb-0.5"
          title={t('send')}
        >
          ➤
        </button>
      </div>
    </div>
  );
};
