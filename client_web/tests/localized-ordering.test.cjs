const {readFileSync}=require('node:fs');
const {resolve}=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const ts=require('typescript');
const moduleContext={exports:{}};
const code=ts.transpileModule(readFileSync(resolve(__dirname,'../src/shared/i18n/sortByLocalizedLabel.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
vm.runInNewContext(code,{exports:moduleContext.exports,module:moduleContext,Intl});
const {sortByLocalizedLabel}=moduleContext.exports;
const apps=[{it:'Rete',en:'Network',fr:'Réseau',es:'Red'},{it:'Calendario',en:'Calendar',fr:'Calendrier',es:'Calendario'},{it:'Archivio 10',en:'Archive 10',fr:'Archive 10',es:'Archivo 10'},{it:'Archivio 2',en:'Archive 2',fr:'Archive 2',es:'Archivo 2'}];
for(const locale of Object.keys(apps[0])) {
 const sorted=sortByLocalizedLabel(apps,locale,app=>app[locale]);
 assert.equal(sorted.length,apps.length);
 assert.ok(sorted.indexOf(apps[3])<sorted.indexOf(apps[2]),`${locale}: numeric labels`);
 for(let i=1;i<sorted.length;i++)assert.ok(new Intl.Collator(locale,{numeric:true,sensitivity:'base'}).compare(sorted[i-1][locale],sorted[i][locale])<=0,locale);
 assert.equal(apps[0].en,'Network','source registry is not mutated');
}
console.log('Localized alphabetical/numeric ordering and registry immutability passed.');
