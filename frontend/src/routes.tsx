import { createBrowserRouter } from 'react-router-dom'

import { AppShell } from './components/AppShell'
import { ExerciseCatalog } from './pages/ExerciseCatalog'
import { LiveWorkout } from './pages/LiveWorkout'
import { MainMenu } from './pages/MainMenu'
import { NotFound } from './pages/NotFound'
import { PlanEditor } from './pages/PlanEditor'
import { PlanList } from './pages/PlanList'
import { ProfilePicker } from './pages/ProfilePicker'
import { Progress } from './pages/Progress'
import { TrainingLog } from './pages/TrainingLog'
import { UserSettings } from './pages/UserSettings'
import { WorkoutPicker } from './pages/WorkoutPicker'

/**
 * The navigation from PLAN.md, routed by user id.
 *
 * `/u/:userId` rather than `/:name` from the spec sketch: `appuser.name` is not
 * unique, so a name cannot address a profile. The name is displayed only.
 */
export const router = createBrowserRouter([
  { path: '/', element: <ProfilePicker />, errorElement: <NotFound /> },
  {
    path: '/u/:userId',
    element: <AppShell />,
    errorElement: <NotFound />,
    children: [
      { index: true, element: <MainMenu /> },
      { path: 'plans', element: <PlanList /> },
      { path: 'plans/:planId', element: <PlanEditor /> },
      { path: 'exercises', element: <ExerciseCatalog /> },
      { path: 'workout', element: <WorkoutPicker /> },
      // One live screen, not one per workout id: the session lives on the
      // device until it is finished and synced.
      { path: 'workout/live', element: <LiveWorkout /> },
      { path: 'log', element: <TrainingLog /> },
      { path: 'log/progress', element: <Progress /> },
      { path: 'settings', element: <UserSettings /> },
    ],
  },
  { path: '*', element: <NotFound /> },
])
