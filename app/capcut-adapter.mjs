import fs from 'node:fs';
import path from 'node:path';
import { spawnTask } from './process-control.mjs';
export function capcutCommand(config, job, jobDir, args) {
  const allowed=['replay','add-overlay','add-text','graphics','transform','keyframe','clear-keyframes','remove','open','export','state','shot','ls','save','seek','playhead','clips','dump'];
  if(!Array.isArray(args) || args.some(v=>typeof v!=='string') || !allowed.includes(args[0]))throw new Error('Choose a supported CapCut bridge command.');
  const folder=path.join(jobDir,'editor-tools'), script=path.join(folder,'capcut/capcut-bridge.py');
  fs.mkdirSync(path.dirname(script),{recursive:true});
  const width=job.aspectRatio==='16:9'?1920:1080,height=job.aspectRatio==='16:9'?1080:1920;
  const code=fs.readFileSync(config.bridge,'utf8').replace('build_draft(name, local_raw, cuts, 1920, 1080)',`build_draft(name, local_raw, cuts, ${width}, ${height})`);
  fs.writeFileSync(script,code);
  if(args[0]==='replay') {
    if(args[1]!==job.id)throw new Error('Replay this job id only.');
    const edl=JSON.parse(fs.readFileSync(path.join(jobDir,'edl.json'),'utf8'));
    const compat=path.join(folder,'projects',job.id), raw=path.basename(job.source);
    fs.mkdirSync(path.join(compat,'raw'),{recursive:true});fs.mkdirSync(path.join(compat,'transcript'),{recursive:true});
    const link=path.join(compat,'raw',raw);if(!fs.existsSync(link))fs.symlinkSync(job.source,link);
    fs.writeFileSync(path.join(compat,'transcript/cuts.json'),JSON.stringify({segments:edl.segments.map(s=>({clip:raw,start:s.src_start,end:s.src_end}))},null,2));
  }
  return spawnTask(config.command || 'uv',['run',script,...args],{cwd:jobDir,stdio:['ignore','pipe','pipe']});
}
