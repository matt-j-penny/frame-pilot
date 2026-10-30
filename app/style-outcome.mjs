// Recover only a transport failure after an explicit completion message and validated new output.
export function styleOutcome({ ok, summary, changed, validated, lastMessage = '' }) {
  const connectionFailure = /stream disconnected|websocket closed|Reconnecting\.\.\./i.test(summary);
  const reportedComplete = /^(completed|finished)\b/i.test(lastMessage.trim());
  if (!ok && connectionFailure && reportedComplete && changed && validated)
    return { status: 'done', summary: lastMessage, warning: `Style saved and validated; the connection interrupted final run confirmation. ${summary}` };
  return { status: ok && changed ? 'done' : 'error',
    summary: ok && !changed ? `No changes were saved. ${summary}` : summary };
}
