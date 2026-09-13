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
 *  - **Pause.** Anything that is not training — a phone call, a machine in
 *    use, a failed sync you have to wait out — is held here as paused time
 *    and subtracted from the duration on finish.
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
  /**
   * When the current pause began, or null while the clock runs.
   *
   * Two fields rather than one, because an open pause and a finished one are
   * different things: this is the open one, `paused_seconds` the sum of the
   * closed ones. On resume the open pause moves into the sum.
   *
   * Both optional on the type so a draft written before pausing existed still
   * loads — such a session simply never paused.
   */
  paused_at?: string | null
  /** Total of all finished pauses, in seconds. */
  paused_seconds?: number
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
    paused_at: null,
    paused_seconds: 0,
    sets: [],
    comment: '',
    ...input,
  }
}

/** Whether the clock is currently stopped. */
export function isPaused(draft: WorkoutDraft): boolean {
  return draft.paused_at != null
}

/**
 * Training seconds so far: wall time since the start, minus every pause.
 *
 * Computed from timestamps rather than counted up by a timer — a counter
 * would silently be wrong every time the phone sleeps. While a pause is open
 * the clock is frozen at the moment it began.
 */
export function activeSeconds(draft: WorkoutDraft, now: number = Date.now()): number {
  const until = draft.paused_at != null ? new Date(draft.paused_at).getTime() : now
  const gross = (until - new Date(draft.started_at).getTime()) / 1000
  return Math.max(0, Math.floor(gross) - (draft.paused_seconds ?? 0))
}

/**
 * Total paused time, counting a pause that is still open.
 *
 * What `finish` sends. It does not close the open pause: a sync that fails
 * leaves you paused, so waiting for a connection is not logged as training.
 */
export function totalPausedSeconds(draft: WorkoutDraft, now: number = Date.now()): number {
  const open = draft.paused_at != null ? (now - new Date(draft.paused_at).getTime()) / 1000 : 0
  return (draft.paused_seconds ?? 0) + Math.max(0, Math.floor(open))
}

/** Stops the clock. Already paused is a no-op, so a double tap cannot lose
 *  the start of the first pause. */
export function pauseDraft(draft: WorkoutDraft, now: number = Date.now()): WorkoutDraft {
  if (draft.paused_at != null) return draft
  return { ...draft, paused_at: new Date(now).toISOString() }
}

/** Starts the clock again, moving the open pause into the total. */
export function resumeDraft(draft: WorkoutDraft, now: number = Date.now()): WorkoutDraft {
  if (draft.paused_at == null) return draft
  const held = Math.max(0, Math.floor((now - new Date(draft.paused_at).getTime()) / 1000))
  return { ...draft, paused_at: null, paused_seconds: (draft.paused_seconds ?? 0) + held }
}

export function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const pad = (value: number) => String(value).padStart(2, '0')
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`
}
