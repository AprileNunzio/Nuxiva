export async function download(url: string, filename: string) {
  const response=await fetch(url,{headers:{Accept:'application/octet-stream'}});
  if(!response.ok)throw new Error(`download_http_${response.status}`);
  const objectUrl=URL.createObjectURL(await response.blob());
  const anchor=document.createElement('a');anchor.href=objectUrl;anchor.download=filename;anchor.click();
  window.setTimeout(()=>URL.revokeObjectURL(objectUrl),60000);
}
