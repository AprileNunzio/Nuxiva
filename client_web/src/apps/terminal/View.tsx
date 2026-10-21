import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useWindowToolbar } from '../../app_shell/window_manager/WindowContext';
import './style.css';

interface Line { role: 'user' | 'nuxiva' | 'system' | 'error'; text: string }
const endpoints: Record<string,string> = { '/health':'/healthz', '/nodes':'/api/v5/mesh/topology', '/features':'/api/features', '/bus':'/api/bus/modules' };
export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('apps/terminal');
  const [lines, setLines] = useState<Line[]>([]);
  const [command, setCommand] = useState('');
  const [busy, setBusy] = useState(false);
  const request = useRef<AbortController | null>(null);
  const history = useRef<string[]>([]);
  const historyIndex = useRef(0);
  const output = useRef<HTMLDivElement>(null);
  const append = useCallback((role: Line['role'], text: string) => setLines(items=>[...items,{role,text}].slice(-150)),[]);
  useEffect(()=>{ if (output.current) output.current.scrollTop=output.current.scrollHeight; },[lines,busy]);
  useEffect(()=>()=>request.current?.abort(),[]);
  const run = useCallback(async (input: string) => {
    const text=input.trim(); if (!text) return;
    if (text === '/clear') { setLines([]); return; }
    if (text === '/stop') { request.current?.abort(); return; }
    if (request.current) return;
    append('user',text);history.current.push(text);historyIndex.current=history.current.length;
    if (text === '/help') { append('system',t('help')); return; }
    if (text.startsWith('/') && !endpoints[text]) { append('error',t('unknown'));return; }
    const controller=new AbortController();request.current=controller;setBusy(true);
    const timeout=setTimeout(()=>controller.abort(),240000);
    try {
      const diagnostic=endpoints[text];
      const response=await fetch(diagnostic || '/api/assistant/chat', diagnostic ? {signal:controller.signal,cache:'no-store'} : {
        method:'POST',headers:{'Content-Type':'application/json','X-Nuxiva-Request':'1'},body:JSON.stringify({text,lang}),signal:controller.signal,
      });
      const data=await response.json().catch(()=>({}));
      if (!response.ok) throw new Error(`${response.status} · ${typeof data.detail==='string'?data.detail:t('failed')}`);
      append(diagnostic?'system':'nuxiva',diagnostic ? JSON.stringify(data,null,2).slice(0,30000) : String(data.reply || data.speech_output || t('empty')));
    } catch (error) { append('error',controller.signal.aborted?t('cancelled'):error instanceof Error?error.message:t('failed')); }
    finally { clearTimeout(timeout);if(request.current===controller)request.current=null;setBusy(false); }
  },[append,lang,t]);
  useWindowToolbar(useCallback((id: string)=>{ void run(`/${id}`); },[run]));
  return <div className="nuxiva-terminal"><header><span className="terminal-status" /><strong>Nuxiva by NunzioTech</strong><span>{t('description')}</span></header>
    <div className="terminal-output" ref={output} role="log" aria-live="polite"><p className="terminal-welcome">{t('welcome')}</p>{lines.map((line,index)=><article className={`terminal-line terminal-${line.role}`} key={index}><span>{line.role==='user'?'›':line.role==='nuxiva'?'N':line.role==='error'?'!':'·'}</span><pre>{line.text}</pre></article>)}{busy && <p className="terminal-pending" role="status">{t('working')}</p>}</div>
    <form onSubmit={event=>{event.preventDefault();const text=command;setCommand('');void run(text);}}><span>›</span><input value={command} aria-label={t('input')} placeholder={t('input')} maxLength={4000} autoComplete="off" spellCheck={false} onChange={event=>setCommand(event.target.value)} onKeyDown={event=>{
      if(event.key==='ArrowUp'){event.preventDefault();historyIndex.current=Math.max(0,historyIndex.current-1);setCommand(history.current[historyIndex.current]||'');}
      if(event.key==='ArrowDown'){event.preventDefault();historyIndex.current=Math.min(history.current.length,historyIndex.current+1);setCommand(history.current[historyIndex.current]||'');}
    }}/><button disabled={busy || !command.trim()}>{t('send')}</button></form>
  </div>;
};
