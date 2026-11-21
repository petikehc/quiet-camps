// Compile-time checks that the generated types say what the API does. Nothing here runs:
// `pnpm typecheck` fails if a type drifts, or if an @ts-expect-error line starts compiling.
import { api, type Problem, type ValidationProblem } from './client'

type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends <T>() => T extends B ? 1 : 2 ? true : false

export async function campgroundOrProblem(campgroundId: number): Promise<string> {
  const { data, error } = await api.GET('/campgrounds/{campground_id}', {
    params: { path: { campground_id: campgroundId } },
  })
  const errorIsAProblem: Equal<typeof error, Problem | ValidationProblem | undefined> = true
  if (error) return `${error.status} ${error.detail} ${errorIsAProblem}`
  return data.name // narrowed: no error means data
}

export async function searchNeedsDates(): Promise<void> {
  // @ts-expect-error arrive and depart are required
  await api.GET('/campgrounds/quiet', { params: { query: { limit: 10 } } })
  await api.GET('/campgrounds/quiet', {
    // @ts-expect-error limit is a number
    params: { query: { arrive: '2027-03-26', depart: '2027-03-29', limit: '10' } },
  })
}

export async function yearValuesAreNumbers(): Promise<number | undefined> {
  const { data } = await api.GET('/year/{year}', { params: { path: { year: 2025 } } })
  const values: number[] | undefined = data?.values
  return values?.[0]
}
