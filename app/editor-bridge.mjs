// Agent-side CLI. Connections stay in the app server, outside model-specific MCP settings.
const [job, action, tool, json] = process.argv.slice(2);
const url=process.env.REEL_RENDER_SERVICE_URL, token=process.env.REEL_RENDER_TOKEN;
if(!url || !token || !job || !['tools','call','capcut'].includes(action)) {
  console.error('Use inside an editor job: node app/editor-bridge.mjs <job-id> tools | call <tool> <JSON> | capcut <JSON array>');process.exit(1);
}
try {
  const body=action==='call'?{action,tool,arguments:JSON.parse(json || '{}')}:action==='capcut'?{action,args:JSON.parse(tool || '[]')}:{action};
  const response=await fetch(`${url}/api/jobs/${encodeURIComponent(job)}/editor-tools`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},body:JSON.stringify(body)});
  const result=await response.json();if(!response.ok)throw new Error(result.error || 'Editor operation failed.');console.log(JSON.stringify(result,null,2));
}catch(error){console.error(error.message);process.exitCode=1;}
