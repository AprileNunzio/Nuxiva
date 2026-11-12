const {readFileSync}=require('node:fs');
const {resolve}=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const assert=require('node:assert/strict');
function load(path) {
 const module={exports:{}};
 vm.runInNewContext(ts.transpileModule(readFileSync(resolve(__dirname,'../src',path),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{module,exports:module.exports});
 return module.exports;
}
const {normalizeManifest}=load('app_shell/window_manager/normalizeManifest.ts');
const {dictionaryText}=load('shared/i18n/dictionaryText.ts');
const manifest={id:'logs',capabilities:['logs.read'],window:{defaultWidth:1100,minWidth:480},ui:{searchable:true,tabs:[{id:'records',labelKey:'logs.records'}],actions:[{id:'export',labelKey:'logs.export',permissions:['logs.export']}]}};
const normalized=normalizeManifest(manifest,'core_apps/logs');
assert.equal(normalized.window.units,'px');
assert.equal(normalized.navigation[0].id,'records');
assert.equal(normalized.toolbars[0].items[0].type,'search');
assert.equal(normalized.toolbars[0].items[1].permissions[0],'logs.export');
assert.equal(manifest.window.units,undefined);
assert.equal(normalizeManifest({id:'legacy',toolbars:[]},'core_apps/legacy').window.units,'legacy');
for(const invalid of [null,{id:'bad',ui:null},{id:'bad',ui:{tabs:{}}},{id:'bad',ui:{actions:[null]}},{id:'bad',capabilities:'logs.read'},{id:'bad',ui:{actions:[{id:'x',labelKey:'x',permissions:'*'}]}}])assert.equal(normalizeManifest(invalid,'scope'),null);
assert.equal(dictionaryText({'logs.export':'Flat'},'logs.export'),'Flat');
assert.equal(dictionaryText({logs:{export:'Nested'}},'logs.export'),'Nested');
assert.equal(dictionaryText({logs:{export:{}}},'logs.export'),undefined);
assert.equal(dictionaryText({},'constructor.name'),undefined);
assert.equal(dictionaryText(Object.create({inherited:'hidden'}),'inherited'),undefined);
console.log('Declarative manifest compatibility, invalid contracts, capability shapes and nested own dictionaries passed.');
