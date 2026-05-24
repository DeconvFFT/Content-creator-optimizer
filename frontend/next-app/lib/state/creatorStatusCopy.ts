const CREATOR_STATUS_REPLACEMENTS: Array<[RegExp, string]> = [
  [/\bCreator app autopilot\b/gi, "Creator always-on studio"],
  [/\bAutopilot\b/g, "Always-on studio"],
  [/\bautopilot\b/g, "always-on studio"],
  [/\bLocal worker scheduler process\b/g, "Background runner"],
  [/\blocal worker scheduler process\b/g, "background runner"],
  [/\bWorker scheduler process\b/g, "Background runner"],
  [/\bworker scheduler process\b/g, "background runner"],
  [/\bLocal scheduler process\b/g, "Background runner"],
  [/\blocal scheduler process\b/g, "background runner"],
  [/\bLocal scheduler\b/g, "Background runner"],
  [/\blocal scheduler\b/g, "background runner"]
];

export function creatorStatusText(text?: string | null) {
  if (!text) {
    return "";
  }
  return CREATOR_STATUS_REPLACEMENTS.reduce(
    (current, [pattern, replacement]) => current.replace(pattern, replacement),
    text
  );
}

export function appendCreatorStatusDetail(prefix: string, detail?: string | null) {
  const cleanDetail = creatorStatusText(detail).trim();
  return cleanDetail ? `${prefix} ${cleanDetail}` : prefix;
}
