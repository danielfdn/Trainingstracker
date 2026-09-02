import { PageTitle } from './ui'

/**
 * Stand-in for a screen that phase 4 will build.
 *
 * The route exists and is reachable from the menu already, so navigation can
 * be walked end to end before any of the screens are written.
 */
export function Placeholder({ title, description }: { title: string; description: string }) {
  return (
    <>
      <PageTitle subtitle={description}>{title}</PageTitle>
      <p className="rounded-card border border-dashed border-border p-6 text-center text-sm text-content-faint">
        Coming in phase 4.
      </p>
    </>
  )
}
