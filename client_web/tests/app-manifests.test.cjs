const { readdirSync, readFileSync, existsSync } = require('node:fs');
const { join, resolve } = require('node:path');
const assert = require('node:assert/strict');
const root = resolve(__dirname,'../src');
let count=0;
function* appFolders(folder) {
  if(existsSync(join(folder,'manifest.json'))&&existsSync(join(folder,'View.tsx')))yield folder;
  for(const entry of readdirSync(folder,{withFileTypes:true}))if(entry.isDirectory())yield* appFolders(join(folder,entry.name));
}
for(const folder of appFolders(root)) {
  const path=join(folder,'manifest.json');
  const scope=folder.slice(root.length+1).replaceAll('\\','/');
  const directory={name:scope.split('/').pop()};
  const manifest=JSON.parse(readFileSync(path,'utf8'));
  assert.equal(manifest.id,directory.name,path);
  assert.equal(manifest.scope,scope,path);
  assert.ok(typeof manifest.category==='string' && manifest.category.length>0,path);
  assert.ok(existsSync(join(folder,'View.tsx')),path);
  assert.equal(manifest.icon3d,'./icon.png',path);
  const icon=readFileSync(join(folder,'icon.png'));
  assert.equal(icon.subarray(1,4).toString(),'PNG',path);
  assert.ok(icon.readUInt32BE(16)>=192 && icon.readUInt32BE(20)>=192,path);
  assert.equal(manifest.icon3dSource.technique,'3d',path);
  assert.ok(manifest.window.defaultWidth>=manifest.window.minWidth,path);
  const locales=readdirSync(join(folder,'language')).filter(name=>name.endsWith('.json')).map(name=>name.slice(0,-5));
  assert.ok(locales.length>0,path);
  for(const locale of locales) {
    const dictionary=JSON.parse(readFileSync(join(folder,'language',`${locale}.json`),'utf8'));
    const own=dictionary.dictionary||dictionary;
    const shellPath=join(root,'app_shell/language',`${locale}.json`);
    const shell=JSON.parse(readFileSync(existsSync(shellPath)?shellPath:join(root,'app_shell/language/en.json'),'utf8'));
    const label=key=>own[key]||key.split('.').reduce((value,part)=>value&&value[part],own)||(shell.dictionary||shell)[key];
    for(const item of [...(manifest.ui?.tabs||[]),...(manifest.ui?.actions||[])])assert.ok(label(item.labelKey),`${path}: ${locale} ${item.labelKey}`);
    if(manifest.ui?.searchPlaceholderKey)assert.ok(label(manifest.ui.searchPlaceholderKey),`${path}: ${locale} search`);
    assert.ok(own.title,`${path}: ${locale} title`);
    for(const bar of manifest.toolbars||[]) for(const item of bar.items) {
      assert.ok(['action','button','search','segmented'].includes(item.type),path);
      for(const key of [item.labelKey,item.placeholderKey].filter(Boolean)) assert.ok(own[key]||(shell.dictionary||shell)[key],`${path}: ${locale} ${key}`);
    }
  }
  count++;
}
assert.ok(count>0);
console.log(`${count} autonomous app manifests: categories, views, 3D assets, dimensions and discovered local dictionaries passed.`);

// Feature plugins must own their assets too; no fixed registry size.
const featureRoot=resolve(__dirname,'../../installer_wizard/features');
for(const folder of readdirSync(featureRoot)) {
 const manifestPath=join(featureRoot,folder,'feature.json');
 if(!existsSync(manifestPath))continue;
 const feature=JSON.parse(readFileSync(manifestPath,'utf8'));
 assert.equal(feature.icon3d,'./icon.png',manifestPath);
 const ownIcon=join(featureRoot,folder,'icon.png');
 assert.ok(existsSync(ownIcon),manifestPath);
 assert.equal(readFileSync(ownIcon).subarray(0,8).toString('hex'),'89504e470d0a1a0a',manifestPath);
}
console.log('Discovered feature manifests own valid local PNG icons.');
