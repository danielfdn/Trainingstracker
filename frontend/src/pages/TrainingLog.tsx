import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useDeleteWorkout, useMarkMissed } from '../api/mutations'
import { userPlansQuery, userQuery, workoutLogQuery } from '../api/queries'
import {
  Button,
  Card,
  EmptyState,
  ErrorNote,
  Field,
  Loading,
  Modal,
  PageTitle,
  Select,
  UndoToast,
} from '../components/ui'
import { useUserId } from '../lib/useUserId'

/** `/u/:userId/log` — every past session, newest first. Spec view one. */
export function TrainingLog() {
  const userId = useUserId()
  const { data: entries, isPending, error, refetch } = useQuery(workoutLogQuery(userId))
  const undo = useDeleteWorkout(userId)
  const [backfill, setBackfill] = useState(false)
  const [missed, setMissed] = useState<{ id: number } | null>(null)

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  return (
    <>
      <PageTitle subtitle={`${entries.length} sessions`}>Training log</PageTitle>

      <div className="mb-6 flex flex-wrap gap-2">
        <Link
          to={`/u/${userId}/log/progress`}
          className="inline-flex min-h-11 items-center rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-accent-content hover:bg-accent-hover"
        >
          Compare months
        </Link>
        <Button onClick={() => setBackfill(true)}>Log a missed session</Button>
      </div>

      {entries.length === 0 && (
        <EmptyState title="Nothing logged yet">Your finished workouts appear here.</EmptyState>
      )}

      <ul className="grid gap-3">
        {entries.map((entry) => (
          <li key={entry.id}>
            <Card className={entry.attended ? undefined : 'border-dashed'}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">
                    {entry.workout_type}
                    {entry.is_custom && (
                      <span className="ml-2 rounded-full bg-surface-hover px-2 py-0.5 text-xs text-content-muted">
                        Custom
                      </span>
                    )}
                    {!entry.attended && (
                      <span className="ml-2 rounded-full bg-surface-hover px-2 py-0.5 text-xs text-content-muted">
                        Missed
                      </span>
                    )}
                  </p>
                  <p className="mt-0.5 truncate text-sm text-content-muted tabular">
                    {new Date(entry.date).toLocaleDateString('de-DE', {
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                    })}
                    {' · '}
                    {entry.plan_title}
                  </p>
                </div>
                <div className="shrink-0 text-right text-sm tabular">
                  {entry.duration && <p className="text-content-muted">{entry.duration}</p>}
                  {/* The weight of that day, not today's — the reason
                      workout.body_weight exists at all. */}
                  {entry.body_weight !== null && entry.body_weight !== undefined && (
                    <p className="text-content-faint">{entry.body_weight} kg</p>
                  )}
                </div>
              </div>

              {entry.attended && (
                <p className="mt-3 text-sm text-content-faint tabular">
                  {entry.set_count} sets · {entry.exercise_count} exercises
                </p>
              )}
              {entry.comment && (
                <p className="mt-2 text-sm text-content-muted">{entry.comment}</p>
              )}
            </Card>
          </li>
        ))}
      </ul>

      {backfill && (
        <BackfillMissed
          userId={userId}
          onClose={() => setBackfill(false)}
          onDone={(id) => {
            setBackfill(false)
            setMissed({ id })
          }}
        />
      )}

      {missed && (
        <UndoToast
          message="Missed session recorded"
          onUndo={() => {
            undo.mutate(missed.id)
            setMissed(null)
          }}
          onDismiss={() => setMissed(null)}
        />
      )}
    </>
  )
}

/**
 * Backfills a session you skipped.
 *
 * The second entry point for "missed", because you usually remember on
 * Thursday that you skipped Tuesday.
 */
function BackfillMissed({
  userId,
  onClose,
  onDone,
}: {
  userId: number
  onClose: () => void
  onDone: (workoutId: number) => void
}) {
  const { data: user } = useQuery(userQuery(userId))
  const { data: plans } = useQuery(userPlansQuery(userId))
  const markMissed = useMarkMissed(userId)
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [planId, setPlanId] = useState(String(user?.active_workout_plan_id ?? plans?.[0]?.id ?? ''))

  return (
    <Modal title="Log a missed session" onClose={onClose}>
      <div className="grid gap-4">
        <Field label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <Select label="Plan" value={planId} onChange={(e) => setPlanId(e.target.value)}>
          {(plans ?? []).map((plan) => (
            <option key={plan.id} value={plan.id}>
              {plan.title}
            </option>
          ))}
        </Select>

        {markMissed.error && (
          <p className="text-sm text-negative">{(markMissed.error as Error).message}</p>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={planId === '' || markMissed.isPending}
            onClick={() =>
              markMissed.mutate(
                {
                  workout_plan_id: Number(planId),
                  training_day_id: null,
                  // Midday, so the calendar-month bucket cannot shift with
                  // the timezone.
                  date: new Date(`${date}T12:00:00`).toISOString(),
                },
                { onSuccess: (workout) => onDone(workout.id) },
              )
            }
          >
            Record
          </Button>
        </div>
      </div>
    </Modal>
  )
}
