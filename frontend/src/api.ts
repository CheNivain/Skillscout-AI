let csrfToken = '';
export function setCsrf(value: string) {
  csrfToken = value;
}
export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      signal: AbortSignal.timeout(150_000),
      credentials: 'same-origin',
      headers: {
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(method === 'GET' ? {} : { 'X-CSRF-Token': csrfToken }),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
  } catch {
    throw new Error('Could not reach SkillScout. Check that the local server is running.');
  }
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: 'The server could not complete this request.' }));
    const detail =
      typeof error.detail === 'string'
        ? error.detail
        : Array.isArray(error.detail)
          ? error.detail.map((e: { msg: string }) => e.msg).join('. ')
          : 'Something went wrong. Please try again.';
    throw Object.assign(new Error(detail), { status: response.status });
  }
  return response.json() as Promise<T>;
}
export const money = (value: number) =>
  value === 0
    ? 'Free'
    : new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 2,
      }).format(value);
export const date = (value: string) =>
  new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
export const initials = (name: string) =>
  name
    .split(/\s+/)
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
