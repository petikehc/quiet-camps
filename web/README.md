# Quiet Camps web

Vite + React + TypeScript, calling the FastAPI server through a typed client.

```sh
pnpm install
pnpm dev         # http://localhost:5173, with /api proxied to the API on port 8000
pnpm typecheck
pnpm lint
pnpm test        # Vitest
pnpm build
```

## The API contract

`src/api/schema.d.ts` is generated from `api/openapi.json`, which the API writes:

```sh
(cd ../api && uv run qc openapi)   # after changing the API
pnpm api:types                     # regenerate src/api/schema.d.ts
pnpm api:check                     # fails if schema.d.ts is out of date
```

Both files are committed, so a change to the contract shows up in the pull request. The
API's test suite fails while `api/openapi.json` differs from the app, `pnpm api:check` fails
while the types are stale, and `src/api/contract.ts` fails `pnpm typecheck` if the types stop
saying what the API does.

TypeScript is pinned to 5.9: openapi-typescript needs the TypeScript 5 compiler API, which
TypeScript 7 doesn't have.
