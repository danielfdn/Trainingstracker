import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useSyncWorkout } from '../api/mutations'
import { exercisesQuery, planQuery } from '../api/queries'
import type { Exercise } from '../api/types'
import { Button, Card, EmptyState, Modal, Select } from '../components/ui'
import {
  clearDraft,
  elapsedSeconds,
  formatDuration,
  loadDraft,
  saveDraft,
  type WorkoutDraft,
} from '../lib/draft'
import { useUserId } from '../lib/useUserId'

/**
 * `/u/:userId/workout/live` — the screen used one-handed, mid-set.
 *
 * Everything is written to the local draft first and sent as one whole
 * workout when you finish. Nothing here needs a connection until then.
 */
export function LiveWorkout() {
  const userId = useUserId()
  const navigate = useNavigate()
  const [draft, setDraft] = useState<WorkoutDraft | null>(() => loadDraft())
  const sync = useSyncWorkout(userId)

  const { data: plan } = useQuery({
    ...planQuery(draft?.workout_plan_id ?? 0),
    enabled: draft !== null,
  })
  const { data: catalog } = useQuery({ ...exercisesQuery(userId), enabled: draft !== null })

  if (draft === null) {
    return (
      <EmptyState title="No workout in progress">
        <Button className="mt-3" onClick={() => navigate(`/u/${userId}/workout`)}>
          Pick a training day
        </Button>
      </EmptyState>
    )
  }

  const update = (next: WorkoutDraft) => {
    saveDraft(next)
    setDraft(next)
  }

  const day = plan?.training_days.find((entry) => entry.id === draft.training_day_id)
  // A planned day brings its exercises with it; a custom session starts empty
  // and grows as you pick.
  const planned = day?.exercise_links ?? []
  const extraIds = draft.sets
    .map((set) => set.exercise_id)
    .filter((id) => !planned.some((link) => link.exercise_id === id))
  const extras = [...new Set(extraIds)]

  const finish = () => {
    const finished_at = new Date().toISOString()
    sync.mutate(
      {
        client_uuid: draft.client_uuid,
        workout_plan_id: draft.workout_plan_id,
        training_day_id: draft.training_day_id,
        date: draft.started_at,
        started_at: draft.started_at,
        finished_at,
        comment: draft.comment,
        sets: draft.sets.map((set) => ({
          exercise_id: set.exercise_id,
          // undefined, not null: a bodyweight exercise must carry no weight.
          weight: set.weight ?? undefined,
          repetitions: set.repetitions,
        })),
      },
      {
        onSuccess: () => {
          clearDraft()
          navigate(`/u/${userId}/log`)
        },
      },
    )
  }

  return (
    <>
      <Header draft={draft} />

      <div className="grid gap-4">
        {planned.map((link) => (
          <ExerciseBlock
            key={link.exercise_id}
            userId={userId}
            exerciseId={link.exercise_id}
            title={link.exercise.title}
            weighted={link.exercise.weighted}
            target={targetText(link.target_sets, link.target_reps_min, link.target_reps_max)}
            targetSets={link.target_sets}
            draft={draft}
            onChange={update}
          />
        ))}

        {extras.map((exerciseId) => {
          const exercise = catalog?.find((entry) => entry.id === exerciseId)
          return (
            <ExerciseBlock
              key={exerciseId}
              userId={userId}
              exerciseId={exerciseId}
              title={exercise?.title ?? `Exercise ${exerciseId}`}
              weighted={exercise?.weighted ?? true}
              targetSets={0}
              draft={draft}
              onChange={update}
            />
          )
        })}
      </div>

      <AddExercise
        catalog={catalog ?? []}
        used={[...planned.map((link) => link.exercise_id), ...extras]}
        onPick={(exerciseId) =>
          update({
            ...draft,
            sets: [
              ...draft.sets,
              { key: crypto.randomUUID(), exercise_id: exerciseId, repetitions: 0, weight: null },
            ],
          })
        }
      />

      {sync.error && (
        <Card className="mt-6 border-negative/40">
          <p className="text-sm text-negative">{(sync.error as Error).message}</p>
          <p className="mt-1 text-sm text-content-muted">
            Your sets are safe on this device. Try again once you have a connection.
          </p>
        </Card>
      )}

      <div className="mt-8 flex gap-3">
        <Button
          variant="danger"
          onClick={() => {
            if (!window.confirm('Discard this workout and everything logged in it?')) return
            clearDraft()
            navigate(`/u/${userId}`)
          }}
        >
          Discard
        </Button>
        <Button
          variant="primary"
          className="flex-1"
          disabled={sync.isPending || draft.sets.length === 0}
          onClick={finish}
        >
          {sync.isPending ? 'Saving…' : 'Finish workout'}
        </Button>
      </div>
    </>
  )
}

/** Running clock. Derived from the start timestamp, so sleeping is harmless. */
function Header({ draft }: { draft: WorkoutDraft }) {
  const [seconds, setSeconds] = useState(() => elapsedSeconds(draft.started_at))

  useEffect(() => {
    const timer = setInterval(() => setSeconds(elapsedSeconds(draft.started_at)), 1000)
    return () => clearInterval(timer)
  }, [draft.started_at])

  return (
    <header className="mb-6 flex items-baseline justify-between gap-4">
      <h1 className="truncate text-2xl font-semibold tracking-tight">{draft.workout_type}</h1>
      <span className="shrink-0 text-2xl tabular text-accent">{formatDuration(seconds)}</span>
    </header>
  )
}

function targetText(sets: number, min: number | undefined, max: number | undefined): string {
  if (min === undefined || min === null) return `${sets}×`
  if (max === undefined || max === null || max === min) return `${sets}×${min}`
  return `${sets}×${min}-${max}`
}

/** One exercise with its set rows. */
function ExerciseBlock({
  exerciseId,
  title,
  weighted,
  target,
  targetSets,
  draft,
  onChange,
}: {
  userId: number
  exerciseId: number
  title: string
  weighted: boolean
  target?: string
  targetSets: number
  draft: WorkoutDraft
  onChange: (draft: WorkoutDraft) => void
}) {
  const sets = draft.sets.filter((set) => set.exercise_id === exerciseId)

  // Empty rows up to the planned number of sets, so the usual case is typing
  // numbers rather than tapping "add" first.
  const rows = useMemo(() => {
    const missing = Math.max(0, targetSets - sets.length)
    return [...sets, ...Array.from({ length: missing }, () => null)]
  }, [sets, targetSets])

  const write = (index: number, patch: { repetitions?: number; weight?: number | null }) => {
    const existing = sets[index]
    if (existing) {
      onChange({
        ...draft,
        sets: draft.sets.map((set) => (set.key === existing.key ? { ...set, ...patch } : set)),
      })
      return
    }
    // Typing into an empty row is what creates the set.
    onChange({
      ...draft,
      sets: [
        ...draft.sets,
        {
          key: crypto.randomUUID(),
          exercise_id: exerciseId,
          repetitions: patch.repetitions ?? 0,
          weight: patch.weight ?? null,
        },
      ],
    })
  }

  const box =
    'min-h-11 w-full rounded-lg border border-border bg-surface px-3 text-center text-lg tabular focus:border-accent focus:outline-none'

  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="min-w-0 truncate font-medium">{title}</h2>
        {target && <span className="shrink-0 text-sm text-content-muted tabular">{target}</span>}
      </div>

      <div className="mt-3 grid gap-2">
        {rows.map((set, index) => (
          <div key={set?.key ?? `empty-${index}`} className="flex items-center gap-2">
            <span className="w-6 shrink-0 text-sm text-content-faint tabular">{index + 1}</span>
            <input
              className={box}
              type="number"
              inputMode="numeric"
              placeholder="reps"
              defaultValue={set?.repetitions || ''}
              onBlur={(e) => write(index, { repetitions: Number(e.target.value) })}
            />
            {weighted && (
              <input
                className={box}
                type="number"
                inputMode="decimal"
                step="0.5"
                placeholder="kg"
                defaultValue={set?.weight ?? ''}
                onBlur={(e) =>
                  write(index, { weight: e.target.value === '' ? null : Number(e.target.value) })
                }
              />
            )}
            {set && (
              <Button
                variant="ghost"
                onClick={() =>
                  onChange({ ...draft, sets: draft.sets.filter((row) => row.key !== set.key) })
                }
              >
                ✕
              </Button>
            )}
          </div>
        ))}
      </div>

      <Button
        className="mt-3"
        onClick={() =>
          onChange({
            ...draft,
            sets: [
              ...draft.sets,
              { key: crypto.randomUUID(), exercise_id: exerciseId, repetitions: 0, weight: null },
            ],
          })
        }
      >
        Add set
      </Button>

      <p className="mt-3 text-xs text-content-faint">Rows left empty are not saved.</p>
    </Card>
  )
}

function AddExercise({
  catalog,
  used,
  onPick,
}: {
  catalog: Exercise[]
  used: number[]
  onPick: (exerciseId: number) => void
}) {
  const [open, setOpen] = useState(false)
  const [choice, setChoice] = useState('')
  const available = catalog.filter((exercise) => !used.includes(exercise.id))

  return (
    <>
      <Button className="mt-4 w-full" onClick={() => setOpen(true)}>
        Add exercise
      </Button>
      {open && (
        <Modal title="Add exercise" onClose={() => setOpen(false)}>
          {available.length === 0 ? (
            <p className="text-sm text-content-muted">
              Every exercise in your catalog is already on this screen.
            </p>
          ) : (
            <div className="grid gap-4">
              <Select label="Exercise" value={choice} onChange={(e) => setChoice(e.target.value)}>
                <option value="">Choose…</option>
                {available.map((exercise) => (
                  <option key={exercise.id} value={exercise.id}>
                    {exercise.title}
                  </option>
                ))}
              </Select>
              <Button
                variant="primary"
                disabled={choice === ''}
                onClick={() => {
                  onPick(Number(choice))
                  setOpen(false)
                  setChoice('')
                }}
              >
                Add
              </Button>
            </div>
          )}
        </Modal>
      )}
    </>
  )
}
