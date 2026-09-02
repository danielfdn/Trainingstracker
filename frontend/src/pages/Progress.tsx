import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { logMonthsQuery, progressQuery } from '../api/queries'
import type { ExerciseProgress } from '../api/types'
import { toNumber } from '../api/types'
import { Card, EmptyState, ErrorNote, Loading, PageTitle, Select } from '../components/ui'
import { useUserId } from '../lib/useUserId'

/**
 * `/u/:userId/log/progress` — spec view two: 09/25 vs 04/26.
 *
 * Both months come from the months that actually contain sessions, so an
 * empty month cannot be picked.
 */
export function Progress() {
  const userId = useUserId()
  const { data: months, isPending, error, refetch } = useQuery(logMonthsQuery(userId))
  const [a, setA] = useState<string>('')
  const [b, setB] = useState<string>('')

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  if (months.length < 2) {
    return (
      <>
        <PageTitle>Progress</PageTitle>
        <EmptyState title="Not enough history yet">
          Two months with logged sessions are needed for a comparison.
        </EmptyState>
      </>
    )
  }

  // Default to the oldest against the newest — the widest span available.
  const monthA = a || months[months.length - 1].month
  const monthB = b || months[0].month

  return (
    <>
      <PageTitle subtitle="Pick any two months.">Progress</PageTitle>

      <div className="mb-6 grid grid-cols-2 gap-3">
        <Select label="From" value={monthA} onChange={(e) => setA(e.target.value)}>
          {months.map((month) => (
            <option key={month.month} value={month.month}>
              {month.label} ({month.workout_count})
            </option>
          ))}
        </Select>
        <Select label="To" value={monthB} onChange={(e) => setB(e.target.value)}>
          {months.map((month) => (
            <option key={month.month} value={month.month}>
              {month.label} ({month.workout_count})
            </option>
          ))}
        </Select>
      </div>

      <Comparison userId={userId} monthA={monthA} monthB={monthB} />
    </>
  )
}

function Comparison({
  userId,
  monthA,
  monthB,
}: {
  userId: number
  monthA: string
  monthB: string
}) {
  const { data, isPending, error, refetch } = useQuery(progressQuery(userId, monthA, monthB))

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  if (data.exercises.length === 0) {
    return <EmptyState title="No exercises in either month" />
  }

  return (
    <>
      <div className="grid gap-3">
        {data.exercises.map((exercise) => (
          <ExerciseRow
            key={exercise.exercise_id}
            exercise={exercise}
            labelA={data.label_a}
            labelB={data.label_b}
          />
        ))}
      </div>

      {data.excluded_custom_workouts > 0 && (
        <p className="mt-6 text-sm text-content-faint">
          {data.excluded_custom_workouts} custom session
          {data.excluded_custom_workouts === 1 ? '' : 's'} left out of this comparison — improvised
          workouts would distort the trend. They are still in your log.
        </p>
      )}
    </>
  )
}

function ExerciseRow({
  exercise,
  labelA,
  labelB,
}: {
  exercise: ExerciseProgress
  labelA: string
  labelB: string
}) {
  // Bodyweight exercises progress on reps; weighted ones on the best set.
  const metric = exercise.weighted ? 'best_weight' : 'best_reps'
  const unit = exercise.weighted ? ' kg' : ' reps'
  const valueA = toNumber(exercise.month_a?.[metric])
  const valueB = toNumber(exercise.month_b?.[metric])
  const delta = toNumber(exercise.delta[metric])

  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="min-w-0 truncate font-medium">{exercise.title}</h2>
        <Delta value={delta} unit={unit} />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <Side label={labelA} value={valueA} unit={unit} stats={exercise.month_a} />
        <Side label={labelB} value={valueB} unit={unit} stats={exercise.month_b} />
      </div>
    </Card>
  )
}

function Side({
  label,
  value,
  unit,
  stats,
}: {
  label: string
  value: number | null
  unit: string
  stats: ExerciseProgress['month_a']
}) {
  return (
    <div className="rounded-lg bg-surface px-3 py-2">
      <p className="text-xs text-content-faint tabular">{label}</p>
      <p className="mt-0.5 text-lg tabular">
        {value === null ? '–' : `${value.toLocaleString('de-DE')}${unit}`}
      </p>
      {stats && (
        <p className="mt-0.5 text-xs text-content-faint tabular">
          ⌀ {stats.avg_reps ?? '–'} reps · {stats.session_count} sessions
        </p>
      )}
    </div>
  )
}

/**
 * The change between the two months.
 *
 * Improvement is green; a regression is deliberately NOT red. Red means an
 * error everywhere else in the app, and it is the accent's neighbour — a
 * falling number reads perfectly well as a sign and an arrow, without
 * claiming that something went wrong.
 */
function Delta({ value, unit }: { value: number | null; unit: string }) {
  if (value === null) {
    return <span className="shrink-0 text-sm text-content-faint">no comparison</span>
  }
  if (value === 0) {
    return <span className="shrink-0 text-sm text-content-muted tabular">unchanged</span>
  }
  const up = value > 0
  return (
    <span
      className={`shrink-0 text-sm tabular ${up ? 'text-positive' : 'text-content-muted'}`}
    >
      {up ? '↑' : '↓'} {up ? '+' : ''}
      {value.toLocaleString('de-DE')}
      {unit}
    </span>
  )
}
