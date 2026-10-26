import React, { FormEvent, useEffect, useRef, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { Field, inputClass } from '../shared/kit';
import { cloneVoice } from './studioApi';
import { Mic, Square, Play, Upload, CheckCircle2, AlertCircle } from 'lucide-react';

interface Props {
  sentences: Record<string, string>;
  busy: boolean;
  run: (task: () => Promise<unknown>) => Promise<boolean>;
  onSuccess?: () => void;
}

export const LiveMicrophoneCloner: React.FC<Props> = ({ sentences, busy, run, onSuccess }) => {
  const { t, lang } = useScopedI18n('core_apps/voice_studio');
  const [name, setName] = useState('');
  const [language, setLanguage] = useState(lang);
  const [consent, setConsent] = useState(false);
  const [mode, setMode] = useState<'mic' | 'file'>('mic');

  // Stati registrazione microfonica
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string>('');
  const [micVolume, setMicVolume] = useState<number>(0);
  const [micError, setMicError] = useState<string>('');

  // Stato file caricato
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const timerRef = useRef<any>(null);
  const chunksRef = useRef<Blob[]>([]);

  const sentence = (sentences[language] ?? sentences.en ?? '').replace('{name}', name.trim() || '…');

  useEffect(() => {
    return () => {
      if (recordedUrl) URL.revokeObjectURL(recordedUrl);
      if (timerRef.current) clearInterval(timerRef.current);
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        void audioContextRef.current.close();
      }
    };
  }, [recordedUrl]);

  const startRecording = async () => {
    setMicError('');
    chunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      const buffer = new Uint8Array(analyser.frequencyBinCount);
      const updateMeter = () => {
        if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') return;
        analyser.getByteFrequencyData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) sum += buffer[i];
        const avg = sum / buffer.length;
        setMicVolume(Math.min(100, Math.round((avg / 128) * 100)));
        requestAnimationFrame(updateMeter);
      };

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const fullBlob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        setRecordedBlob(fullBlob);
        if (recordedUrl) URL.revokeObjectURL(recordedUrl);
        setRecordedUrl(URL.createObjectURL(fullBlob));
        stream.getTracks().forEach((track) => track.stop());
        setMicVolume(0);
      };

      recorder.start(250);
      setIsRecording(true);
      setRecordSeconds(0);
      timerRef.current = setInterval(() => {
        setRecordSeconds((s) => s + 1);
      }, 1000);

      requestAnimationFrame(updateMeter);
    } catch (err: any) {
      setMicError(err?.message || 'Accesso al microfono non consentito o dispositivo non rilevato');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    if (timerRef.current) clearInterval(timerRef.current);
    setIsRecording(false);
  };

  const handleClone = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !consent) return;
    const audioData = mode === 'mic' ? recordedBlob : uploadedFile;
    if (!audioData) return;

    const ok = await run(async () => {
      await cloneVoice(name.trim(), language, audioData, mode === 'mic' ? 'mic_sample.webm' : uploadedFile?.name);
    });

    if (ok) {
      setName('');
      setConsent(false);
      setRecordedBlob(null);
      setUploadedFile(null);
      if (onSuccess) onSuccess();
    }
  };

  const hasAudio = mode === 'mic' ? recordedBlob !== null : uploadedFile !== null;

  return (
    <form onSubmit={handleClone} className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cyan-300 pb-4">
        <div>
          <h4 className="text-base font-bold text-slate-950">{t('clone')}</h4>
          <p className="text-xs text-slate-700">{t('clone_hint')}</p>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Modalità acquisizione audio">
          <button
            type="button"
            aria-pressed={mode === 'mic'}
            onClick={() => setMode('mic')}
            className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${
              mode === 'mic'
                ? 'bg-cyan-500 text-slate-950 font-extrabold shadow-cyan-500/30'
                : 'border border-slate-300 bg-slate-100 text-slate-950 hover:bg-slate-200 hover:text-cyan-800'
            }`}
          >
            <Mic className="h-4 w-4" aria-hidden="true" />
            {t('record_microphone')}
          </button>
          <button
            type="button"
            aria-pressed={mode === 'file'}
            onClick={() => setMode('file')}
            className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${
              mode === 'file'
                ? 'bg-cyan-500 text-slate-950 font-extrabold shadow-cyan-500/30'
                : 'border border-slate-300 bg-slate-100 text-slate-950 hover:bg-slate-200 hover:text-cyan-800'
            }`}
          >
            <Upload className="h-4 w-4" aria-hidden="true" />
            {t('upload_file')}
          </button>
        </div>
      </div>

      {/* Dati Voce */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t('name')}>
          <input
            className={inputClass}
            value={name}
            maxLength={40}
            required
            aria-required="true"
            placeholder="Es. Marco - Voce Personale"
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field label={t('language')}>
          <select
            className={inputClass}
            value={language}
            aria-label={t('language')}
            onChange={(e) => setLanguage(e.target.value)}
          >
            {['it', 'en', 'fr', 'es', 'de', 'pt'].map((val) => (
              <option key={val} value={val}>
                {val.toUpperCase()}
              </option>
            ))}
          </select>
        </Field>
      </div>

      {/* Frase di lettura e consenso ad alto contrasto */}
      <div className="rounded-2xl border border-slate-300 bg-white p-5 shadow-lg">
        <span className="text-xs font-bold text-cyan-700">{t('read_sentence_label')}:</span>
        <blockquote className="mt-2.5 rounded-xl border border-slate-300 bg-white p-4 text-sm font-semibold text-slate-950 shadow-inner">
          «{sentence}»
        </blockquote>
      </div>

      {/* Modalità Registrazione Microfono */}
      {mode === 'mic' ? (
        <div className="rounded-2xl border border-slate-300 bg-white p-5 shadow-lg">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              {!isRecording ? (
                <button
                  type="button"
                  onClick={startRecording}
                  className="flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/25 transition hover:bg-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
                >
                  <Mic className="h-5 w-5" aria-hidden="true" />
                  {t('start_recording')}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={stopRecording}
                  className="flex animate-pulse items-center gap-2 rounded-xl bg-rose-500 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-rose-500/25 transition hover:bg-rose-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
                >
                  <Square className="h-5 w-5" aria-hidden="true" />
                  {t('stop_recording')} ({recordSeconds}s)
                </button>
              )}
            </div>

            {/* VU Meter audio con attributi ARIA */}
            {isRecording && (
              <div
                className="flex items-center gap-3"
                role="meter"
                aria-label="Livello audio microfono"
                aria-valuenow={micVolume}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <span className="text-xs font-semibold text-slate-800">Livello input:</span>
                <div className="h-3.5 w-36 overflow-hidden rounded-full border border-slate-300 bg-white">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-400 via-yellow-400 to-rose-500 transition-all duration-75"
                    style={{ width: `${micVolume}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {micError && (
            <p role="alert" className="mt-3 flex items-center gap-2 text-xs font-semibold text-rose-700">
              <AlertCircle className="h-4 w-4" aria-hidden="true" />
              {micError}
            </p>
          )}

          {recordedBlob && (
            <div className="mt-4 flex flex-wrap items-center gap-3 rounded-xl border border-emerald-300 bg-emerald-950/40 p-4">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" />
              <div className="flex-1 text-xs font-medium text-emerald-900">
                Registrazione vocale pronta ({Math.round(recordedBlob.size / 1024)} KB)
              </div>
              {recordedUrl && (
                <audio controls src={recordedUrl} className="h-8 max-w-xs" />
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-300 bg-white p-5 shadow-lg">
          <label className="block text-xs font-bold text-slate-800">
            {t('audio_file')}
            <input
              className="mt-2 block w-full cursor-pointer text-xs text-slate-700 file:mr-4 file:rounded-xl file:border-0 file:bg-cyan-100 file:px-4 file:py-2 file:text-xs file:font-bold file:text-cyan-800 hover:file:bg-cyan-100"
              type="file"
              accept="audio/*,video/webm"
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null;
                setUploadedFile(f);
              }}
            />
          </label>
        </div>
      )}

      {/* Checkbox Consenso ad Alto Contrasto */}
      <label className="flex items-start gap-3 rounded-xl border border-slate-300 bg-white p-4 text-xs font-medium text-slate-800">
        <input
          type="checkbox"
          className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
        />
        <span>{t('consent')}</span>
      </label>

      {/* Pulsante Invio */}
      <button
        type="submit"
        disabled={busy || !name.trim() || !hasAudio || !consent}
        className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-5 py-2.5 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/25 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Play className="h-4 w-4 fill-slate-950" aria-hidden="true" />
        {t('create_clone_voice')}
      </button>
    </form>
  );
};
