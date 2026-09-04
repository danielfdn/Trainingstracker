import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '../api/client'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // The tracker is single-user and local; data barely changes behind our
      // back, so refetching on every window focus is only noise.
      refetchOnWindowFocus: false,
      staleTime: 30_000,
      retry: (failureCount, error) => {
        // A 404 or a 422 will not become correct by asking again.
        if (error instanceof ApiError && error.status < 500) return false
        return failureCount < 2
      },
    },
  },
})
