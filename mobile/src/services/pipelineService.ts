declare const process: {
  env?: Record<string, string | undefined>;
};

const BASE_URL =
  (typeof process !== 'undefined' && process.env?.EXPO_PUBLIC_ALERTS_BASE_URL) ??
  'https://api.orbitaltrust.io/v1';

export interface PipelineStatus {
  running: boolean;
  payload_count: number;
  last_frame: number;
  error: string | null;
}

export async function startPipeline(
  video = 'queimada.mp4',
  areaId = 'BR-MT-001',
  every = 30,
): Promise<PipelineStatus> {
  const response = await fetch(`${BASE_URL}/pipeline/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video, area_id: areaId, every }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Falha ao iniciar pipeline: ${detail}`);
  }

  return response.json() as Promise<PipelineStatus>;
}

export async function stopPipeline(): Promise<void> {
  await fetch(`${BASE_URL}/pipeline/stop`, { method: 'POST' });
}

export async function getPipelineStatus(): Promise<PipelineStatus> {
  const response = await fetch(`${BASE_URL}/pipeline/status`);

  if (!response.ok) {
    throw new Error(`Falha ao obter status do pipeline: ${response.status}`);
  }

  return response.json() as Promise<PipelineStatus>;
}
