const {readFileSync}=require('node:fs'),{resolve}=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript');
const moduleContext={exports:{}};
vm.runInNewContext(ts.transpileModule(readFileSync(resolve(__dirname,'../src/app_shell/taskbarGroups.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,{exports:moduleContext.exports,module:moduleContext});
const windows=[{id:'one',appId:'updater',z:1,minimized:false},{id:'two',appId:'updater',z:3,minimized:true},{id:'three',appId:'terminal',z:2,minimized:true}];
const groups=moduleContext.exports.taskbarGroups(windows,['updater','network']);
assert.equal(groups.length,3);assert.equal(groups.filter(group=>group.appId==='updater').length,1);
assert.equal(groups[0].entries.length,2);assert.equal(groups[0].entries[0].id,'two');assert.equal(groups[0].background,false);
assert.equal(groups.find(group=>group.appId==='terminal').background,true);assert.equal(groups.find(group=>group.appId==='network').background,false);
assert.equal(windows[0].id,'one');
console.log('Taskbar grouping: pinned deduplication, multiple windows, minimized groups and stable source passed.');


const runningOnly=moduleContext.exports.taskbarGroups(windows,[]);
assert.equal(runningOnly.length,2);
assert.ok(runningOnly.every(group=>group.entries.length>0));
assert.ok(runningOnly.some(group=>group.appId==='terminal' && group.background));
