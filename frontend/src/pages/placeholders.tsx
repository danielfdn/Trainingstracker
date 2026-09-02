import { Placeholder } from '../components/Placeholder'

/**
 * The screens phase 4 fills in. They exist as routes now so the navigation in
 * PLAN.md §"Phase 4 — Screens" can be walked through end to end.
 */

export const PlanList = () => (
  <Placeholder title="Workout plans" description="List of plans, plus creating a new one." />
)

export const PlanEditor = () => (
  <Placeholder
    title="Plan editor"
    description="Training days, exercises from the catalog, targets like 3×8-10."
  />
)

export const ActivePlan = () => (
  <Placeholder title="Active plan" description="Choose the one plan that is currently in effect." />
)

export const WorkoutPicker = () => (
  <Placeholder
    title="Start a workout"
    description="The active plan's training days, plus Custom below the divider."
  />
)

export const LiveWorkout = () => (
  <Placeholder
    title="Live workout"
    description="Timer, exercise list and set entry — built for one-handed use on a phone."
  />
)

export const TrainingLog = () => (
  <Placeholder title="Training log" description="Every past session, newest first." />
)

export const Progress = () => (
  <Placeholder
    title="Progress"
    description="Compare two months, e.g. 09/25 vs 04/26, exercise by exercise."
  />
)

export const UserSettings = () => (
  <Placeholder title="Edit user data" description="Name, age and weight." />
)
