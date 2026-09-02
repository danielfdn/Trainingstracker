import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { useCreateExercise, useDeleteExercise, useUpdateExercise } from '../api/mutations'
import { exercisesQuery } from '../api/queries'
import type { Exercise } from '../api/types'
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

/**
 * `/u/:userId/exercises` — the personal catalog.
 *
 * Deliberately generic: a catalog entry is a name and whether it takes
 * weight. Sets and rep ranges belong to the plan, actual weights to the sets
 * you log. The same "Bankdrücken" can be 5×5 in one plan and 3×12 in the next
 * while staying one row — which is what lets the progress view compare months
 * across a plan change.
 *
 * Renaming matters more than it looks: an exercise is unique per name, so a
 * typo creates a second row that splits that exercise's history in two. This
 * screen is where you repair that.
 */
export function ExerciseCatalog() {
  const userId = useUserId()
  const { data: exercises, isPending, error, refetch } = useQuery(exercisesQuery(userId))
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Exercise | null>(null)

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  return (
    <>
      <PageTitle subtitle="Names only — sets and reps live in your plans.">
        Exercise catalog
      </PageTitle>

      {exercises.length === 0 && (
        <EmptyState title="Catalog is empty">
          Exercises you add here can be used by every plan.
        </EmptyState>
      )}

      {exercises.length > 0 && (
        <Card className="p-0 sm:p-0">
          <ul className="divide-y divide-border">
            {exercises.map((exercise) => (
              <li key={exercise.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <span className="min-w-0 truncate">
                  {exercise.title}
                  {!exercise.weighted && (
                    <span className="ml-2 text-xs text-content-faint">bodyweight</span>
                  )}
                </span>
                <Button variant="ghost" onClick={() => setEditing(exercise)}>
                  Edit
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Button variant="primary" className="mt-6 w-full" onClick={() => setFormOpen(true)}>
        New exercise
      </Button>

      {formOpen && <ExerciseForm userId={userId} onClose={() => setFormOpen(false)} />}
      {editing && (
        <ExerciseForm userId={userId} exercise={editing} onClose={() => setEditing(null)} />
      )}
    </>
  )
}

function ExerciseForm({
  userId,
  exercise,
  onClose,
}: {
  userId: number
  exercise?: Exercise
  onClose: () => void
}) {
  const create = useCreateExercise(userId)
  const update = useUpdateExercise(userId)
  const remove = useDeleteExercise(userId)
  const [title, setTitle] = useState(exercise?.title ?? '')
  const [weighted, setWeighted] = useState(String(exercise?.weighted ?? true))

  const pending = create.isPending || update.isPending
  const failure = (create.error ?? update.error ?? remove.error) as Error | null

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    const body = { title: title.trim(), weighted: weighted === 'true' }
    if (exercise) update.mutate({ id: exercise.id, ...body }, { onSuccess: onClose })
    else create.mutate(body, { onSuccess: onClose })
  }

  return (
    <Modal title={exercise ? 'Edit exercise' : 'New exercise'} onClose={onClose}>
      <form onSubmit={submit} className="grid gap-4">
        <Field
          label="Name"
          autoFocus
          value={title}
          maxLength={100}
          onChange={(e) => setTitle(e.target.value)}
          hint={exercise ? 'Renaming keeps all logged sets attached.' : undefined}
        />
        <Select label="Type" value={weighted} onChange={(e) => setWeighted(e.target.value)}>
          <option value="true">With weight</option>
          <option value="false">Bodyweight only</option>
        </Select>

        {failure && <p className="text-sm text-negative">{failure.message}</p>}

        <div className="flex items-center justify-between gap-2">
          {exercise ? (
            <Button
              type="button"
              variant="danger"
              onClick={() => {
                // Deleting takes every logged set of this exercise with it —
                // renaming is almost always what you actually want.
                if (
                  !window.confirm(
                    `Delete "${exercise.title}"? Every set ever logged for it is deleted too.`,
                  )
                )
                  return
                remove.mutate(exercise.id, { onSuccess: onClose })
              }}
            >
              Delete
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={title.trim() === '' || pending}>
              Save
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  )
}
