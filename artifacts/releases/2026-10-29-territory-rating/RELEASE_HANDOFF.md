# Territory Brief publication precedence — review candidate

Status: tested review candidate; NOT approved for deployment or merge.

Branch: codex/territory-rating-publication-20261029. Base: 7f4c79ea31c26a76ecb788147d735d82a48bba0f (the common source base used by the tested local implementation). The original dirty checkout is preserved and has not been reset or committed wholesale.

Changes: newest dated CQC file/website publication wins; undated website fills publication gaps; API fills remaining gaps only. Candidates and provenance remain available when unresolved. Output labels show publication-as-of date and source. Commercial/checkout/delivery gates remain unchanged.

Important integration gate: current origin/main 97e845d has a separately introduced rating_resolver, opt-in resolved-contract gate, buyer-rule fields, and rule_ratings source-edition handling not present in this tested base. Reconcile the two implementations while preserving those newer behaviours before merging or deploying a release. This branch must not overwrite main's newer handling.

Independent gates: Grok 4.6 xhigh must retest the exact candidate journey, followed by an independent different-model approved-provider challenge. Neither is satisfied by the producer tests or supplementary agent review. DeepSeek prohibited.

Automatic deployments are disabled for this named branch in both Vercel configuration files to keep a push from bypassing the review gate. No global Vercel or production settings changed. The existing production deployment remains untouched.

Validation on isolated branch: 128 backend tests, 8 isolated Postgres tests, 9 targeted frontend tests and candidate Ruff checks. Original packet also records TypeScript verification. Test-only lint fixes remove an unused import and require strict zip pairing; frozen prior evidence files remain unchanged.

Evidence: artifacts/rating-resolution/2026-10-29-publication-precedence/; original rating audit included under artifacts/rating-audit/2026-10-22/. Both frozen packet manifests should be checked before review. No production data/source-edition import, merge, gate opening or deployment is included.
