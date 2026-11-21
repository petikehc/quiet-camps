import type { Problem, ValidationProblem } from './client'

// openapi-fetch returns errors instead of throwing them; TanStack Query needs a throw to show
// its error state. This carries the API's problem+json body, when there is one, to the page.
export class ApiError extends Error {
  readonly status: number
  readonly problem: Problem | ValidationProblem | undefined

  constructor(status: number, problem: Problem | ValidationProblem | undefined) {
    super(problem?.detail ?? `The API answered ${status}`)
    this.status = status
    this.problem = problem
  }
}

// An openapi-fetch call's data, or its error thrown as an ApiError.
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: Problem | ValidationProblem; response: Response }>,
): Promise<T> {
  const { data, error, response } = await request
  if (data === undefined) throw new ApiError(response.status, error)
  return data
}

// A 4xx won't change on a retry, so only network errors and 5xx are retried.
export function shouldRetry(failures: number, error: Error): boolean {
  return !(error instanceof ApiError && error.status < 500) && failures < 3
}

export function fieldErrors(error: unknown): ValidationProblem['errors'] {
  if (error instanceof ApiError && error.problem && 'errors' in error.problem) {
    return error.problem.errors
  }
  return []
}
