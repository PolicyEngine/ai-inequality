export function policyEngineVersion(metadata) {
  return metadata.policyengine_version ?? "version unavailable";
}

export function policyEngineLabel(metadata) {
  return `PolicyEngine ${policyEngineVersion(metadata)}`;
}
