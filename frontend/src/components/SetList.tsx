import type { ReactNode } from 'react'

import { Card } from './ui'

/**
 * The set-list skeleton, shared by the live workout and the session detail.
 *
 * Both screens show the same thing — an exercise, then its numbered sets —
 * and differ only in whether a row is an input or a reading. Keeping the
 * frame here means the history cannot drift into looking like a different
 * app than the screen the sets were entered on.
 *
 * The grouping and formatting helpers live in `lib/sets.ts`.
 */

/** One exercise: title, an optional note on the right, then its rows. */
export function ExerciseCard({
  title,
  meta,
  children,
  footer,
}: {
  title: string
  meta?: ReactNode
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="min-w-0 truncate font-medium">{title}</h2>
        {meta && <span className="shrink-0 text-sm text-content-muted tabular">{meta}</span>}
      </div>

      <div className="mt-3 grid gap-2">{children}</div>

      {footer}
    </Card>
  )
}

/** A single set row, with the shared number gutter. */
export function SetRow({ index, children }: { index: number; children: ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-6 shrink-0 text-sm text-content-faint tabular">{index + 1}</span>
      {children}
    </div>
  )
}
