import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

/**
 * The small set of primitives every screen shares.
 *
 * Kept in one file on purpose: they are a handful of class strings, and one
 * file makes the visual language easy to read in one go.
 */

/** Minimum 44px tap targets — the live workout screen is used one-handed. */
const tapTarget = 'min-h-11 px-4 py-2.5'

const variants = {
  primary: 'bg-accent text-accent-content hover:bg-accent-hover font-medium',
  secondary:
    'bg-surface-raised text-content border border-border hover:bg-surface-hover hover:border-border-strong',
  ghost: 'text-content-muted hover:text-content hover:bg-surface-hover',
  danger: 'bg-surface-raised text-negative border border-border hover:border-negative',
} as const

export type Variant = keyof typeof variants

const buttonBase = `inline-flex items-center justify-center gap-2 rounded-lg text-sm transition-colors disabled:opacity-50 disabled:pointer-events-none ${tapTarget}`

export function Button({
  variant = 'secondary',
  className = '',
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button className={`${buttonBase} ${variants[variant]} ${className}`} {...props} />
}

export function LinkButton({
  to,
  variant = 'secondary',
  className = '',
  children,
}: {
  to: string
  variant?: Variant
  className?: string
  children: ReactNode
}) {
  return (
    <Link to={to} className={`${buttonBase} ${variants[variant]} ${className}`}>
      {children}
    </Link>
  )
}

export function Card({ className = '', children }: { className?: string; children: ReactNode }) {
  return (
    <div
      className={`rounded-card border border-border bg-surface-raised p-4 sm:p-5 ${className}`}
    >
      {children}
    </div>
  )
}

/** A full-width card that is itself the tap target — the menu row pattern. */
export function CardLink({
  to,
  title,
  description,
}: {
  to: string
  title: string
  description?: string
}) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between gap-4 rounded-card border border-border bg-surface-raised p-4 transition-colors hover:border-border-strong hover:bg-surface-hover sm:p-5"
    >
      <span className="min-w-0">
        <span className="block truncate font-medium">{title}</span>
        {description && (
          <span className="mt-0.5 block truncate text-sm text-content-muted">{description}</span>
        )}
      </span>
      <span aria-hidden className="shrink-0 text-content-faint">
        ›
      </span>
    </Link>
  )
}

export function PageTitle({ children, subtitle }: { children: ReactNode; subtitle?: ReactNode }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{children}</h1>
      {subtitle && <p className="mt-1 text-sm text-content-muted">{subtitle}</p>}
    </header>
  )
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <p role="status" className="py-10 text-center text-sm text-content-muted">
      {label}
    </p>
  )
}

export function ErrorNote({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : 'Something went wrong'
  return (
    <Card className="border-negative/40">
      <p className="text-sm text-negative">{message}</p>
      <p className="mt-1 text-sm text-content-muted">
        Check that the backend is reachable and try again.
      </p>
      {onRetry && (
        <Button className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </Card>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Card className="border-dashed text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-2 text-sm text-content-muted">{children}</div>}
    </Card>
  )
}

const fieldBase =
  'w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-content placeholder:text-content-faint focus:border-accent focus:outline-none min-h-11'

export function Field({
  label,
  hint,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm text-content-muted">{label}</span>
      <input className={fieldBase} {...props} />
      {hint && <span className="mt-1 block text-xs text-content-faint">{hint}</span>}
    </label>
  )
}

export function TextArea({
  label,
  hint,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm text-content-muted">{label}</span>
      <textarea className={`${fieldBase} min-h-24 resize-y py-2.5`} {...props} />
      {hint && <span className="mt-1 block text-xs text-content-faint">{hint}</span>}
    </label>
  )
}

export function Select({
  label,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm text-content-muted">{label}</span>
      <select className={fieldBase} {...props}>
        {children}
      </select>
    </label>
  )
}

/** Centred dialog. Used for the short create/edit forms. */
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-4 sm:items-center"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-label={title}
        className="w-full max-w-md rounded-card border border-border bg-surface-raised p-5"
        // The backdrop closes the dialog; a click inside it must not.
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="mb-4 text-lg font-semibold">{title}</h2>
        {children}
      </div>
    </div>
  )
}

/**
 * Bottom toast carrying an undo action.
 *
 * Used instead of a confirmation dialog for reversible writes: confirming
 * every marked-as-missed session would cost more than the rare mistake does.
 */
export function UndoToast({
  message,
  onUndo,
  onDismiss,
}: {
  message: string
  onUndo: () => void
  onDismiss: () => void
}) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000)
    return () => clearTimeout(timer)
  }, [onDismiss])

  return (
    <div className="fixed inset-x-0 bottom-4 z-50 flex justify-center px-4">
      <div className="flex items-center gap-4 rounded-full border border-border bg-surface-raised py-2 pl-5 pr-2 shadow-lg">
        <span className="text-sm">{message}</span>
        <button
          onClick={onUndo}
          className="rounded-full px-3 py-1.5 text-sm font-medium text-accent hover:bg-surface-hover"
        >
          Undo
        </button>
      </div>
    </div>
  )
}
