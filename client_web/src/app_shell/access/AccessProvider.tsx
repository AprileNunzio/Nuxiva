import React, { createContext, useContext, useEffect, useState } from 'react';
import { latestRequest } from '../../shared/http/latestRequest';
import { reportError } from '../../shared/errors/errorBus';

interface Access { ready:boolean;failed:boolean;role:string;nodes:string[];capabilities:string[];can:(permission:string)=>boolean; }
const AccessContext=createContext<Access>({ready:false,failed:false,role:'',nodes:[],capabilities:[],can:()=>false});
export function AccessProvider({user,children}:{user:string;children:React.ReactNode}) {
  const [state,setState]=useState<{user:string;ready:boolean;failed:boolean;role:string;capabilities:string[];nodes:string[]}>({user,ready:false,failed:false,role:'',capabilities:[],nodes:[]});
  useEffect(()=>{
    const request=latestRequest(signal=>fetch('/api/authz/access',{signal,headers:{Accept:'application/json'},cache:'no-store'}).then(response=>{if(!response.ok)throw new Error(`access_http_${response.status}`);return response.json();}).then(data=>{
      if(!data || data.user!==user || typeof data.role!=='string' || !Array.isArray(data.capabilities) || !data.capabilities.every((value:unknown)=>typeof value==='string') || !Array.isArray(data.nodes) || !data.nodes.every((value:unknown)=>typeof value==='string'))throw new Error('invalid_access_contract');
      return data;
    }),data=>setState({user,ready:true,failed:false,role:data.role,capabilities:data.capabilities,nodes:data.nodes}),cause=>{setState({user,ready:true,failed:true,role:'',capabilities:[],nodes:[]});reportError('access_unavailable',cause);});
    request.run();const reload=()=>request.run();window.addEventListener('focus',reload);window.addEventListener('online',reload);
    return()=>{request.dispose();window.removeEventListener('focus',reload);window.removeEventListener('online',reload);};
  },[user]);
  const current=state.user===user?state:{...state,ready:false,capabilities:[],nodes:[]};
  return <AccessContext.Provider value={{...current,can:permission=>current.capabilities.includes('*')||current.capabilities.includes(permission)}}>{children}</AccessContext.Provider>;
}
export const useAccess=()=>useContext(AccessContext);
