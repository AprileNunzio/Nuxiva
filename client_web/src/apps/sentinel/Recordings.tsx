import React from 'react';
import { AskRecordings } from './AskRecordings';
import { RecordingPolicy } from './RecordingPolicy';
import { PersonRecordings } from './PersonRecordings';
import type { SentinelModel } from './useSentinel';

export function Recordings({model}:{model:SentinelModel}) {
  return <div className="sentinel-nvr"><AskRecordings model={model}/></div>;
}

export function RecordingPrivacy({model}:{model:SentinelModel}) {
  return <div className="sentinel-nvr"><RecordingPolicy model={model}/><PersonRecordings model={model}/></div>;
}
