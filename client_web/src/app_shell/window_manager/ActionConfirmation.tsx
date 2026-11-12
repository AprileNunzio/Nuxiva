import React, { useEffect, useRef } from 'react';
export function ActionConfirmation({title,body,cancelLabel,confirmLabel,danger,onCancel,onConfirm}:{title:string;body:string;cancelLabel:string;confirmLabel:string;danger:boolean;onCancel:()=>void;onConfirm:()=>void}) {
  const ref=useRef<HTMLDialogElement>(null);
  useEffect(()=>{const dialog=ref.current;if(dialog&&!dialog.open)dialog.showModal();return()=>dialog?.close();},[]);
  return <dialog ref={ref} className="os-action-dialog" aria-label={title} onCancel={event=>{event.preventDefault();onCancel();}}><strong>{title}</strong><p>{body}</p><div><button autoFocus onClick={onCancel}>{cancelLabel}</button><button data-danger={danger} onClick={onConfirm}>{confirmLabel}</button></div></dialog>;
}
