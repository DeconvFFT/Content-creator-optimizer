import type { UUID } from "../api/types";

export const ARTIFACT_JUMP_EVENT = "agentstudio:artifact-jump";

export function artifactDomId(artifactId: UUID) {
  return `artifact-${artifactId}`;
}

export function artifactHref(artifactId: UUID) {
  return `#${artifactDomId(artifactId)}`;
}

export function artifactIdFromHash(hash: string) {
  const prefix = "#artifact-";
  if (!hash.startsWith(prefix)) {
    return null;
  }
  const artifactId = hash.slice(prefix.length);
  try {
    return artifactId.length > 0 ? decodeURIComponent(artifactId) : null;
  } catch {
    return null;
  }
}

export function dispatchArtifactJump(artifactId: UUID) {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent(ARTIFACT_JUMP_EVENT, {
      detail: { artifactId }
    })
  );
}
