export function dictionaryText(dictionary:Record<string,unknown>|undefined,key:string):string|undefined {
  if(!dictionary)return undefined;
  if(Object.prototype.hasOwnProperty.call(dictionary,key)&&typeof dictionary[key]==='string')return dictionary[key] as string;
  let value:unknown=dictionary;
  for(const part of key.split('.')) {
    if(!value||typeof value!=='object'||!Object.prototype.hasOwnProperty.call(value,part))return undefined;
    value=(value as Record<string,unknown>)[part];
  }
  return typeof value==='string'?value:undefined;
}
