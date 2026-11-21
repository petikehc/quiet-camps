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

export function fieldErrors(error: unknown): ValidationProblem['errors'] {
  if (error instanceof ApiError && error.problem && 'errors' in error.problem) {
    return error.problem.errors
  }
  return []
}
