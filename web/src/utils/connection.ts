interface NetworkInformation {
  saveData?: boolean;
  effectiveType?: string;
}

const SLOW_CONNECTION_TYPES = ["slow-2g", "2g", "3g"];

/** True when the user asked to save data or the connection is slow; false when the browser reports nothing. */
export function isConstrainedConnection(): boolean {
  const connection = (navigator as Navigator & { connection?: NetworkInformation }).connection;
  if (!connection) return false;
  return connection.saveData === true || SLOW_CONNECTION_TYPES.includes(connection.effectiveType ?? "");
}
