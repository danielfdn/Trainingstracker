import type { components } from './schema'

/**
 * Short names for the generated schemas.
 *
 * `components['schemas']['UserPublic']` everywhere would be unreadable, and it
 * would also spread the generated file's shape across the whole codebase.
 */
type Schemas = components['schemas']

export type User = Schemas['UserPublic']
export type WorkoutPlan = Schemas['WorkoutPlanPublic']
export type WorkoutPlanWithDays = Schemas['WorkoutPlanWithDays']
export type TrainingDay = Schemas['TrainingDayPublic']
export type Exercise = Schemas['ExercisePublic']
export type TrainingDayExercise = Schemas['TrainingDayExercisePublic']
export type TrainingDayWithExercises = Schemas['TrainingDayWithExercises']
export type Workout = Schemas['WorkoutPublic']
export type ExerciseSet = Schemas['SetPublic']

export type WorkoutLogEntry = Schemas['WorkoutLogEntry']
export type MonthOption = Schemas['MonthOption']
export type ProgressComparison = Schemas['ProgressComparison']
export type ExerciseProgress = Schemas['ExerciseProgress']

/**
 * Weights are `Numeric` in the database, so Pydantic serialises them as JSON
 * strings ("82.50"), never as numbers. Parse before doing arithmetic.
 */
export function toNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * Reads a decimal the user typed, accepting both separators.
 *
 * `formatWeight` prints with a German locale, so the app shows "82,5 kg" —
 * and on a German keyboard the decimal key *is* a comma. A `type="number"`
 * input reports an empty string for "82,5", which silently turned every
 * decimal weight into no weight at all. The inputs are therefore plain text
 * with `inputMode="decimal"`, and the parsing happens here.
 *
 * Returns null for anything that is not a finite number, including "" — the
 * callers all treat null as "no weight given".
 */
export function parseDecimalInput(value: string): number | null {
  const normalised = value.trim().replace(',', '.')
  if (normalised === '') return null
  const parsed = Number(normalised)
  return Number.isFinite(parsed) ? parsed : null
}

/** Formats a weight for display: "82.5 kg", or a dash when there is none. */
export function formatWeight(value: string | number | null | undefined): string {
  const parsed = toNumber(value)
  return parsed === null ? '–' : `${parsed.toLocaleString('de-DE')} kg`
}
