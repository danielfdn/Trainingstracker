/**
 * The workout you are in the middle of, stored on the device.
 *
 * Sets are written here the moment you enter them, before anything is sent to
 * the server. That solves three problems at once:
 *
 *  - **Offline.** Gyms have bad reception. A failed request mid-workout would
 *    otherwise lose the set you just did, at the worst possible moment.
 *  - **Resume.** Close the tab, lock the phone, run out of battery — the
 *    session is still here when you come back.
 *  - **Ordering.** Posting sets one by one needs a workout id the server has
 *    not issued yet while you are offline. Keeping the whole session together
 *    and sending it once, on finish, avoids that entirely.
 *
 * localStorage rather than IndexedDB: a session is a few kilobytes, and a
 * synchronous read keeps the live screen free of loading states.
 */

const KEY = 'trainingstracker.draft'

export type DraftSet = {
  /** Local row id — the server assigns real ids only after the sync. */
  key: string
  exercise_id: number
  repetitions: number
  weight: number | null
  /**
   * Which slot of the training day this set belongs to.
   *
   * The same exercise may appear twice on a day — heavy first, light last —
   * and the two are only distinguishable by their slot. null for a custom
   * session and for exercises added on the spot, which have no slot.
   *
   * Optional on the type so a draft written by an older version of the app
   * still loads: those sets simply have no slot.
   */
  training_day_exercise_id?: number | null
}

export type WorkoutDraft = {
  /** Sent as client_uuid so a retried sync cannot create a second session. */
  client_uuid: string
  user_id: number
  workout_plan_id: number
  /** null means a custom session — the analysis skips those by design. */
  training_day_id: number | null
  workout_type: string
  started_at: string
  sets: DraftSet[]
  comment: string
}

export function loadDraft(): WorkoutDraft | null {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as WorkoutDraft) : null
  } catch {
    // A corrupted draft must never block the app from starting.
    return null
  }
}

export function saveDraft(draft: WorkoutDraft): void {
  localStorage.setItem(KEY, JSON.stringify(draft))
}

export function clearDraft(): void {
  localStorage.removeItem(KEY)
}

export function newDraft(input: {
  user_id: number
  workout_plan_id: number
  training_day_id: number | null
  workout_type: string
}): WorkoutDraft {
  return {
    client_uuid: crypto.randomUUID(),
    started_at: new Date().toISOString(),
    sets: [],
    comment: '',
    ...input,
  }
}

/** Elapsed seconds, computed from the start timestamp rather than counted.
 *  A counting timer would silently be wrong every time the phone sleeps. */
export function elapsedSeconds(startedAt: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000))
}

export function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const pad = (value: number) => String(value).padStart(2, '0')
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`
}
