import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { usersQuery } from '../api/queries'
import { parseDecimalInput } from '../api/types'
import { useCreateUser } from '../api/mutations'
import { isInstalled, lastProfile } from '../lib/lastProfile'
import { Button, ErrorNote, Field, Loading, Modal, PageTitle } from '../components/ui'

/** Landing page: pick a profile, or create the first one. */
export function ProfilePicker() {
  const { data: users, isPending, error, refetch } = useQuery(usersQuery())
  const [formOpen, setFormOpen] = useState(false)
  const navigate = useNavigate()

  // Launched from the home screen, go straight to the profile you were last
  // in — but only once the list confirms it still exists, so a deleted
  // profile cannot strand the app on a dead route.
  const remembered = lastProfile()
  useEffect(() => {
    if (!isInstalled() || remembered === null || users === undefined) return
    if (users.some((user) => user.id === remembered)) {
      navigate(`/u/${remembered}`, { replace: true })
    }
  }, [remembered, users, navigate])

  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col justify-center px-4 py-10">
      <PageTitle subtitle="Choose a profile to continue.">Trainingstracker</PageTitle>

      {isPending && <Loading label="Loading profiles…" />}
      {error && <ErrorNote error={error} onRetry={() => void refetch()} />}

      {users && (
        <>
          <ul className="grid gap-3 sm:grid-cols-2">
            {users.map((user) => (
              <li key={user.id}>
                <Link
                  to={`/u/${user.id}`}
                  className="flex items-center gap-3 rounded-card border border-border bg-surface-raised p-4 transition-colors hover:border-border-strong hover:bg-surface-hover"
                >
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent-muted text-sm font-medium uppercase text-accent">
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

          <Button variant="primary" className="mt-6 w-full" onClick={() => setFormOpen(true)}>
            New profile
          </Button>

          {users.length === 0 && (
            <p className="mt-4 text-center text-sm text-content-faint">
              No profiles yet — create one to get started.
            </p>
          )}
        </>
      )}

      {formOpen && <NewProfileForm onClose={() => setFormOpen(false)} />}
    </div>
  )
}

function NewProfileForm({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const createUser = useCreateUser()
  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [weight, setWeight] = useState('')

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    createUser.mutate(
      { name: name.trim(), age: Number(age), weight: parseDecimalInput(weight) ?? 0 },
      // Straight into the new profile — creating one is always the first
      // step of using it.
      { onSuccess: (user) => navigate(`/u/${user.id}`) },
    )
  }

  const complete = name.trim() !== '' && age !== '' && weight !== ''

  return (
    <Modal title="New profile" onClose={onClose}>
      <form onSubmit={submit} className="grid gap-4">
        <Field
          label="Name"
          value={name}
          autoFocus
          maxLength={100}
          onChange={(e) => setName(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-4">
          <Field
            label="Age"
            type="number"
            inputMode="numeric"
            min={1}
            max={129}
            value={age}
            onChange={(e) => setAge(e.target.value)}
          />
          <Field
            label="Weight (kg)"
            // See parseDecimalInput: type="number" drops comma decimals.
            type="text"
            inputMode="decimal"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            hint="Recorded with each workout"
          />
        </div>

        {createUser.error && (
          <p className="text-sm text-negative">{(createUser.error as Error).message}</p>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={!complete || createUser.isPending}>
            {createUser.isPending ? 'Creating…' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
