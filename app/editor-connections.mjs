import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { spawnTask, stopTask } from './process-control.mjs';
const APP = path.dirname(fileURLToPath(import.meta.url)), ROOT = path.dirname(APP);
const FILE = path.join(APP, 'editor-connections.json');
export const EDITORS = [{id:'native',label:'Native'}, {id:'capcut',label:'CapCut'}, {id:'palmier',label:'Palmier Pro'}, {id:'davinci',label:'DaVinci Resolve'}];
const read = file => { try { return JSON.parse(fs.readFileSync(file,'utf8')); } catch { return {}; } };
function discovery() {
  const claude = read(path.join(os.homedir(),'.claude.json'));
  let servers = {...claude.mcpServers};
  const scopes = Object.keys(claude.projects || {}).filter(p => ROOT === p || ROOT.startsWith(p + path.sep)).sort((a,b)=>a.length-b.length);
  for(const scope of scopes) servers = {...servers, ...claude.projects[scope].mcpServers};
  servers = {...servers,...read(path.join(ROOT,'.mcp.json')).mcpServers};
  const palmier = servers['palmier-pro'], davinci = servers['davinci-resolve'];
  const capcutCandidates = [path.join(path.dirname(ROOT),'capcut-video-editor-use/capcut-bridge.py'),path.join(path.dirname(ROOT),'Edit Pipeline/lanes/capcut/capcut-bridge.py')];
  return {
    native: {},
    capcut: { type:'capcut', command:'uv', bridge:capcutCandidates.find(p=>fs.existsSync(p)) || '' },
    palmier: palmier || {type:'http',url:'http://127.0.0.1:19789/mcp'},
    davinci: davinci || {type:'stdio',command:'',args:[]},
  };
}
export function connections() { const defaults=discovery(), saved=read(FILE); return Object.fromEntries(EDITORS.map(e=>[e.id,{...defaults[e.id],...saved[e.id]}])); }
const states = new Map(), clients = new Map();
export function editorStatuses() {
  const configs = connections();
  return EDITORS.map(editor => {
    const c=configs[editor.id], state=states.get(editor.id);
    return {...editor, ready:editor.id==='native' || state?.ready === true, status:editor.id==='native'?'ready':state?.status || 'unchecked', message:editor.id==='native'?'Built-in renderer':state?.message || 'Check connection in Setup',
      config:{type:c.type || (c.url?'http':'stdio'),url:c.url || '',command:c.command || '',args:c.args || [],bridge:c.bridge || ''}};
  });
}
export function saveConnection(id, value) {
  if (!EDITORS.some(e=>e.id===id) || id==='native') throw new Error('Choose an external editor.');
  let config;
  if(id==='capcut') {
    if(typeof value.bridge!=='string' || !path.isAbsolute(value.bridge) || !fs.statSync(value.bridge).isFile()) throw new Error('Choose an existing absolute CapCut bridge path.');
    config={type:'capcut',bridge:value.bridge,command:value.command || 'uv'};
  } else if(value.type==='http') {
    const url=new URL(value.url);
    if(!['http:','https:'].includes(url.protocol) || !['127.0.0.1','localhost','[::1]'].includes(url.hostname) || url.username || url.password) throw new Error('Use a local MCP URL without credentials.');
    config={type:'http',url:url.href};
  } else {
    if(typeof value.command!=='string' || !value.command.trim() || !Array.isArray(value.args) || value.args.some(v=>typeof v!=='string')) throw new Error('Enter an MCP command and a JSON array of arguments.');
    config={type:'stdio',command:value.command.trim(),args:value.args};
  }
  const saved=read(FILE); saved[id]=config;
  fs.writeFileSync(FILE,JSON.stringify(saved,null,2),{mode:0o600});
  clients.get(id)?.close(); clients.delete(id); states.delete(id);
}
function unwrap(result) {
  if(result?.isError) throw new Error(result.content?.filter(c=>c.type==='text').map(c=>c.text).join('\n') || 'Editor tool failed.');
  if(result?.structuredContent?.success===false || result?.structuredContent?.error)throw new Error(JSON.stringify(result.structuredContent));
  for(const item of result?.content || []) if(item.type==='text') {
    try { const value=JSON.parse(item.text); if(value?.success===false || value?.error) throw new Error(typeof value.error==='string'?value.error:JSON.stringify(value)); } catch(error) { if(!(error instanceof SyntaxError)) throw error; }
  }
  return result;
}
class MCPClient {
  constructor(config) {this.config=config;this.next=0;this.pending=new Map();this.session=null;this.protocol='2025-03-26';this.closed=false;}
  async start() {
    if(!this.config.url) {
      if(!this.config.command) throw new Error('Configure the local MCP server in Setup.');
      this.child=spawnTask(this.config.command,this.config.args || [],{cwd:ROOT,env:{...process.env,...this.config.env},stdio:['pipe','pipe','pipe']});
      this.child.stdin.on('error',()=>{});let buffer='',error='';
      this.child.stderr.on('data',chunk=>{error=(error+chunk).slice(-1500);});
      this.child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{this.receive(JSON.parse(line));}catch{}}});
      const fail=message=>{this.closed=true;for(const p of this.pending.values())p.reject(new Error(message));this.pending.clear();};
      this.child.on('error',e=>fail(e.message));this.child.on('close',()=>fail(error || 'Editor bridge closed.'));
    }
    const result=await this.request('initialize',{protocolVersion:this.protocol,capabilities:{},clientInfo:{name:'video-editor',version:'1.0'}});
    this.protocol=result.protocolVersion || this.protocol;
    await this.notify('notifications/initialized',{});
    return this;
  }
  receive(message) {
    const pending=this.pending.get(message.id);
    if(pending){this.pending.delete(message.id);message.error?pending.reject(new Error(message.error.message)):pending.resolve(message.result);}
    else if(message.id != null && this.child) this.child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:message.id,error:{code:-32601,message:'Client requests are unsupported'}})+'\n');
  }
  async http(message) {
    const timeout = message.method === 'tools/call' ? 180000 : 15000;
    const response=await fetch(this.config.url,{method:'POST',redirect:'error',headers:{'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':this.protocol,...this.config.headers,...(this.session?{'Mcp-Session-Id':this.session}:{})},body:JSON.stringify(message),signal:AbortSignal.timeout(timeout)});
    if(!response.ok) throw new Error(`Editor connection returned HTTP ${response.status}. Open the editor and check Setup.`);
    this.session=response.headers.get('mcp-session-id') || this.session;
    if(message.id==null || response.status===202){await response.body?.cancel();return;}
    if(response.headers.get('content-type')?.includes('text/event-stream')) {
      const reader=response.body.getReader(), decoder=new TextDecoder();let buffer='';
      try {while(true){const part=await reader.read();if(part.done)break;buffer+=decoder.decode(part.value,{stream:true}).replace(/\r\n/g,'\n');let end;while((end=buffer.indexOf('\n\n'))>=0){const event=buffer.slice(0,end);buffer=buffer.slice(end+2);const data=event.split('\n').filter(l=>l.startsWith('data:')).map(l=>l.slice(5).trimStart()).join('\n');if(!data)continue;let parsed;try{parsed=JSON.parse(data);}catch{continue;}if(parsed.id===message.id){if(parsed.error)throw new Error(parsed.error.message);return parsed.result;}}}}finally{await reader.cancel();}
      throw new Error('Editor stream ended without a result.');
    }
    const parsed=await response.json();if(parsed.error)throw new Error(parsed.error.message);return parsed.result;
  }
  async request(method,params,jobId=null) {
    const id=++this.next,message={jsonrpc:'2.0',id,method,params};
    if(this.config.url) {
      this.pending.set(id,{jobId,reject:()=>{}});
      try{return await this.http(message);}finally{this.pending.delete(id);}
    }
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{this.pending.delete(id);reject(new Error('Editor request timed out.'));},180000);
      this.pending.set(id,{jobId,resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}});
      this.child.stdin.write(JSON.stringify(message)+'\n');
    });
  }
  async notify(method,params) {const message={jsonrpc:'2.0',method,params};if(this.config.url)return this.http(message);this.child?.stdin.write(JSON.stringify(message)+'\n');}
  async tools() {const tools=[];let cursor;do{const result=await this.request('tools/list',cursor?{cursor}:{});tools.push(...result.tools || []);cursor=result.nextCursor;}while(cursor);return tools;}
  cancel(jobId) {for(const [id,p] of this.pending)if(p.jobId===jobId)this.notify('notifications/cancelled',{requestId:id,reason:'Cancelled by the user'}).catch(()=>{});}
  close(){this.closed=true;stopTask(this.child);if(this.config.url && this.session)fetch(this.config.url,{method:'DELETE',headers:{...this.config.headers,'Mcp-Session-Id':this.session},signal:AbortSignal.timeout(3000)}).catch(()=>{});}
}
export async function editorClient(id) {
  let client=clients.get(id);if(client?.closed){clients.delete(id);client=null;}
  if(!client){client=new MCPClient(connections()[id]);clients.set(id,client);client.ready=client.start();try{await client.ready;}catch(e){client.close();clients.delete(id);throw e;}}
  await client.ready;
  return client;
}
export async function callEditor(id, tool, args, jobId) {return unwrap(await (await editorClient(id)).request('tools/call',{name:tool,arguments:args},jobId));}
export function cancelEditorJob(id,jobId){clients.get(id)?.cancel(jobId);}
export async function checkEditor(id) {
  if(id==='native')return editorStatuses()[0];
  try {
    if(id==='capcut') {
      const config=connections().capcut;
      if(!config.bridge || !fs.existsSync(config.bridge))throw new Error('Set the CapCut bridge path.');
      const app=[path.join('/Applications','CapCut.app'),path.join(os.homedir(),'Applications/CapCut.app')].some(p=>fs.existsSync(p));
      if(!app)throw new Error('Install CapCut desktop.');
      await new Promise((resolve,reject)=>{const child=spawnTask(config.command || 'uv',['--version'],{stdio:'ignore'});const timer=setTimeout(()=>{stopTask(child);reject(new Error('uv check timed out.'));},5000);child.on('error',e=>{clearTimeout(timer);reject(e);});child.on('close',code=>{clearTimeout(timer);code===0?resolve():reject(new Error('Install uv to run the CapCut bridge.'));});});
    } else {
      const tools=await (await editorClient(id)).tools();
      const tool=id==='palmier'?tools.find(t=>t.name.endsWith('manage_project')):tools.find(t=>t.name==='resolve_control');
      if(!tool)throw new Error('Expected editor tools are unavailable on this connection.');
      await callEditor(id,tool.name,id==='palmier'?{action:'list'}:{action:'get_version'},null);
    }
    states.set(id,{ready:true,status:id==='capcut'?'configured':'ready',message:id==='capcut'?'Bridge configured. CapCut needs macOS Accessibility permission for live editing and export.':'Connected to editor'});
  }catch(error){states.set(id,{ready:false,status:'error',message:error.message});}
  return editorStatuses().find(e=>e.id===id);
}
export async function requireEditor(id) {
  if(!EDITORS.some(e=>e.id===id))throw Object.assign(new Error('Choose a supported editor.'),{status:400});
  const editor=await checkEditor(id);if(!editor.ready)throw Object.assign(new Error(`${editor.label}: ${editor.message}`),{status:409});return editor;
}
export function editorPrompt(job) {
  if(!job.editor || job.editor==='native')return '';
  return `OUTPUT EDITOR: ${EDITORS.find(e=>e.id===job.editor)?.label}. This overrides the native Remotion build and render stages.
Create or revise a genuinely editable timeline in this editor, using source clips and separate graphics, captions, music and SFX layers as appropriate. Do not import a flattened final video as the whole project. Preserve existing manual edits during revisions. Do not fall back to Native when disconnected.
Use the authenticated bridge CLI from this folder: node app/editor-bridge.mjs ${job.id} tools; node app/editor-bridge.mjs ${job.id} call <tool-name> '<JSON arguments>'. Tools include their input schemas. Consult them before calling. All paths must be absolute. The bridge works with either Claude or Codex without modifying global MCP configuration.
${job.editor==='capcut'?`CapCut commands: node app/editor-bridge.mjs ${job.id} capcut '<JSON array of bridge arguments>'. Available commands: replay, add-overlay, add-text, graphics, transform, keyframe, clear-keyframes, remove, open, export, state, shot, ls, save. To create this job use ["replay","${job.id}","--name","${job.id}"]. The adapter converts edl.json into the bridge format and copies the bridge with the selected canvas. Do not replay an existing hand-edited draft; revise it with additive commands. The bridge handles closing/reopening CapCut for structural writes. Read the configured bridge README if needed.`:''}
Read SKILL.md and references/edit.md for ingestion, transcription, cuts, planning and verification, but carry out editing and export in the selected editor. Reuse job-local transcripts and map original transcript selections onto the cut timeline.
Save project details to editor-project.json: {"editor":"${job.editor}","projectId":"...","projectName":"...","projectPath":"absolute local path when available","verified":true}. Only set verified after reading back the actual editor timeline. Recheck and update this record for every revision.
Export an MP4 from the selected editor to this job's output/final.mp4 so the app can preview it; then run reel.py verify. A native preview alone is not a completed external-editor job. End with a concise summary and project location.`;
}
