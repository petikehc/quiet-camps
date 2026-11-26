# 0006: Deploy on Lambda and CloudFront, with Postgres on Neon

- **Status:** accepted
- **Date:** 2026-11-26

## Context

The site should have a public link, cost close to nothing while few people use it, and run
on AWS, where `/ask` already calls Bedrock (ADR 0005). Most visitors are in Australia. The
local database is 1.8 GB, almost all of it `camp_night`, a row per site per night since
2011; the API reads it for lead times (the last 3 years) and for `/trips/latest` (the last
12 months), and everything else from tables derived from it.

Prices and limits checked on 26 Nov 2026: App Runner stopped taking new customers on 30 Apr
2026; RDS `db.t4g.micro` in Sydney is about US$18 a month before storage; Neon's free plan
holds a project of up to 0.5–1 GB, with Postgres 18 in `aws-ap-southeast-2`.

## Decision

One CloudFront distribution serves the web from a private S3 bucket and `/api/*` from a
Lambda function URL; the function runs the same Docker image as everywhere else, with the
AWS Lambda Web Adapter turning each invocation into an HTTP request to uvicorn. Postgres is
a Neon project in Sydney, holding a trimmed, read-only snapshot. Everything is in
`deploy/aws/`: CloudFormation templates, `ship.sh` and `publish-db.sh`.

- **Only through CloudFront:** the function URL is public (auth NONE), so CloudFront adds a
  secret header and the API answers 403 without it (`ORIGIN_SECRET`).
- **The snapshot:** `camp_night` keeps the nights from 1 Oct 2023 (350 MB in all). The two
  derived materialized views become plain tables filled from the full data, because a
  restore refreshes a materialized view from whatever rows it has. Search, calendars and
  typical nights keep their history since 2011; `/trips/{year}` before 2024 comes back
  nearly empty, and the web doesn't ask for it. The snapshot is never migrated: change the
  local database, then build and load it again.
- **`/ask` on, with guardrails:** the function's role may invoke only the `au.` Haiku 4.5
  profile, with no access keys anywhere. The hourly limit counts viewers by
  `CloudFront-Viewer-Address`, which viewers can't set. Spending is watched by the account's
  own budget alert, not one in this stack: a budget can only be scoped to the stack through a
  cost-allocation tag, and Bedrock's on-demand calls, the cost that can grow, don't carry it.

## Alternatives considered

- **Mangum instead of the Web Adapter:** a Python handler around the ASGI app; the adapter
  needs no code and the same image runs locally, in CI and on Lambda.
- **RDS:** the AWS way, but about US$20 a month, and the function would have to be in the
  VPC, where reaching Bedrock needs a NAT gateway (about US$33 a month) or an endpoint.
- **ECS Express Mode (App Runner's successor):** no cold starts, but a load balancer and
  Fargate cost US$40–60 a month.
- **Fly.io or a small VPS:** cheap and always on, but not AWS.
- **Neon with all 1.8 GB:** every year's trips, for about US$1–3 a month on the paid plan;
  the web only shows the latest 12 months.
- **CloudFront origin access control for the function:** signs requests to the function
  instead of a shared secret, but then viewers must send a hash of every POST body.
- **A custom error page for SPA routes:** would also turn the API's 404s into `index.html`;
  a CloudFront Function rewrites only paths without a file extension.

## Consequences

- Almost free while quiet: Lambda, CloudFront and Neon's free tiers cover low traffic; the
  repository's images cost cents.
- Cold starts: the first request after the function has been idle takes a few seconds, and
  Neon also wakes from suspend. `pool_pre_ping` replaces connections that died meanwhile.
  `/trips/latest` and `/year` are cached by CloudFront for a day, as their `Cache-Control`
  says.
- The `/ask` limit is per function instance, in memory: several warm instances each allow
  20 an hour per viewer. The account's budget alert is the backstop; a shared store
  (DynamoDB) would make it exact.
- Updating the data means rebuilding and reloading the snapshot (`publish-db.sh`), not
  running `qc` against Neon.
- `ship.sh teardown` deletes all of it; Neon is deleted in its own console.
