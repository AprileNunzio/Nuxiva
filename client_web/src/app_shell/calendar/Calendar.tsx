import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import './calendar.css';
export function Calendar({ now, onClose }: { now: Date; onClose: () => void }) {
  const { t, lang } = useScopedI18n('app_shell/calendar');
  const [month, setMonth] = useState(() => new Date(now.getFullYear(),now.getMonth(),1));
  const [selected, setSelected] = useState(now);
  const first = new Date(month.getFullYear(),month.getMonth(),1);
  const offset = (first.getDay()+6)%7;
  const cells = Array.from({length:42},(_,index)=>new Date(month.getFullYear(),month.getMonth(),index-offset+1));
  return <aside className="os-calendar" aria-label={t('title')}><header><div><strong>{now.toLocaleTimeString(lang,{hour:'2-digit',minute:'2-digit'})}</strong><p>{selected.toLocaleDateString(lang,{weekday:'long',day:'numeric',month:'long',year:'numeric'})}</p></div><button aria-label={t('close')} onClick={onClose}><X /></button></header>
    <nav><button aria-label={t('previous')} onClick={()=>setMonth(new Date(month.getFullYear(),month.getMonth()-1,1))}><ChevronLeft /></button><strong>{month.toLocaleDateString(lang,{month:'long',year:'numeric'})}</strong><button aria-label={t('next')} onClick={()=>setMonth(new Date(month.getFullYear(),month.getMonth()+1,1))}><ChevronRight /></button></nav>
    <div className="os-calendar-grid">{Array.from({length:7},(_,index)=><span key={index}>{new Date(2026,0,5+index).toLocaleDateString(lang,{weekday:'short'})}</span>)}
      {cells.map(date=><button key={date.toISOString()} data-muted={date.getMonth()!==month.getMonth()} aria-pressed={date.toDateString()===selected.toDateString()} aria-current={date.toDateString()===now.toDateString()?'date':undefined} onClick={()=>setSelected(date)}>{date.getDate()}</button>)}
    </div><footer><button onClick={()=>{setMonth(new Date(now.getFullYear(),now.getMonth(),1));setSelected(now);}}>{t('today')}</button></footer>
  </aside>;
}
