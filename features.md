## Find / research (lead intelligence)
  - ⭐ Saved searches + auto-discovery on a schedule — reuse the existing follow-up scheduler to re-run a saved discovery query weekly and surface only new companies (you already have ventures + the prompt-builder agent).
  - ⭐ Dedup + "already contacted" guard — detect duplicate companies/domains across discoveries so you never email the same lead twice.
  - Website/tech signal scraping — fetch the lead's site and detect signals relevant to your pitch (e.g. for NDetex: does the site already have a "visualizer/configurator"? what e-comm platform?). Turns discovery into qualification.
  - Lead scoring (AI fit score 0–100) — rank leads by fit to a chosen venture so you work the best ones first.
  - CSV import/export — bulk-import a prospect list, export enriched leads for use elsewhere. 

## Engage (outreach power-ups)
  - ⭐ Reply detection via IMAP — poll the inbox, match replies to campaign emails, auto-mark responded, and auto-stop follow-ups when someone replies (you already track replied_at).
  - ⭐ A/B subject testing with auto-winner — the email agent already generates subject variants; split-send and promote the best by open rate.
  - Sending guardrails — daily send caps per SMTP account + warm-up ramp + per-domain throttling (extends your random-delay pacer) to protect deliverability.
  - Unsubscribe link + suppression list — CAN-SPAM/GDPR compliance (the README already promises this); one-click opt-out via your existing /track router.
  - Multi-channel — generate a LinkedIn DM / connection-note variant alongside the email (you already capture linkedin_url).
  - Snippet/template library + per-venture sender identities.

## Grow / analyze (the "research tool" layer)
  - ⭐ Analytics dashboard — funnel (discovered→enriched→contacted→replied→converted), best subjects, best send-times, response-rate by industry/region/timezone. You already store all the
  events.
  - Best-time-to-send recommender — learn from open timestamps per timezone (pairs perfectly with the scheduler you just got).
  - CRM-lite pipeline — a Kanban of lead statuses with notes/tasks/reminders so this becomes your outreach hub.
  - Weekly digest email to yourself: new leads found, replies, meetings booked.

## Platform/AI exotica
  - "Research assistant" chat over your own lead DB ("show me NZ e-comm leads who opened but didn't reply").
  - Meeting booking link injected into emails + click tracking you already have.
  - Webhooks/Zapier out, and an MCP server so you can drive discovery/campaigns from Claude directly.