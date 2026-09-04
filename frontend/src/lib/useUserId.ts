import { useParams } from 'react-router-dom'

/**
 * The `:userId` of the current route, as a number.
 *
 * Every screen below `/u/:userId` needs it, and every screen would otherwise
 * repeat the same `Number(params.userId)` with the same missing NaN check.
 * Throwing lands on the router's error element instead of firing a request
 * for `/api/v1/users/NaN`.
 */
export function useUserId(): number {
  const { userId } = useParams()
  const parsed = Number(userId)
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`"${userId}" is not a valid user id`)
  }
  return parsed
}
