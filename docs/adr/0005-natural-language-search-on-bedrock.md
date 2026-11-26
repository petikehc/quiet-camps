# 0005: Plain-words search with Claude Haiku on Amazon Bedrock

- **Status:** accepted
- **Date:** 2026-11-23

## Context

The homepage asks one question, "where and when?", in plain words: "next weekend around
Sunshine Coast", "Easter, a getaway from Toowoomba". The words have to become dates, a place
and a distance for the search. Dates come in many shapes (weekends, long weekends, named
holidays, "3–6 April"), and places as nicknames and regions ("the Sunny Coast", "K'gari").

## Decision

`POST /ask` sends the words to Claude Haiku on Amazon Bedrock and gets back a structured
reading (arrive, depart, place, from or near, km), validated against a Pydantic schema. It
calls AWS's Converse API on `bedrock-runtime` with the `au.` inference profile, so the words
stay in Australia; the reading is a forced call of a tool whose input is the schema. The
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

- **Endpoint and model:** Claude Haiku 4.5 (`au.anthropic.claude-haiku-4-5-20251001-v1:0`) in
  Sydney through Converse. Anthropic's SDK client for Bedrock's Messages API
  (`bedrock-mantle`) is kept as a second reader (`ASK_ENDPOINT=mantle`), but AWS opens that
  endpoint per account and region: here it had no Haiku in Sydney, and in Melbourne (an
  opt-in region) answered "not available for this account". Haiku 5.5 is newer and cheaper;
  it needs Anthropic's first-time-use form and its terms accepted in the console, then
  `ASK_MODEL=au.anthropic.claude-haiku-5-5`.
- **Cost:** a short extraction (~600 tokens in, ~100 out): about a tenth of a cent an ask on
  Haiku 4.5, a hundredth on Haiku 5.5. Guards: off unless `ASK_ENABLED`, 200 characters, the
  same words answered from a cache for the rest of the day, and limits counted in Postgres:
  20 an hour per viewer and 300 a day for the whole site (ADR 0006).
- **Privacy:** the words go to Bedrock in our AWS account; we don't store or log them, only
  whether dates and a place were understood.
- **Failure:** throttling, no model access, a refusal or a bad reading is a 503, and the page
  falls back to its own date and place fields. Search never depends on `/ask`.
- **Tests:** a fake reader stands in for Bedrock; one live test runs only with
  `RUN_LIVE_AWS=1`.
