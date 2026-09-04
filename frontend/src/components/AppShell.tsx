import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Link, Outlet } from 'react-router-dom'

import { userQuery } from '../api/queries'
import { forgetProfile, rememberProfile } from '../lib/lastProfile'
import { useUserId } from '../lib/useUserId'

/**
 * Frame around every screen below `/u/:userId`.
 *
 * Routing is by id (`/u/3`) because `appuser.name` is not unique; the name is
 * only ever displayed. The header resolves it once here, so no screen has to
 * fetch the user just to show a title.
 */
export function AppShell() {
  const userId = useUserId()
  const { data: user } = useQuery(userQuery(userId))

  // So the installed app can open straight into this profile next launch.
  useEffect(() => rememberProfile(userId), [userId])

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 border-b border-border bg-surface/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between gap-4 px-4">
          <Link
            to={`/u/${userId}`}
            className="truncate text-sm font-medium tracking-tight hover:text-accent"
          >
            {user?.name ?? '…'}
          </Link>
          <Link
            to="/"
            className="shrink-0 text-sm text-content-muted hover:text-content"
            // Clearing it first, or the installed app would jump right back
            // into the profile you just asked to leave.
            onClick={forgetProfile}
          >
            Switch profile
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-6 sm:py-10">
        <Outlet />
      </main>
    </div>
  )
}
