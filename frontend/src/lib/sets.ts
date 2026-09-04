import { formatWeight } from '../api/types'

/** Pure helpers behind the set list. Separate from the components so the
 *  rendering file stays fast-refreshable. */

/**
 * Groups sets by exercise, in the order each exercise first appears.
 *
 * Order matters: sets arrive in the sequence they were logged, and that
 * sequence is the order the workout actually happened in.
 */
export function groupByExercise<T extends { exercise_id: number }>(
  sets: T[],
): { exerciseId: number; sets: T[] }[] {
  const groups: { exerciseId: number; sets: T[] }[] = []
  for (const set of sets) {
    const group = groups.find((entry) => entry.exerciseId === set.exercise_id)
    if (group) group.sets.push(set)
    else groups.push({ exerciseId: set.exercise_id, sets: [set] })
  }
  return groups
}

/** "8 × 82.5 kg", or just "8 reps" for a bodyweight exercise. */
export function formatSet(repetitions: number, weight: string | number | null | undefined): string {
  if (weight === null || weight === undefined) return `${repetitions} reps`
  return `${repetitions} × ${formatWeight(weight)}`
}
