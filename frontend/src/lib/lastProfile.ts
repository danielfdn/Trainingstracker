/**
 * The profile you used last.
 *
 * `start_url` is "/", so every launch of the installed app lands on the
 * profile picker. For a single-person tracker that is one tap of friction on
 * every single use, so the installed app skips straight to the profile you
 * were last in. The picker stays one tap away via "Switch profile" in the
 * header — and in a normal browser tab nothing is skipped at all, because
 * there the picker is a page you navigated to on purpose.
 */

const KEY = 'trainingstracker.lastProfile'

export function rememberProfile(userId: number): void {
  localStorage.setItem(KEY, String(userId))
}

export function lastProfile(): number | null {
  const raw = localStorage.getItem(KEY)
  const parsed = Number(raw)
  return raw !== null && Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

export function forgetProfile(): void {
  localStorage.removeItem(KEY)
}

/** True when running from the home screen rather than in a browser tab. */
export function isInstalled(): boolean {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    // iOS predates the standard and still reports it its own way.
    (window.navigator as { standalone?: boolean }).standalone === true
  )
}
