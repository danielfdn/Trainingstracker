import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useDeleteWorkout, useMarkMissed } from '../api/mutations'
import { planQuery, userQuery } from '../api/queries'
import { Button, Card, EmptyState, ErrorNote, Loading, PageTitle, UndoToast } from '../components/ui'
import { loadDraft, newDraft, saveDraft } from '../lib/draft'
import { useUserId } from '../lib/useUserId'

/**
 * `/u/:userId/workout` — which day is it today?
 *
 * Lists the active plan's training days, with Custom below the divider for
 * the days the equipment is missing.
 */
export function WorkoutPicker() {
  const userId = useUserId()
  const navigate = useNavigate()
  const { data: user, isPending, error, refetch } = useQuery(userQuery(userId))
  const planId = user?.active_workout_plan_id ?? null
  const { data: plan } = useQuery({ ...planQuery(planId ?? 0), enabled: planId !== null })

  const markMissed = useMarkMissed(userId)
  const undoMissed = useDeleteWorkout(userId)
  const [missed, setMissed] = useState<{ id: number; label: string } | null>(null)

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  if (planId === null) {
    return (
      <>
        <PageTitle>Start a workout</PageTitle>
        <EmptyState title="No active plan">
          Pick one in Workout plans first — the day list comes from it.
        </EmptyState>
      </>
    )
  }

  const start = (trainingDayId: number | null, workoutType: string) => {
    const existing = loadDraft()
    // A second session while one is still open would leave the first
    // stranded, so ask before replacing it.
    if (existing && !window.confirm('A workout is still open. Discard it and start a new one?')) {
      navigate(`/u/${userId}/workout/live`)
      return
    }
    saveDraft(
      newDraft({
        user_id: userId,
        workout_plan_id: planId,
        training_day_id: trainingDayId,
        workout_type: workoutType,
      }),
    )
    navigate(`/u/${userId}/workout/live`)
  }

  const skip = (trainingDayId: number, label: string) =>
    markMissed.mutate(
      {
        workout_plan_id: planId,
        training_day_id: trainingDayId,
        date: new Date().toISOString(),
      },
      { onSuccess: (workout) => setMissed({ id: workout.id, label }) },
    )

  return (
    <>
      <PageTitle subtitle={plan?.title}>Start a workout</PageTitle>

      <div className="grid gap-3">
        {(plan?.training_days ?? []).map((day) => (
          <Card key={day.id}>
            <div className="flex items-center justify-between gap-3">
              <button
                className="min-w-0 flex-1 text-left"
                onClick={() => start(day.id, day.workout_type)}
              >
                <span className="block truncate font-medium">
                  <span className="text-content-faint">Day {day.position} — </span>
                  {day.workout_type}
                </span>
                <span className="mt-0.5 block truncate text-sm text-content-muted">
                  {day.exercise_links.length} exercises
                </span>
              </button>
              {/* Secondary action: one tap, undoable, no dialog. */}
              <Button
                variant="ghost"
                title="Mark as missed"
                onClick={() => skip(day.id, day.workout_type)}
                disabled={markMissed.isPending}
              >
                Skip
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <div className="my-6 flex items-center gap-3 text-xs text-content-faint">
        <span className="h-px flex-1 bg-border" />
        or
        <span className="h-px flex-1 bg-border" />
      </div>

      <Card>
        <button className="w-full text-left" onClick={() => start(null, 'Custom')}>
          <span className="block font-medium">Custom workout</span>
          <span className="mt-0.5 block text-sm text-content-muted">
            Free choice of exercises. Kept out of the progress analysis, still listed in the log.
          </span>
        </button>
      </Card>

      {missed && (
        <UndoToast
          message={`${missed.label} marked as missed`}
          onUndo={() => {
            undoMissed.mutate(missed.id)
            setMissed(null)
          }}
          onDismiss={() => setMissed(null)}
        />
      )}
    </>
  )
}
