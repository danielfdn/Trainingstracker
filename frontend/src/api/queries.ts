import { queryOptions } from '@tanstack/react-query'

import { api, unwrap } from './client'

/**
 * Query definitions, one per endpoint the app reads.
 *
 * Declared as `queryOptions` rather than as hooks so key and fetcher stay
 * together: `queryClient.invalidateQueries(userQuery(3))` after a mutation
 * cannot then drift from what the component subscribed to.
 */

export const usersQuery = () =>
  queryOptions({
    queryKey: ['users'],
    queryFn: () => unwrap(api.GET('/api/v1/users', {})),
  })

export const userQuery = (userId: number) =>
  queryOptions({
    queryKey: ['users', userId],
    queryFn: () => unwrap(api.GET('/api/v1/users/{user_id}', { params: { path: { user_id: userId } } })),
  })

/** Plans are filtered by query parameter, not by a nested path. */
export const userPlansQuery = (userId: number) =>
  queryOptions({
    queryKey: ['users', userId, 'plans'],
    queryFn: () =>
      unwrap(api.GET('/api/v1/workout-plans', { params: { query: { user_id: userId } } })),
  })

export const workoutLogQuery = (userId: number) =>
  queryOptions({
    queryKey: ['users', userId, 'log', 'workouts'],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/users/{user_id}/log/workouts', {
          params: { path: { user_id: userId } },
        }),
      ),
  })

export const logMonthsQuery = (userId: number) =>
  queryOptions({
    queryKey: ['users', userId, 'log', 'months'],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/users/{user_id}/log/months', {
          params: { path: { user_id: userId } },
        }),
      ),
  })

/** The month-vs-month comparison. Both months come from `logMonthsQuery`. */
export const progressQuery = (userId: number, monthA: string, monthB: string) =>
  queryOptions({
    queryKey: ['users', userId, 'log', 'progress', monthA, monthB],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/users/{user_id}/log/progress', {
          params: { path: { user_id: userId }, query: { month_a: monthA, month_b: monthB } },
        }),
      ),
  })
