import createClient from 'openapi-fetch'

import type { paths } from './schema'

/** Base URL of the backend, without a trailing slash (see .env.example). */
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

/**
 * The single typed entry point to the API.
 *
 * `paths` is generated from the backend's own OpenAPI document
 * (`npm run gen:api`), so a renamed field or a changed status code turns into
 * a TypeScript error here instead of an undefined at runtime.
 */
export const api = createClient<paths>({ baseUrl })

/**
 * The shape every openapi-fetch call resolves to: either data or an error,
 * never both, always with the raw Response alongside.
 */
type ApiResult<T> =
  | { data: T; error?: undefined; response: Response }
  | { data?: undefined; error: unknown; response: Response }

/**
 * Turns an openapi-fetch call into a promise TanStack Query can use.
 *
 * openapi-fetch never throws: it resolves with `{ error }` on a 404 just as it
 * does with `{ data }` on a 200. Query needs a rejection to mark a query as
 * failed, so every fetcher is wrapped in this.
 */
export async function unwrap<T>(call: Promise<ApiResult<T>>): Promise<T> {
  const result = await call
  if (result.error !== undefined || result.data === undefined) {
    throw new ApiError(result.response.status, detailOf(result.error))
  }
  return result.data
}

export class ApiError extends Error {
  // Written out rather than declared as a constructor parameter property:
  // tsconfig sets erasableSyntaxOnly, which forbids that TypeScript-only form.
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** FastAPI reports errors as `{ detail: ... }` — a string, or a 422 list. */
function detailOf(error: unknown): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          item && typeof item === 'object' && 'msg' in item
            ? String((item as { msg: unknown }).msg)
            : String(item),
        )
        .join(', ')
    }
  }
  return 'Request failed'
}
