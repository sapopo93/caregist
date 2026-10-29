# Territory Brief publication precedence — review candidate

Status: tested review candidate; NOT approved for deployment or merge.

Branch: codex/territory-rating-publication-20261029. Base: 7f4c79ea31c26a76ecb788147d735d82a48bba0f (the common source base used by the tested local implementation). The original dirty checkout is preserved and has not been reset or committed wholesale.

Changes: newest dated CQC file/website publication wins; undated website fills publication gaps; API fills remaining gaps only. Candidates and provenance remain available when unresolved. Output labels show publication-as-of date and source. Commercial/checkout/delivery gates remain unchanged.

Important integration gate: current origin/main 97e845d has a separately introduced rating_resolver, opt-in resolved-contract gate, buyer-rule fields, and rule_ratings source-edition handling not present in this tested base. Reconcile the two implementations while preserving those newer behaviours before merging or deploying a release. This branch must not overwrite main's newer handling.

Independent gates: Grok 4.6 xhigh must retest the exact candidate journey, followed by an independent different-model approved-provider challenge. Neither is satisfied by the producer tests or supplementary agent review. DeepSeek prohibited.

Automatic deployments are disabled for this named branch in both Vercel configuration files to keep a push from bypassing the review gate. No global Vercel or production settings changed. The existing production deployment remains untouched.

Validation on isolated branch: 128 backend tests, 8 isolated Postgres tests, 9 targeted frontend tests and candidate Ruff checks. Original packet also records TypeScript verification. Test-only lint fixes remove an unused import and require strict zip pairing; frozen prior evidence files remain unchanged.

Evidence: artifacts/rating-resolution/2026-10-29-publication-precedence/; original rating audit included under artifacts/rating-audit/2026-10-22/. Both frozen packet manifests should be checked before review. No production data/source-edition import, merge, gate opening or deployment is included.

## Push and deployment disposition

Pushed candidate commits: 2df98bf (implementation/evidence) and c58efa3 (CSV/ODS manifest inputs). Draft PR https://github.com/sapopo93/caregist/pull/151 reports CONFLICTING / DIRTY against main, with no CI check results. The remote branch SHA was verified as c58efa3e8a3ccc0559d86a78be8f242dbe6f8b29 before this status-only update. GitHub reports no deployment for that candidate SHA.

Grok retest was attempted through the installed Hermes CLI using explicit xai-oauth, grok-4.6, xhigh, 25-turn maximum, and a 180-second run budget. No output or review receipt was returned before interruption after the budget. This is NOT VERIFIED, not a pass or an inferred authentication diagnosis. The independent different-model challenge remains pending after a completed Grok retest. No DeepSeek invocation was made.

Deployment was withheld because main integration and prescribed independent review gates have not passed. Automatic deployment remains disabled for this review branch. The original checkout's unrelated changes remain outside these commits.
