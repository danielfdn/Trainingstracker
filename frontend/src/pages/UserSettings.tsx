import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useDeleteUser, useUpdateUser } from '../api/mutations'
import { userQuery } from '../api/queries'
import { parseDecimalInput } from '../api/types'
import { Button, Card, ErrorNote, Field, Loading, PageTitle } from '../components/ui'
import { useUserId } from '../lib/useUserId'

/** `/u/:userId/settings` — name, age and weight. */
export function UserSettings() {
  const userId = useUserId()
  const navigate = useNavigate()
  const { data: user, isPending, error, refetch } = useQuery(userQuery(userId))
  const updateUser = useUpdateUser(userId)
  const deleteUser = useDeleteUser()

  const [draft, setDraft] = useState<{ name: string; age: string; weight: string } | null>(null)
  const [saved, setSaved] = useState(false)

  if (isPending) return <Loading />
  if (error) return <ErrorNote error={error} onRetry={() => void refetch()} />

  // Initialised from the loaded user the first time it is rendered.
  const form = draft ?? {
    name: user.name,
    age: String(user.age),
    weight: String(user.weight),
  }
  const set = (patch: Partial<typeof form>) => {
    setDraft({ ...form, ...patch })
    setSaved(false)
  }

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    updateUser.mutate(
      { name: form.name.trim(), age: Number(form.age), weight: parseDecimalInput(form.weight) ?? 0 },
      { onSuccess: () => setSaved(true) },
    )
  }

  return (
    <>
      <PageTitle subtitle="Your profile data.">Settings</PageTitle>

      <Card>
        <form onSubmit={submit} className="grid gap-4">
          <Field label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Age"
              type="number"
              inputMode="numeric"
              value={form.age}
              onChange={(e) => set({ age: e.target.value })}
            />
            <Field
              label="Weight (kg)"
              // See parseDecimalInput: type="number" drops comma decimals.
              type="text"
              inputMode="decimal"
              value={form.weight}
              onChange={(e) => set({ weight: e.target.value })}
            />
          </div>

          {/* The one thing about this screen that is not obvious. */}
          <p className="text-xs text-content-faint">
            Your weight is stored with every workout you log from now on. Changing it here does not
            rewrite past sessions — the training log keeps the weight of the day.
          </p>

          {updateUser.error && (
            <p className="text-sm text-negative">{(updateUser.error as Error).message}</p>
          )}

          <div className="flex items-center justify-end gap-3">
            {saved && <span className="text-sm text-positive">Saved</span>}
            <Button type="submit" variant="primary" disabled={updateUser.isPending}>
              {updateUser.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </form>
      </Card>

      <Card className="mt-6">
        <h2 className="font-medium">Delete profile</h2>
        <p className="mt-1 text-sm text-content-muted">
          Removes {user.name} with every plan, exercise and logged session. This cannot be undone.
        </p>
        <Button
          variant="danger"
          className="mt-4"
          disabled={deleteUser.isPending}
          onClick={() => {
            // The one place a confirm is worth it: nothing here is reversible.
            if (!window.confirm(`Delete ${user.name} and all training data?`)) return
            deleteUser.mutate(userId, { onSuccess: () => navigate('/') })
          }}
        >
          Delete profile
        </Button>
      </Card>

      {/* Which bundle this device is actually running. An installed PWA can
          keep serving an old one long after the server has been updated, and
          without this there is no way to tell that from the outside. */}
      <p className="mt-6 text-center text-xs text-content-faint tabular">
        Version {__BUILD_ID__}
      </p>
    </>
  )
}
