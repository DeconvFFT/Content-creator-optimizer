export function compactId(id: string) {
  return `${id.slice(0, 8)}...${id.slice(-4)}`;
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function artifactBody(content: Record<string, unknown>) {
  const preferredKeys = ["body", "draft", "text", "script", "article", "content"];
  for (const key of preferredKeys) {
    const value = content[key];
    if (typeof value === "string" && value.trim().length > 0) {
      return value;
    }
  }
  return JSON.stringify(content, null, 2);
}

export function statusLabel(status: string) {
  return status.replace(/[_-]+/g, " ");
}
