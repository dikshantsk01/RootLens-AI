/** Base URL for the backend API. All fetch wrappers live in src/api/. */
export const API_BASE_URL = 'http://localhost:8000'

export interface HealthResponse {
  status: string
}

/** GET /health — probe backend liveness. */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`)
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }
  return (await response.json()) as HealthResponse
}
