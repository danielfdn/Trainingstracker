import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useSyncWorkout } from '../api/mutations'
import { exercisesQuery, planQuery } from '../api/queries'
import { parseDecimalInput } from '../api/types'
import type { Exercise } from '../api/types'
import { ExerciseCard, SetRow } from '../components/SetList'
import { Button, Card, EmptyState, Modal, Select, TextArea } from '../components/ui'
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
  // Anything without a slot was not on the plan: a custom session, or an
  // exercise added on the spot. Deciding this by slot rather than by exercise
  // matters now that the plan may list the same exercise twice.
  const extraIds = draft.sets
    .filter((set) => set.training_day_exercise_id == null)
    .map((set) => set.exercise_id)
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
          training_day_exercise_id: set.training_day_exercise_id ?? null,
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

      <SessionNote draft={draft} onChange={update} />

      <div className="grid gap-4">
        {planned.map((link) => (
          <ExerciseBlock
            key={link.id}
            userId={userId}
            linkId={link.id}
            exerciseId={link.exercise_id}
            title={link.exercise.title}
            weighted={link.exercise.weighted}
            target={`${link.target_sets}×`}
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
              linkId={null}
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
              {
                key: crypto.randomUUID(),
                exercise_id: exerciseId,
                repetitions: 0,
                weight: null,
                training_day_exercise_id: null,
              },
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

/**
 * The session note — one free-text field for the whole workout.
 *
 * Written into the draft rather than sent immediately: mid-workout there may
 * be no connection, and the note travels with the session on finish like the
 * sets do. Editing it again before finishing simply overwrites it.
 */
function SessionNote({
  draft,
  onChange,
}: {
  draft: WorkoutDraft
  onChange: (draft: WorkoutDraft) => void
}) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState(draft.comment)

  return (
    <>
      <button
        onClick={() => {
          // Start from what is stored, not from whatever a cancelled edit left.
          setText(draft.comment)
          setOpen(true)
        }}
        className="mb-6 w-full rounded-card border border-dashed border-border bg-surface-raised p-4 text-left transition-colors hover:border-border-strong hover:bg-surface-hover"
      >
        <span className="block text-xs uppercase tracking-wide text-content-faint">
          Session note
        </span>
        <span
          className={`mt-1 block text-sm ${draft.comment ? 'text-content' : 'text-content-muted'}`}
        >
          {draft.comment || 'Add a note — how it went, what to change next time.'}
        </span>
      </button>

      {open && (
        <Modal title="Session note" onClose={() => setOpen(false)}>
          <div className="grid gap-4">
            <TextArea
              label="Note"
              value={text}
              // Matches the column: the server rejects anything longer.
              maxLength={2000}
              autoFocus
              placeholder="Felt strong. Bench moved well, squats heavy."
              hint="Kept on this device and sent with the workout when you finish."
              onChange={(e) => setText(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  onChange({ ...draft, comment: text })
                  setOpen(false)
                }}
              >
                Save
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}

/** One exercise with its set rows. */
function ExerciseBlock({
  linkId,
  exerciseId,
  title,
  weighted,
  target,
  targetSets,
  draft,
  onChange,
}: {
  userId: number
  /** The slot of the training day this card logs into, or null when the
   *  exercise is not on the plan (custom session, or added on the spot). */
  linkId: number | null
  exerciseId: number
  title: string
  weighted: boolean
  target?: string
  targetSets: number
  draft: WorkoutDraft
  onChange: (draft: WorkoutDraft) => void
}) {
  // Scoped by slot, so "Bench Press 5×5" and "Bench Press 3×12" on the same
  // day keep their own rows instead of mirroring each other. Cards without a
  // slot collect the sets that have none, by exercise.
  const sets = draft.sets.filter((set) =>
    linkId === null
      ? set.training_day_exercise_id == null && set.exercise_id === exerciseId
      : set.training_day_exercise_id === linkId,
  )

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
          training_day_exercise_id: linkId,
        },
      ],
    })
  }

  const box =
    'min-h-11 w-full rounded-lg border border-border bg-surface px-3 text-center text-lg tabular focus:border-accent focus:outline-none'

  const addSet = () =>
    onChange({
      ...draft,
      sets: [
        ...draft.sets,
        {
          key: crypto.randomUUID(),
          exercise_id: exerciseId,
          repetitions: 0,
          weight: null,
          training_day_exercise_id: linkId,
        },
      ],
    })

  return (
    <ExerciseCard
      title={title}
      meta={target}
      footer={
        <>
          <Button className="mt-3" onClick={addSet}>
            Add set
          </Button>
          <p className="mt-3 text-xs text-content-faint">Rows left empty are not saved.</p>
        </>
      }
    >
      {rows.map((set, index) => (
        <SetRow key={set?.key ?? `empty-${index}`} index={index}>
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
              // Text, not number: a comma is what the German keyboard offers
              // and what formatWeight prints, but type="number" reads "82,5"
              // as an empty string. parseDecimalInput takes either separator.
              type="text"
              inputMode="decimal"
              placeholder="kg"
              defaultValue={set?.weight ?? ''}
              onBlur={(e) => write(index, { weight: parseDecimalInput(e.target.value) })}
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
        </SetRow>
      ))}
    </ExerciseCard>
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
