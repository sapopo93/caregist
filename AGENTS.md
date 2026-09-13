<!-- stripe-projects-cli managed:agents-md:start -->
## Stripe Projects CLI

This repository is initialized for the Stripe project "CareGist".

## Tools used

- [Stripe CLI](https://docs.stripe.com/stripe-cli) with the `projects` plugin to manage third-party services, credentials, and deployments for this project. Use the stripe-projects-cli to manage deploying and access to third party services.
<!-- stripe-projects-cli managed:agents-md:end -->

# CareGist operating loop

Read `.warroom/README.md` and `.warroom/PIPELINE.md` before acting.

1. **Grok 4.6 xhigh** investigates. Hard cap 120 turns.
2. **Checkpoint** before exhaustion. Persist `.warroom/CURRENT_VERDICT.md`, `TOP_BLOCKERS.md`, `NEXT_ACTIONS.md`, `UNFINISHED.md`.
3. **CONTINUE** resumes from `.warroom/`. Do not repeat closed work.
4. **Codex** (gpt-5.6-sol) applies the named fix only.
5. **Grok** re-tests the customer journey step by step.
6. **DeepSeek V4 Pro** challenges a frozen evidence packet. Model agreement is not green.
7. **Hermes** orchestrates the next single bounded step.

Checkout, collectors, outbound delivery, leads, claims, and exports stay fail-closed until their named gates pass. A producing model cannot approve its own work.
