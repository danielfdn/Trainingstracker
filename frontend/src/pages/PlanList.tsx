import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useCreatePlan, useDeletePlan, useDuplicatePlan, useSetActivePlan } from '../api/mutations'
import { userPlansQuery, userQuery } from '../api/queries'
import {
  Button,
  Card,
  EmptyState,
  ErrorNote,
  Field,
  Loading,
  Modal,
  PageTitle,
} from '../components/ui'
import { useUserId } from '../lib/useUserId'

/**
 * `/u/:userId/plans` — the plans, and everything you do to a plan.
 *
 * Switching the active plan lives here rather than on its own menu row: it is
 * one choice among these plans, so this is where you already are when you
 * want to make it.
 */
export function PlanList() {
  const userId = useUserId()
  const { data: plans, isPending, error, refetch } = useQuery(userPlansQuery(userId))
  const { data: user } = useQuery(userQuery(userId))
  const setActive = useSetActivePlan(userId)
  const duplicate = useDuplicatePlan(userId)
  const remove = useDeletePlan(userId)
  const [formOpen, setFormOpen] = useState(false)

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  return (
    <>
      <PageTitle subtitle="One plan is active at a time.">Workout plans</PageTitle>

      {plans.length === 0 && (
        <EmptyState title="No plans yet">
          A plan holds your training days — Push, Pull, Legs — and the exercises for each.
        </EmptyState>
      )}

      <ul className="grid gap-3">
        {plans.map((plan) => {
          const isActive = plan.id === user?.active_workout_plan_id
          return (
            <li key={plan.id}>
              <Card className={isActive ? 'border-accent/60' : undefined}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link
                      to={`/u/${userId}/plans/${plan.id}`}
                      className="block truncate font-medium hover:text-accent"
                    >
                      {plan.title}
                    </Link>
                    <p className="mt-0.5 text-sm text-content-muted tabular">
                      {plan.starting_date ? `from ${plan.starting_date}` : 'no start date'}
                    </p>
                  </div>
                  {isActive && (
                    <span className="shrink-0 rounded-full bg-accent-muted px-2.5 py-1 text-xs font-medium text-accent">
                      Active
                    </span>
                  )}
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {!isActive && (
                    <Button onClick={() => setActive.mutate(plan.id)} disabled={setActive.isPending}>
                      Make active
                    </Button>
                  )}
                  <Link
                    to={`/u/${userId}/plans/${plan.id}`}
                    className="inline-flex min-h-11 items-center rounded-lg border border-border bg-surface-raised px-4 py-2.5 text-sm hover:bg-surface-hover"
                  >
                    Edit
                  </Link>
                  <Button onClick={() => duplicate.mutate(plan.id)} disabled={duplicate.isPending}>
                    Duplicate
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => {
                      // Deleting a plan takes its logged sessions with it.
                      if (!window.confirm(`Delete "${plan.title}" and its logged sessions?`)) return
                      remove.mutate(plan.id)
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </Card>
            </li>
          )
        })}
      </ul>

      <Button variant="primary" className="mt-6 w-full" onClick={() => setFormOpen(true)}>
        New plan
      </Button>

      {formOpen && <NewPlanForm userId={userId} onClose={() => setFormOpen(false)} />}
    </>
  )
}

function NewPlanForm({ userId, onClose }: { userId: number; onClose: () => void }) {
  const createPlan = useCreatePlan(userId)
  const [title, setTitle] = useState('')
  // The days are named at creation, as agreed: a plan is N training days,
  // each with a type. Exercises are attached afterwards in the editor.
  const [days, setDays] = useState<string[]>(['Push', 'Pull', 'Legs'])

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    createPlan.mutate(
      {
        title: title.trim(),
        training_days: days
          .map((workout_type, index) => ({ position: index + 1, workout_type: workout_type.trim() }))
          .filter((day) => day.workout_type !== ''),
      },
      { onSuccess: onClose },
    )
  }

  return (
    <Modal title="New plan" onClose={onClose}>
      <form onSubmit={submit} className="grid gap-4">
        <Field
          label="Title"
          autoFocus
          value={title}
          maxLength={100}
          placeholder="Push/Pull/Legs"
          onChange={(e) => setTitle(e.target.value)}
        />

        <div>
          <span className="mb-1.5 block text-sm text-content-muted">Training days</span>
          <div className="grid gap-2">
            {days.map((day, index) => (
              <div key={index} className="flex gap-2">
                <input
                  className="min-h-11 w-full rounded-lg border border-border bg-surface px-3 py-2.5 focus:border-accent focus:outline-none"
                  value={day}
                  placeholder={`Day ${index + 1}`}
                  onChange={(e) =>
                    setDays(days.map((value, i) => (i === index ? e.target.value : value)))
                  }
                />
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setDays(days.filter((_, i) => i !== index))}
                >
                  Remove
                </Button>
              </div>
            ))}
          </div>
          <Button type="button" className="mt-2" onClick={() => setDays([...days, ''])}>
            Add day
          </Button>
        </div>

        {createPlan.error && (
          <p className="text-sm text-negative">{(createPlan.error as Error).message}</p>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={title.trim() === '' || createPlan.isPending}
          >
            {createPlan.isPending ? 'Creating…' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
