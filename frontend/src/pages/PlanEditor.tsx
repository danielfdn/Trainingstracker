import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

import {
  useAddPlanExercise,
  useAddTrainingDay,
  useCreateExercise,
  useDeleteTrainingDay,
  useRemovePlanExercise,
  useUpdatePlanExercise,
} from '../api/mutations'
import { exercisesQuery, planQuery } from '../api/queries'
import type { TrainingDayExercise } from '../api/types'
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
} from '../components/ui'
import { useUserId } from '../lib/useUserId'

/** A plan covers a week, so the backend caps positions at 7. */
const MAX_TRAINING_DAYS = 7

/**
 * The lowest position not yet taken by a training day.
 *
 * `days.length + 1` looks like the same thing and is not: delete the middle
 * day of three and you are left with positions 1 and 3, where length + 1 is
 * 3 — already taken. The backend rejects that with a 409, and adding a day
 * silently did nothing at all. Counting is not numbering as soon as anything
 * can be removed from the middle.
 *
 * Filling the gap rather than appending past it also keeps positions dense,
 * which matters because of the cap: a plan of five days must never run out
 * of numbers because two were deleted along the way.
 */
function nextFreePosition(days: { position: number }[]): number {
  const taken = new Set(days.map((day) => day.position))
  let position = 1
  while (taken.has(position)) position += 1
  return position
}

/** `/u/:userId/plans/:planId` — training days, their exercises and targets. */
export function PlanEditor() {
  const userId = useUserId()
  const { planId: planParam } = useParams()
  const planId = Number(planParam)
  const { data: plan, isPending, error, refetch } = useQuery(planQuery(planId))
  const addDay = useAddTrainingDay()
  const deleteDay = useDeleteTrainingDay()
  const [pickerFor, setPickerFor] = useState<number | null>(null)

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  const voll = plan.training_days.length >= MAX_TRAINING_DAYS

  return (
    <>
      <PageTitle subtitle={`${plan.training_days_per_week} training days`}>{plan.title}</PageTitle>

      {plan.training_days.length === 0 && (
        <EmptyState title="No training days">Add a day to start filling in exercises.</EmptyState>
      )}

      <div className="grid gap-4">
        {plan.training_days.map((day) => (
          <Card key={day.id}>
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-medium">
                <span className="text-content-faint">Day {day.position} — </span>
                {day.workout_type}
              </h2>
              <Button
                variant="ghost"
                onClick={() => {
                  if (!window.confirm(`Remove "${day.workout_type}" from this plan?`)) return
                  deleteDay.mutate(day.id)
                }}
              >
                Remove day
              </Button>
            </div>

            <ul className="mt-3 divide-y divide-border">
              {day.exercise_links.map((link) => (
                <PlanExerciseRow key={link.id} link={link} />
              ))}
            </ul>

            {day.exercise_links.length === 0 && (
              <p className="mt-2 text-sm text-content-faint">No exercises yet.</p>
            )}

            <Button className="mt-4" onClick={() => setPickerFor(day.id)}>
              Add exercise
            </Button>
          </Card>
        ))}
      </div>

      <Button
        className="mt-6 w-full"
        disabled={voll || addDay.isPending}
        onClick={() => {
          const workout_type = window.prompt('Name of the training day (e.g. Push)')?.trim()
          if (!workout_type) return
          addDay.mutate({
            workout_plan_id: planId,
            position: nextFreePosition(plan.training_days),
            workout_type,
          })
        }}
      >
        {addDay.isPending ? 'Adding…' : 'Add training day'}
      </Button>

      {voll && (
        <p className="mt-2 text-sm text-content-faint">
          A plan holds at most {MAX_TRAINING_DAYS} days — remove one to add another.
        </p>
      )}
      {/* A rejected create used to leave no trace: you typed a name, the
          dialog closed, and nothing appeared. */}
      {addDay.error && (
        <p className="mt-2 text-sm text-negative">
          Could not add the day: {(addDay.error as Error).message}
        </p>
      )}
      {deleteDay.error && (
        <p className="mt-2 text-sm text-negative">{(deleteDay.error as Error).message}</p>
      )}

      {pickerFor !== null && (
        <ExercisePicker
          userId={userId}
          trainingDayId={pickerFor}
          // One past the highest in use, so a new exercise lands at the end
          // of the day even after one was removed from the middle. Unlike the
          // days, these positions carry no uniqueness constraint — a clash
          // would not error, it would just order two exercises arbitrarily.
          nextPosition={
            Math.max(
              0,
              ...(plan.training_days
                .find((day) => day.id === pickerFor)
                ?.exercise_links.map((link) => link.position) ?? []),
            ) + 1
          }
          onClose={() => setPickerFor(null)}
        />
      )}
    </>
  )
}

/**
 * One planned exercise: the number of sets, and a button that saves it.
 *
 * Saving on blur is what this screen did before, and it lost changes: on the
 * phone you usually leave the field by tapping somewhere that navigates, and
 * whether blur still reached the mutation was a race. Worse, nothing ever
 * told you either way — you typed 4, saw 4, and the plan kept 3. An explicit
 * button makes the save a thing you do, with a visible result.
 *
 * The input is controlled, so the field is the draft and `link.target_sets`
 * is what the server has. "Save" appears only while the two differ.
 */
function PlanExerciseRow({ link }: { link: TrainingDayExercise }) {
  const update = useUpdatePlanExercise()
  const remove = useRemovePlanExercise()
  const [sets, setSets] = useState(String(link.target_sets))
  const [saved, setSaved] = useState(false)

  const parsed = Number(sets)
  const valid = Number.isInteger(parsed) && parsed >= 1 && parsed <= 20
  // Compared against the string form of what the server holds, so re-typing
  // the same number does not offer a pointless save.
  const changed = sets !== String(link.target_sets)

  const save = () => {
    if (!valid || !changed) return
    update.mutate(
      { trainingDayId: link.training_day_id, linkId: link.id, target_sets: parsed },
      { onSuccess: () => setSaved(true) },
    )
  }

  const numberBox =
    'w-16 min-h-11 rounded-lg border border-border bg-surface px-2 text-center tabular focus:border-accent focus:outline-none'

  return (
    <li className="py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="min-w-0 flex-1 truncate">
          {link.exercise.title}
          {!link.exercise.weighted && (
            <span className="ml-2 text-xs text-content-faint">bodyweight</span>
          )}
        </span>

        <div className="flex items-center gap-1.5 text-sm text-content-muted">
          <input
            className={numberBox}
            type="number"
            inputMode="numeric"
            min={1}
            max={20}
            value={sets}
            aria-label={`Sets for ${link.exercise.title}`}
            onChange={(e) => {
              setSets(e.target.value)
              setSaved(false)
            }}
            // Enter saves, so the keyboard's own confirm key does the
            // obvious thing instead of nothing.
            onKeyDown={(e) => {
              if (e.key === 'Enter') save()
            }}
          />
          <span>sets</span>

          {changed ? (
            <Button variant="primary" disabled={!valid || update.isPending} onClick={save}>
              {update.isPending ? 'Saving…' : 'Save'}
            </Button>
          ) : (
            saved && <span className="text-positive">Saved</span>
          )}

          <Button
            variant="ghost"
            onClick={() =>
              remove.mutate({
                trainingDayId: link.training_day_id,
                linkId: link.id,
              })
            }
          >
            ✕
          </Button>
        </div>
      </div>

      {changed && !valid && (
        <p className="mt-1 text-sm text-negative">Sets must be a whole number from 1 to 20.</p>
      )}
      {update.error && (
        <p className="mt-1 text-sm text-negative">{(update.error as Error).message}</p>
      )}
    </li>
  )
}

/**
 * Picks an exercise from the catalog, or creates one on the spot.
 *
 * Creating from here still writes to the catalog — there is no such thing as
 * a plan-local exercise, which is what keeps the month comparison working
 * across a plan change.
 */
export function ExercisePicker({
  userId,
  trainingDayId,
  nextPosition,
  onClose,
}: {
  userId: number
  trainingDayId: number
  nextPosition: number
  onClose: () => void
}) {
  const { data: exercises } = useQuery(exercisesQuery(userId))
  const add = useAddPlanExercise()
  const create = useCreateExercise(userId)
  const [title, setTitle] = useState('')
  const [weighted, setWeighted] = useState('true')

  const available = exercises ?? []

  const attach = (exercise_id: number) =>
    add.mutate({ trainingDayId, exercise_id, position: nextPosition }, { onSuccess: onClose })

  return (
    <Modal title="Add exercise" onClose={onClose}>
      {available.length > 0 && (
        <ul className="mb-5 max-h-64 divide-y divide-border overflow-y-auto">
          {available.map((exercise) => (
            <li key={exercise.id}>
              <button
                onClick={() => attach(exercise.id)}
                className="flex w-full items-center justify-between gap-3 py-3 text-left hover:text-accent"
              >
                <span className="truncate">{exercise.title}</span>
                {!exercise.weighted && (
                  <span className="shrink-0 text-xs text-content-faint">bodyweight</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="border-t border-border pt-4">
        <p className="mb-3 text-sm text-content-muted">Or add a new one to your catalog:</p>
        <div className="grid gap-3">
          <Field
            label="Name"
            value={title}
            placeholder="Bankdrücken"
            onChange={(e) => setTitle(e.target.value)}
          />
          <Select label="Type" value={weighted} onChange={(e) => setWeighted(e.target.value)}>
            <option value="true">With weight</option>
            <option value="false">Bodyweight only</option>
          </Select>
          {create.error && <p className="text-sm text-negative">{(create.error as Error).message}</p>}
          <Button
            variant="primary"
            disabled={title.trim() === '' || create.isPending}
            onClick={() =>
              create.mutate(
                { title: title.trim(), weighted: weighted === 'true' },
                { onSuccess: (exercise) => attach(exercise.id) },
              )
            }
          >
            Create and add
          </Button>
        </div>
      </div>
    </Modal>
  )
}
