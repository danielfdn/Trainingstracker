import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { useUpdateWorkoutComment } from '../api/mutations'
import { exercisesQuery, workoutLogQuery, workoutQuery } from '../api/queries'
import { ExerciseCard, SetRow } from '../components/SetList'
import {
  Button,
  Card,
  EmptyState,
  ErrorNote,
  Loading,
  Modal,
  PageTitle,
  TextArea,
} from '../components/ui'
import { formatSet, groupByExercise } from '../lib/sets'
import { useUserId } from '../lib/useUserId'

/**
 * `/u/:userId/log/:workoutId` — one past session, in the shape it was logged.
 *
 * The sets come from the workout itself; the heading facts (which training
 * day, which plan) come from the log entry that is already cached behind the
 * list you tapped. Two cached reads rather than one wider endpoint.
 */
export function SessionDetail() {
  const userId = useUserId()
  const { workoutId: raw } = useParams()
  const workoutId = Number(raw)
  if (!Number.isInteger(workoutId) || workoutId <= 0) {
    throw new Error(`"${raw}" is not a valid workout id`)
  }

  const { data: workout, isPending, error, refetch } = useQuery(workoutQuery(workoutId))
  const { data: log } = useQuery(workoutLogQuery(userId))
  const { data: catalog } = useQuery(exercisesQuery(userId))

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  const entry = log?.find((row) => row.id === workoutId)
  const groups = groupByExercise(workout.sets)
  const date = new Date(workout.date).toLocaleDateString('de-DE', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })

  return (
    <>
      <Link
        to={`/u/${userId}/log`}
        className="mb-4 inline-block text-sm text-content-muted hover:text-content"
      >
        ‹ Training log
      </Link>

      <PageTitle subtitle={date}>
        {entry?.workout_type ?? (workout.is_custom ? 'Custom' : 'Session')}
      </PageTitle>

      <Card className="mb-6">
        <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <Fact label="Plan" value={entry?.plan_title ?? '–'} />
          <Fact label="Duration" value={workout.duration ?? '–'} />
          <Fact
            label="Body weight"
            value={
              workout.body_weight === null || workout.body_weight === undefined
                ? '–'
                : `${workout.body_weight} kg`
            }
          />
          <Fact
            label="Volume"
            value={`${workout.sets.length} sets · ${groups.length} exercises`}
          />
        </dl>
      </Card>

      <SessionNote userId={userId} workoutId={workoutId} comment={workout.comment} />

      {!workout.attended ? (
        <EmptyState title="Missed session">
          Recorded as not trained, so it carries no sets and no duration.
        </EmptyState>
      ) : groups.length === 0 ? (
        <EmptyState title="No sets logged">
          The session was recorded, but nothing was entered against it.
        </EmptyState>
      ) : (
        <div className="grid gap-4">
          {groups.map((group) => {
            const exercise = catalog?.find((row) => row.id === group.exerciseId)
            return (
              <ExerciseCard
                key={group.exerciseId}
                title={exercise?.title ?? `Exercise ${group.exerciseId}`}
                meta={`${group.sets.length} sets`}
              >
                {group.sets.map((set, index) => (
                  <SetRow key={set.id} index={index}>
                    <span className="text-lg tabular">
                      {formatSet(set.repetitions, set.weight)}
                    </span>
                  </SetRow>
                ))}
              </ExerciseCard>
            )
          })}
        </div>
      )}
    </>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs uppercase tracking-wide text-content-faint">{label}</dt>
      <dd className="mt-1 truncate tabular">{value}</dd>
    </div>
  )
}

/** The same note as on the live screen, editable after the fact. */
function SessionNote({
  userId,
  workoutId,
  comment,
}: {
  userId: number
  workoutId: number
  comment: string
}) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState(comment)
  const save = useUpdateWorkoutComment(userId)

  return (
    <>
      <button
        onClick={() => {
          setText(comment)
          setOpen(true)
        }}
        className="mb-6 w-full rounded-card border border-dashed border-border bg-surface-raised p-4 text-left transition-colors hover:border-border-strong hover:bg-surface-hover"
      >
        <span className="block text-xs uppercase tracking-wide text-content-faint">
          Session note
        </span>
        <span className={`mt-1 block text-sm ${comment ? 'text-content' : 'text-content-muted'}`}>
          {comment || 'No note — tap to add one.'}
        </span>
      </button>

      {open && (
        <Modal title="Session note" onClose={() => setOpen(false)}>
          <div className="grid gap-4">
            <TextArea
              label="Note"
              value={text}
              maxLength={2000}
              autoFocus
              placeholder="Felt strong. Bench moved well, squats heavy."
              onChange={(e) => setText(e.target.value)}
            />

            {save.error && <p className="text-sm text-negative">{(save.error as Error).message}</p>}

            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                disabled={save.isPending}
                onClick={() =>
                  save.mutate({ workoutId, comment: text }, { onSuccess: () => setOpen(false) })
                }
              >
                {save.isPending ? 'Saving…' : 'Save'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}
