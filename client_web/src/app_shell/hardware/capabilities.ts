export type HardwareCapabilities = Readonly<Record<string, readonly string[]>>;

export function parseHardwareCapabilities(value: unknown): HardwareCapabilities {
  if (!value || typeof value !== 'object' || !('capabilities' in value)) {
    throw new Error('invalid_hardware_capabilities');
  }
  const capabilities = value.capabilities;
  if (!capabilities || typeof capabilities !== 'object' || Array.isArray(capabilities)) {
    throw new Error('invalid_hardware_capabilities');
  }
  const result: Record<string, readonly string[]> = Object.create(null);
  for (const [name, devices] of Object.entries(capabilities)) {
    if (!/^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)+$/.test(name) || !Array.isArray(devices)
      || devices.length > 256 || devices.some(device => typeof device !== 'string' || !device || device.length > 256)) {
      throw new Error('invalid_hardware_capabilities');
    }
    result[name] = [...devices];
  }
  return result;
}
