import { isRouteErrorResponse, useRouteError } from 'react-router-dom'

import { LinkButton, PageTitle } from '../components/ui'

/**
 * Shown for an unknown path and as the router's error element, so a thrown
 * error (an invalid user id, say) lands on a page instead of a blank screen.
 */
export function NotFound() {
  const error = useRouteError()
  const message = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : 'This page does not exist.'

  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col justify-center px-4 text-center">
      <PageTitle subtitle={message}>Not found</PageTitle>
      <div>
        <LinkButton to="/" variant="primary">
          Back to profiles
        </LinkButton>
      </div>
    </div>
  )
}
