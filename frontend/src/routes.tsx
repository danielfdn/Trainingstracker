import { createBrowserRouter } from 'react-router-dom'

import { AppShell } from './components/AppShell'
import { NotFound } from './pages/NotFound'
import { MainMenu } from './pages/MainMenu'
import { ProfilePicker } from './pages/ProfilePicker'
import {
  ActivePlan,
  LiveWorkout,
  PlanEditor,
  PlanList,
  Progress,
  TrainingLog,
  UserSettings,
  WorkoutPicker,
} from './pages/placeholders'

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
      { path: 'active-plan', element: <ActivePlan /> },
      { path: 'workout', element: <WorkoutPicker /> },
      { path: 'workout/:workoutId', element: <LiveWorkout /> },
      { path: 'log', element: <TrainingLog /> },
      { path: 'log/progress', element: <Progress /> },
      { path: 'settings', element: <UserSettings /> },
    ],
  },
  { path: '*', element: <NotFound /> },
])
