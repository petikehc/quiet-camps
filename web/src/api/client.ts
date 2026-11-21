// The typed client for the FastAPI server. schema.d.ts is generated from api/openapi.json by
// `pnpm api:types`: never edit it by hand.
import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

export type Problem = components['schemas']['Problem']
export type ValidationProblem = components['schemas']['ValidationProblem']

// In development Vite proxies /api to the API on port 8000 (vite.config.ts).
export const api = createClient<paths>({ baseUrl: '/api' })
