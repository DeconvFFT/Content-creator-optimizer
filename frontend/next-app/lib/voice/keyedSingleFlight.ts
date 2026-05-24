export type KeyedSingleFlightResult<T> = {
  promise: Promise<T>;
  started: boolean;
};

export function startKeyedSingleFlight<T>(
  inFlight: Map<string, Promise<T>>,
  key: string,
  start: () => Promise<T>
): KeyedSingleFlightResult<T> {
  const existing = inFlight.get(key);
  if (existing) {
    return { promise: existing, started: false };
  }
  const promise = start().finally(() => {
    inFlight.delete(key);
  });
  inFlight.set(key, promise);
  return { promise, started: true };
}
