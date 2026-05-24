export async function settleVoiceSetupFanout<T extends readonly unknown[]>(
  tasks: { [K in keyof T]: Promise<T[K]> }
): Promise<T> {
  const results = await Promise.allSettled(tasks);
  const rejected = results.find(
    (result): result is PromiseRejectedResult => result.status === "rejected"
  );
  if (rejected) {
    throw rejected.reason;
  }
  return results.map((result) => (result as PromiseFulfilledResult<unknown>).value) as unknown as T;
}
