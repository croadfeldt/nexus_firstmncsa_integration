# nexus_firstmncsa_integration — Design & Feature Inventory

**Status:** Living document
**Last updated:** 2026-05-25
**Source:** this repo (`app.py`, `Containerfile`)

This document records what the bridge is, what it listens for, and what it forwards. Update it whenever the trigger phrases change, the CSA payload shape changes, or a new event channel is added.

## Goal

Bridge two FRC competition operations tools that currently force volunteers to monitor both:

- **frc.nexus** — Slack-channel-per-event reports from the FRC Nexus tool
- **firstmn.csa support tool** — the MN CSA crew's ticketing workflow

The bridge listens on Slack for Nexus bot messages that indicate someone needs CSA help (volunteer assist, FTA request, team help) and automatically opens a corresponding ticket in the CSA tool — so the CSA crew can keep working in their familiar tooling while Nexus stays the single front door for teams and volunteers.

**Long-term goal:** influence frc.nexus to absorb the CSA-tooling capabilities directly, making this bridge unnecessary.

## Non-goals

- **Not a general Slack bot.** Only listens for specific Nexus bot phrases; everything else is ignored.
- **Not a two-way sync.** CSA ticket updates do not flow back into Slack/Nexus.
- **Not a self-serve interface.** No commands; the bot only reacts to Nexus's own posts.

## How it works

```
FRC Nexus bot ──posts to──► Slack channel (per event)
                                    │
                                    ▼
                    Slack Socket Mode (this app, slack_bolt)
                                    │
                                    ▼
                          message-text classifier
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
   "volunteer has         "FTA request for       "has requested help"
    requested help"        team N"                (team-side ask)
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
                       POST {webform} to firstmn.csa
                                    │
                                    ▼
                  reply ✅ / ⚠️ in the originating channel
```

### Trigger phrases (order matters)

The classifier picks `contactName` by matching, in this order:

1. `"volunteer has requested help"` → `Nexus - Volunteer`
2. `"FTA request for team"` → `Nexus - FTA`
3. `"has requested help"` → `Nexus - Team` (fall-through for the generic team ask)

Anything else → log "Unrecognized bot message, please tell Chris" and drop.

### Explicit ignores

- `channel_join`, `channel_leave`, `message_changed`, `message_deleted`, `bot_add` subtypes
- Non-`bot_message` subtypes (humans typing in the channel)
- Nexus "This channel will receive…" setup messages
- LRI inspection-flag messages (inspection team handles separately)
- Reinspection messages (`has been flagged for reinspection`, `requested reinspection`)

### CSA payload

POSTed to `FIRSTMNCSA_API_ENDPOINT` with the API key in `API-Key` header:

```json
{
  "title": "<original Slack message text>",
  "teamNumber": "<extracted with regex>",
  "frcEvent": "<looked up from eventMap by Slack channel ID>",
  "priority": "Medium",
  "description": "<flattened Slack block text — header + rich_text + section>",
  "contactName": "Nexus - Volunteer | Nexus - FTA | Nexus - Team",
  "contactEmail": "firstmn.csa@gmail.com",
  "problemCategory": "Other or not sure",
  "attachments": []
}
```

## Event channel map

`eventMap` in `app.py` is the source of truth for channel-ID → event-name lookup. When a new MN event channel is added in Slack, append it here. Channels not in the map fall back to `"Off Season"`.

## Deployment

- **Container:** `python:3.12` base, single-process Slack Socket Mode handler. See `Containerfile`.
- **Config:** environment variables only —
  - `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`
  - `FIRSTMNCSA_API_KEY`, `FIRSTMNCSA_URL`, `FIRSTMNCSA_API_ENDPOINT`
  - `DEBUG` (default `true`; set `false` to quiet down)
- **Local dev:** `setup-nl.sh` activates a venv and runs `app.py` directly. **The committed `setup-nl.sh` contains real Slack and CSA tokens** — see "Known issues" below.

## Known issues / future work

- **🔒 Secrets committed in `setup-nl.sh`.** Real Slack `xoxb-…` / `xapp-…` tokens and the CSA API key are in git history. Rotate, move to a Secret-loader or `.env` file (gitignored), and consider scrubbing history with `git filter-repo`. *Not actioned by this design pass.*
- **No test coverage.** Trigger-phrase regression is risk-prone; a small pytest with sample Nexus payloads would prevent silent breakage when Nexus changes wording.
- **Hardcoded contact email** (`firstmn.csa@gmail.com`). Reasonable for current ops; lift to env var if the bridge ever runs for a different region.
- **No retry on transient CSA failures.** A 5xx becomes a `⚠️` Slack reply; the volunteer is asked to submit manually. Could add a bounded retry with exponential backoff.
- **Single channel per event** assumption. If Nexus ever fans out into multiple channels per event, `eventMap` becomes a leaky abstraction.
- **No CSA → Slack feedback loop.** When CSA marks the ticket resolved, Nexus/Slack doesn't know. Adding that would be a separate inbound webhook handler.
- **Long-term replace-by-upstream** — track which Nexus features would absorb this bridge, and what would have to be built into Nexus for the CSA crew to stop needing their separate tooling.
