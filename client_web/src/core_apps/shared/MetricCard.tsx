import React from 'react';
import './metrics.css';

export function MetricCard({label,value,icon,tone='blue'}:{label:string;value:React.ReactNode;icon:React.ReactNode;tone?:'blue'|'red'|'amber'|'violet'}) {
  return <div className="os-metric" data-tone={tone}><span className="os-metric-icon" aria-hidden="true">{icon}</span><div><span className="os-metric-label">{label}</span><strong>{value}</strong></div></div>;
}
