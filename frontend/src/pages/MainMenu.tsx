import { useQuery } from '@tanstack/react-query'

import { userPlansQuery, userQuery } from '../api/queries'
import { useUserId } from '../lib/useUserId'
import { CardLink, ErrorNote, Loading, PageTitle } from '../components/ui'

/** `/u/:userId` — the option menu the spec lists for a chosen profile. */
export function MainMenu() {
  const userId = useUserId()
  const { data: user, isPending, error, refetch } = useQuery(userQuery(userId))
  const { data: plans } = useQuery(userPlansQuery(userId))

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  const activePlan = plans?.find((plan) => plan.id === user.active_workout_plan_id)
  const base = `/u/${userId}`

  return (
    <>
      <PageTitle subtitle={activePlan ? `Active plan: ${activePlan.title}` : 'No active plan yet'}>
        {user.name}
      </PageTitle>

      <nav className="grid gap-3">
        <CardLink
          to={`${base}/workout`}
          title="Start a workout"
          description="Pick today's training day, then log your sets"
        />
        <CardLink
          to={`${base}/plans`}
          title="Workout plans"
          description={plans ? `${plans.length} plan(s)` : 'Create and edit plans'}
        />
        <CardLink
          to={`${base}/active-plan`}
          title="Active plan"
          description={activePlan?.title ?? 'None selected'}
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
