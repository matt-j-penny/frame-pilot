export const FEATURES = { roughCut: 'Rough cut', subtitles: 'Subtitles', motionGraphics: 'Motion graphics', sfx: 'SFX', music: 'Music' };
export function creationSettings(body) {
  const editor = body.editor ?? 'native';
  if (!['native','capcut','palmier','davinci'].includes(editor)) throw new Error('Choose Native, CapCut, Palmier Pro or DaVinci Resolve.');
  const aspectRatio = body.aspectRatio ?? '9:16';
  if (!['9:16', '16:9'].includes(aspectRatio)) throw new Error('Choose 9:16 or 16:9.');
  const features = {};
  for (const key of Object.keys(FEATURES)) {
    const value = body.features?.[key] ?? true;
    if (typeof value !== 'boolean') throw new Error(`Invalid ${FEATURES[key]} setting.`);
    features[key] = value;
  }
  if (!Array.isArray(body.references ?? []) || (body.references ?? []).some(p => typeof p !== 'string')) throw new Error('Invalid reference files.');
  if (!Array.isArray(body.transcriptEdits ?? [])) throw new Error('Invalid transcript instructions.');
  const previewIdeas = body.previewIdeas ?? 0;
  if (![0, 1, 2, 3].includes(previewIdeas)) throw new Error('Choose 1 to 3 ideas per beat.');
  if (previewIdeas && editor !== 'native') throw new Error('Preview before building works with the Native editor only.');
  if (previewIdeas && !features.motionGraphics) throw new Error('Turn on Motion graphics to preview them.');
  return { editor, aspectRatio, features, previewIdeas, inspiration: body.inspiration || null, references: body.references ?? [], transcriptionId: body.transcriptionId || null,
    transcriptEdits: (body.transcriptEdits ?? []).map(edit => {
      const template = edit.template ?? null;
      if (template !== null && (typeof template !== 'string' || !/^[\w.-]+$/.test(template))) throw new Error('Invalid template.');
      if (!Number.isInteger(edit.from) || !Number.isInteger(edit.to) || edit.from < 0 || edit.to < edit.from || typeof (edit.instruction ?? '') !== 'string' || (!template && !edit.instruction?.trim())) throw new Error('Select words and describe the change.');
      return { from: edit.from, to: edit.to, instruction: (edit.instruction ?? '').trim(), ...(template ? { template } : {}) };
    }) };
}
export function settingsPrompt(job) {
  const s = creationSettings(job);
  return `${!job.style ? "No saved style: follow the user brief and supplied references. Any job-local rendering defaults are adjustable and do not impose a named style. Do not apply saved style examples, learning or layout quotas.\n" : ""}Job-specific settings override the default reel workflow and saved style for this job only.
Output: ${s.aspectRatio}, ${s.aspectRatio === '16:9' ? '1920×1080 landscape' : '1080×1920 portrait'}. Ingest reads ui.json and configures this job's canvas. Adapt layouts and typography to fit.
Features: ${Object.entries(s.features).map(([k,v]) => `${FEATURES[k]} ${v ? 'ON' : 'OFF'}`).join(', ')}.
When rough cut is OFF, do not remove fillers, pauses or retakes automatically; explicit transcript removal instructions still apply. reel.py cut preserves the source unless explicit cuts.json ranges are supplied.
Disabled features must not be added. When motion graphics is OFF use talking_head beats, zoom 1 and cut transitions. Enabled features follow the selected style.
Inspiration video (study pacing and visual treatment; do not use as source footage): ${s.inspiration || 'none'}
Reference images/videos (inspect and use where relevant): ${JSON.stringify(s.references)}
Transcript instructions use ORIGINAL source word indices and source times, before rough cuts. Read transcript-edits.json and transcript.json, apply all instructions, and map surviving words through edl.json onto the cut timeline. Do not reinterpret indices as cut-word indices.${s.transcriptEdits.some(e => e.template) ? `
Instructions with a "template" must use that HyperFrames template for exactly that passage (even if motion graphics is OFF): see "HyperFrames templates" in references/edit.md. Fill its copy from the instruction, or from the spoken words when the instruction is empty.` : ''}
${JSON.stringify(s.transcriptEdits)}`;
}
