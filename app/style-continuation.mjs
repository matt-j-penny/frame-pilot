import { modelConfig } from './agent-runner.mjs';

export function styleContinuation(previous, model, root) {
  if (!previous || previous.status !== 'error') throw new Error('Only failed style runs can be continued.');
  const resume = !!previous.sessionId && modelConfig(model).provider === modelConfig(previous.model).provider;
  const context = (previous.log ?? []).slice(-60).map(entry => entry.text).join('\n');
  const prompt = `Continue the interrupted ${previous.kind === 'refine' ? 'refinement' : 'creation'} of style "${previous.name}".
Read SKILL.md in ${root}, references/create-style.md, and the style schema/checklist first.
Inspect existing styles/${previous.name}/ files, including references, downloaded footage, contact sheets, transcripts, and any unfinished style guide. Reuse completed work; do not download or extract it again unless missing or broken. Finish the analysis and guide, run reel.py style-check ${previous.name} until it passes, and summarize what you completed. Do not run a test edit.
${previous.prompt ? `Original task:\n${previous.prompt}\n` : 'This older run did not save its original prompt. Recover the reference sources and intent from the existing style folder and progress below.'}
Previous progress:\n${context}
Previous failure:\n${previous.summary || 'Run interrupted.'}`;
  return { prompt, resume, sessionId: resume ? previous.sessionId : null };
}
