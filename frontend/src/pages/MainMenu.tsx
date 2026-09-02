import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { planQuery, userPlansQuery, userQuery, workoutLogQuery } from '../api/queries'
import { CardLink, Card, ErrorNote, Loading, PageTitle } from '../components/ui'
import { elapsedSeconds, formatDuration, loadDraft } from '../lib/draft'
import { useUserId } from '../lib/useUserId'

/** `/u/:userId` — the option menu from the spec, with two panels above it. */
export function MainMenu() {
  const userId = useUserId()
  const { data: user, isPending, error, refetch } = useQuery(userQuery(userId))
  const { data: plans } = useQuery(userPlansQuery(userId))
  const { data: log } = useQuery(workoutLogQuery(userId))
  const activePlanId = user?.active_workout_plan_id ?? null
  const { data: activePlan } = useQuery({
    ...planQuery(activePlanId ?? 0),
    enabled: activePlanId !== null,
  })

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  const base = `/u/${userId}`
  const draft = loadDraft()
  const lastSession = log?.find((entry) => entry.attended)

  // Which day is up next: the one after the most recent attended session,
  // cycling round. A panel that only names the plan would be decoration.
  const days = activePlan?.training_days ?? []
  const lastDayType = log?.find((entry) => entry.attended && !entry.is_custom)?.workout_type
  const lastIndex = days.findIndex((day) => day.workout_type === lastDayType)
  const nextDay = days.length > 0 ? days[(lastIndex + 1) % days.length] : undefined

  return (
    <>
      <PageTitle>{user.name}</PageTitle>

      {/* An open session outranks everything else on this screen. */}
      {draft && draft.user_id === userId && (
        <Link
          to={`${base}/workout/live`}
          className="mb-4 flex items-center justify-between gap-4 rounded-card border border-accent bg-accent-muted p-4 transition-colors hover:bg-accent-muted/70"
        >
          <span className="min-w-0">
            <span className="block font-medium text-accent">Resume {draft.workout_type}</span>
            <span className="mt-0.5 block text-sm text-content-muted tabular">
              running {formatDuration(elapsedSeconds(draft.started_at))} · {draft.sets.length} sets
            </span>
          </span>
          <span aria-hidden className="shrink-0 text-accent">
            ›
          </span>
        </Link>
      )}

      <div className="mb-6 grid gap-3 sm:grid-cols-2">
        <Card>
          <p className="text-xs uppercase tracking-wide text-content-faint">Next up</p>
          {activePlan ? (
            <>
              <p className="mt-1 truncate font-medium">
                {nextDay ? `Day ${nextDay.position} — ${nextDay.workout_type}` : 'No training days'}
              </p>
              <p className="mt-0.5 truncate text-sm text-content-muted">{activePlan.title}</p>
            </>
          ) : (
            <p className="mt-1 text-sm text-content-muted">
              No active plan —{' '}
              <Link to={`${base}/plans`} className="text-accent hover:underline">
                choose one
              </Link>
            </p>
          )}
        </Card>

        <Card>
          <p className="text-xs uppercase tracking-wide text-content-faint">Last session</p>
          {lastSession ? (
            <>
              <p className="mt-1 truncate font-medium">{lastSession.workout_type}</p>
              <p className="mt-0.5 text-sm text-content-muted tabular">
                {daysSince(lastSession.date)} · {lastSession.set_count} sets
              </p>
            </>
          ) : (
            <p className="mt-1 text-sm text-content-muted">Nothing logged yet</p>
          )}
        </Card>
      </div>

      <nav className="grid gap-3">
        <CardLink
          to={`${base}/workout`}
          title="Start a workout"
          description="Pick today's training day, then log your sets"
        />
        <CardLink
          to={`${base}/plans`}
          title="Workout plans"
          description={
            plans
              ? `${plans.length} plan${plans.length === 1 ? '' : 's'}${activePlan ? ` · active: ${activePlan.title}` : ''}`
              : 'Create, duplicate and activate plans'
          }
        />
        <CardLink
          to={`${base}/exercises`}
          title="Exercise catalog"
          description="Rename, add or remove exercises"
        />
        <CardLink
          to={`${base}/log`}
          title="Training log"
          description="History and month-vs-month progress"
        />
        <CardLink to={`${base}/settings`} title="Edit user data" description="Name, age, weight" />
      </nav>
    </>
  )
}

function daysSince(iso: string): string {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (days <= 0) return 'today'
  if (days === 1) return 'yesterday'
  return `${days} days ago`
}
