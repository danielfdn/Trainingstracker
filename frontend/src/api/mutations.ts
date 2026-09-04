import { useMutation, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from './client'

/**
 * Every write the app performs.
 *
 * Each hook invalidates the queries its write invalidates — collected here
 * rather than spread across the screens, so a new endpoint cannot forget to
 * refresh the list it just changed.
 */

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; age: number; weight: number }) =>
      unwrap(api.POST('/api/v1/users', { body })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

export function useUpdateUser(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name?: string; age?: number; weight?: number }) =>
      unwrap(api.PATCH('/api/v1/users/{user_id}', { params: { path: { user_id: userId } }, body })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

export function useDeleteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (userId: number) => {
      // 204 No Content: there is no body to unwrap, only a status to check.
      const { error, response } = await api.DELETE('/api/v1/users/{user_id}', {
        params: { path: { user_id: userId } },
      })
      if (error !== undefined && !response.ok) throw new Error('Could not delete the profile')
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

/** The one active plan. `workout_plan_id: null` clears the choice. */
export function useSetActivePlan(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (workout_plan_id: number | null) =>
      unwrap(
        api.PUT('/api/v1/users/{user_id}/active-plan', {
          params: { path: { user_id: userId } },
          body: { workout_plan_id },
        }),
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

export function useCreatePlan(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      title: string
      training_days: { position: number; workout_type: string }[]
    }) =>
      unwrap(
        api.POST('/api/v1/workout-plans', {
          body: {
            title: body.title,
            user_id: userId,
            // The days start empty; exercises are added in the plan editor.
            training_days: body.training_days.map((day) => ({ ...day, exercises: [] })),
          },
        }),
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', userId, 'plans'] }),
  })
}

export function useDuplicatePlan(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (planId: number) =>
      unwrap(
        api.POST('/api/v1/workout-plans/{plan_id}/duplicate', {
          params: { path: { plan_id: planId } },
          body: {},
        }),
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', userId, 'plans'] }),
  })
}

export function useDeletePlan(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (planId: number) => {
      const { error, response } = await api.DELETE('/api/v1/workout-plans/{plan_id}', {
        params: { path: { plan_id: planId } },
      })
      if (error !== undefined && !response.ok) throw new Error('Could not delete the plan')
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users', userId, 'plans'] })
      // Deleting the active plan clears appuser.active_workout_plan_id.
      qc.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

export function useCreateExercise(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { title: string; weighted: boolean }) =>
      unwrap(api.POST('/api/v1/exercises', { body: { ...body, user_id: userId } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', userId, 'exercises'] }),
  })
}

export function useUpdateExercise(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; title?: string; weighted?: boolean }) =>
      unwrap(
        api.PATCH('/api/v1/exercises/{exercise_id}', {
          params: { path: { exercise_id: id } },
          body,
        }),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users', userId, 'exercises'] })
      qc.invalidateQueries({ queryKey: ['plans'] })
    },
  })
}

export function useDeleteExercise(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (exerciseId: number) => {
      const { error, response } = await api.DELETE('/api/v1/exercises/{exercise_id}', {
        params: { path: { exercise_id: exerciseId } },
      })
      if (error !== undefined && !response.ok) throw new Error('Could not delete the exercise')
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users', userId, 'exercises'] })
      qc.invalidateQueries({ queryKey: ['plans'] })
    },
  })
}

export function useAddPlanExercise() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      trainingDayId,
      position = 1,
      target_sets = 3,
      ...body
    }: {
      trainingDayId: number
      exercise_id: number
      position?: number
      target_sets?: number
      target_reps_min?: number
      target_reps_max?: number
    }) =>
      unwrap(
        api.POST('/api/v1/training-days/{training_day_id}/exercises', {
          params: { path: { training_day_id: trainingDayId } },
          body: { ...body, position, target_sets },
        }),
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plans'] }),
  })
}

export function useUpdatePlanExercise() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      trainingDayId,
      exerciseId,
      ...body
    }: {
      trainingDayId: number
      exerciseId: number
      target_sets?: number
      target_reps_min?: number
      target_reps_max?: number
      position?: number
    }) =>
      unwrap(
        api.PATCH('/api/v1/training-days/{training_day_id}/exercises/{exercise_id}', {
          params: { path: { training_day_id: trainingDayId, exercise_id: exerciseId } },
          body,
        }),
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plans'] }),
  })
}

export function useRemovePlanExercise() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      trainingDayId,
      exerciseId,
    }: {
      trainingDayId: number
      exerciseId: number
    }) => {
      const { error, response } = await api.DELETE(
        '/api/v1/training-days/{training_day_id}/exercises/{exercise_id}',
        { params: { path: { training_day_id: trainingDayId, exercise_id: exerciseId } } },
      )
      if (error !== undefined && !response.ok) throw new Error('Could not remove the exercise')
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plans'] }),
  })
}

export function useAddTrainingDay() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { workout_plan_id: number; position: number; workout_type: string }) =>
      unwrap(api.POST('/api/v1/training-days', { body: { ...body, exercises: [] } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plans'] }),
  })
}

export function useDeleteTrainingDay() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (trainingDayId: number) => {
      const { error, response } = await api.DELETE('/api/v1/training-days/{training_day_id}', {
        params: { path: { training_day_id: trainingDayId } },
      })
      if (error !== undefined && !response.ok) throw new Error('Could not delete the day')
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plans'] }),
  })
}

/** Sends a finished local draft as one whole workout. Idempotent server-side. */
export function useSyncWorkout(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      client_uuid: string
      workout_plan_id: number
      training_day_id: number | null
      date: string
      started_at: string
      finished_at: string
      comment: string
      sets: { exercise_id: number; repetitions: number; weight?: number }[]
    }) => unwrap(api.POST('/api/v1/workouts/sync', { body })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users', userId, 'log'] })
      qc.invalidateQueries({ queryKey: ['users', userId, 'workouts'] })
    },
  })
}

/**
 * Edits the note on a session that is already synced.
 *
 * The live screen writes the note into the local draft; once the workout is
 * on the server the draft is gone, so the second entry point is a PATCH —
 * you usually remember the useful remark the morning after.
 */
export function useUpdateWorkoutComment(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ workoutId, comment }: { workoutId: number; comment: string }) =>
      unwrap(
        api.PATCH('/api/v1/workouts/{workout_id}', {
          params: { path: { workout_id: workoutId } },
          body: { comment },
        }),
      ),
    onSuccess: (workout) => {
      qc.invalidateQueries({ queryKey: ['workouts', workout.id] })
      qc.invalidateQueries({ queryKey: ['users', userId, 'log'] })
      qc.invalidateQueries({ queryKey: ['users', userId, 'workouts'] })
    },
  })
}

/**
 * Records a session you did not do.
 *
 * A plan has training days but no dates, so nothing knows you meant to train
 * on Tuesday — marking one missed means writing the row retroactively, with
 * no times and no sets.
 */
export function useMarkMissed(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      workout_plan_id: number
      training_day_id: number | null
      date: string
      comment?: string
    }) =>
      unwrap(
        api.POST('/api/v1/workouts', {
          body: {
            ...body,
            comment: body.comment ?? '',
            // No start and no finish: a session that did not happen has no
            // times, and therefore no duration in the log.
            attended: false,
          },
        }),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users', userId, 'log'] })
      qc.invalidateQueries({ queryKey: ['users', userId, 'workouts'] })
    },
  })
}

/** Undo for the above — the toast's action, not a general delete. */
export function useDeleteWorkout(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (workoutId: number) => {
      const { error, response } = await api.DELETE('/api/v1/workouts/{workout_id}', {
        params: { path: { workout_id: workoutId } },
      })
      if (error !== undefined && !response.ok) throw new Error('Could not undo')
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users', userId, 'log'] })
      qc.invalidateQueries({ queryKey: ['users', userId, 'workouts'] })
    },
  })
}
