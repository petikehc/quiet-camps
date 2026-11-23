# 0005: Plain-words search with Claude Haiku on Amazon Bedrock

- **Status:** accepted
- **Date:** 2026-11-23

## Context

The homepage asks one question, "where and when?", in plain words: "next weekend around
Sunshine Coast", "Easter, a getaway from Toowoomba". The words have to become dates, a place
and a distance for the search. Dates come in many shapes (weekends, long weekends, named
holidays, "3–6 April"), and places as nicknames and regions ("the Sunny Coast", "K'gari").

## Decision

`POST /ask` sends the words to Claude Haiku 5.5 on Amazon Bedrock and gets back a structured
reading (arrive, depart, place, from or near, km), validated against a Pydantic schema. The
model only reads; the API checks the dates, and finds the place in our own list of
Queensland places (ADR 0003, `qc places`). Holiday dates come from our calendar in the
prompt, so "Easter" is never the model's arithmetic.

## Alternatives considered

- **A rule-based parser and a list of regions:** free and predictable, but every phrasing
  is another rule; the model handles phrasing, and our code still owns the facts.
- **The Claude API directly:** the same model, but the deploy is heading to AWS (Lambda), and
  Bedrock keeps billing, credentials (IAM) and limits in one account.
- **Amazon Location Service for places:** handles any address, but costs per lookup and
  needs AWS at run time; the ABS list is free and offline, and the model normalises names
  to it.

## Consequences

- **Cost:** a short extraction (~600 tokens in, ~100 out) at effort `low`; thousands of asks
  cost about a dollar. Guards: off unless `ASK_ENABLED`, 200 characters, 20 an hour per
  client (in memory, per process: API Gateway throttling replaces it once deployed), the same
  words answered from a cache for the rest of the day, and an AWS Budgets alert.
- **Privacy:** the words go to Bedrock in our AWS account; we don't store or log them, only
  whether dates and a place were understood.
- **Failure:** throttling, no model access, a refusal or a bad reading is a 503, and the page
  falls back to its own date and place fields. Search never depends on `/ask`.
- **Tests:** a fake reader stands in for Bedrock; one live test runs only with
  `RUN_LIVE_AWS=1`.
