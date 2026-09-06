import { formatWeight } from '../api/types'

/** Pure helpers behind the set list. Separate from the components so the
 *  rendering file stays fast-refreshable. */

/**
 * Groups sets by the slot of the training day they were logged against.
 *
 * A plan may list the same exercise twice — heavy at the start, light at the
 * end — and those are two different things to look back on, so they stay
 * apart here. Sets without a slot (custom sessions, exercises added on the
 * spot, and everything logged before slots existed) fall back to grouping by
 * exercise, which is exactly how the whole log behaved before.
 *
 * `occurrence` counts how often the same exercise has already appeared, so
 * the screen can label repeats "Bench Press (2)" instead of showing what
 * looks like the same card twice.
 */
export function groupBySlot<
  T extends { exercise_id: number; training_day_exercise_id?: number | null },
>(sets: T[]): { key: string; exerciseId: number; occurrence: number; sets: T[] }[] {
  const groups: { key: string; exerciseId: number; occurrence: number; sets: T[] }[] = []
  for (const set of sets) {
    // Slotless sets of one exercise all belong together; slotted ones are
    // separated by their slot even when the exercise is the same.
    const key =
      set.training_day_exercise_id == null
        ? `exercise-${set.exercise_id}`
        : `slot-${set.training_day_exercise_id}`
    const group = groups.find((entry) => entry.key === key)
    if (group) {
      group.sets.push(set)
      continue
    }
    groups.push({
      key,
      exerciseId: set.exercise_id,
      occurrence: groups.filter((entry) => entry.exerciseId === set.exercise_id).length + 1,
      sets: [set],
    })
  }
  return groups
}

/** How many groups this exercise has in the list — 1 means no need to number. */
export function occurrencesOf(
  groups: { exerciseId: number }[],
  exerciseId: number,
): number {
  return groups.filter((group) => group.exerciseId === exerciseId).length
}

/** "8 × 82.5 kg", or just "8 reps" for a bodyweight exercise. */
export function formatSet(repetitions: number, weight: string | number | null | undefined): string {
  if (weight === null || weight === undefined) return `${repetitions} reps`
  return `${repetitions} × ${formatWeight(weight)}`
}
