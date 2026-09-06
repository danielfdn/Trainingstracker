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
        onClick={() => {
          const workout_type = window.prompt('Name of the training day (e.g. Push)')?.trim()
          if (!workout_type) return
          addDay.mutate({
            workout_plan_id: planId,
            // Next free position; the backend keeps them unique per plan.
            position: plan.training_days.length + 1,
            workout_type,
          })
        }}
      >
        Add training day
      </Button>

      {pickerFor !== null && (
        <ExercisePicker
          userId={userId}
          trainingDayId={pickerFor}
          nextPosition={
            (plan.training_days.find((day) => day.id === pickerFor)?.exercise_links.length ?? 0) + 1
          }
          onClose={() => setPickerFor(null)}
        />
      )}
    </>
  )
}

/** One planned exercise: the target is editable inline, since that is the
 *  only thing you actually come here to change. */
function PlanExerciseRow({ link }: { link: TrainingDayExercise }) {
  const update = useUpdatePlanExercise()
  const remove = useRemovePlanExercise()

  const change = (patch: { target_sets?: number; target_reps_min?: number; target_reps_max?: number }) =>
    update.mutate({
      trainingDayId: link.training_day_id,
      linkId: link.id,
      ...patch,
    })

  const numberBox =
    'w-16 min-h-11 rounded-lg border border-border bg-surface px-2 text-center tabular focus:border-accent focus:outline-none'

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 py-3">
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
          defaultValue={link.target_sets}
          onBlur={(e) => change({ target_sets: Number(e.target.value) })}
        />
        <span>×</span>
        <input
          className={numberBox}
          type="number"
          inputMode="numeric"
          min={1}
          defaultValue={link.target_reps_min ?? ''}
          onBlur={(e) => change({ target_reps_min: Number(e.target.value) })}
        />
        <span>–</span>
        <input
          className={numberBox}
          type="number"
          inputMode="numeric"
          min={1}
          defaultValue={link.target_reps_max ?? ''}
          onBlur={(e) => change({ target_reps_max: Number(e.target.value) })}
        />
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
