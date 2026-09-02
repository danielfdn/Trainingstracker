import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { usersQuery } from '../api/queries'
import { EmptyState, ErrorNote, Loading, PageTitle } from '../components/ui'

/** Landing page: pick a profile. The spec's first screen. */
export function ProfilePicker() {
  const { data: users, isPending, error, refetch } = useQuery(usersQuery())

  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col justify-center px-4 py-10">
      <PageTitle subtitle="Choose a profile to continue.">Trainingstracker</PageTitle>

      {isPending && <Loading label="Loading profiles…" />}
      {error && <ErrorNote error={error} onRetry={() => void refetch()} />}

      {users && users.length === 0 && (
        <EmptyState title="No profiles yet">
          Seed the database with <code className="text-content">uv run python scripts/seed.py</code>{' '}
          or create a user via the API.
        </EmptyState>
      )}

      {users && users.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2">
          {users.map((user) => (
            <li key={user.id}>
              <Link
                to={`/u/${user.id}`}
                className="flex items-center gap-3 rounded-card border border-border bg-surface-raised p-4 transition-colors hover:border-border-strong hover:bg-surface-hover"
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-hover text-sm font-medium uppercase">
                  {user.name.slice(0, 2)}
                </span>
                <span className="min-w-0">
                  <span className="block truncate font-medium">{user.name}</span>
                  <span className="block text-sm text-content-muted tabular">
                    {user.age} years · {user.weight} kg
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
