# Governed Google Workspace integration candidate

**Status:** Policy implementation tested; no OAuth, credentials, Google API calls or Workspace mutations have occurred.

## Founder-authorised target

- Gmail: whole-mailbox read-only.
- Drive: operate only within explicitly assigned folders/files.
- Docs, Sheets and Slides: create/read/update only within those assigned folders/files.
- NotebookLM: improve research, analysis and output using public URLs or public/sanitised files in a dedicated research folder.
- Forbidden: email send/reply/draft/modify/delete/label changes; Contacts; Calendar; external sharing; Drive delete; Drive access outside allowlists; Gmail-to-NotebookLM transfer.

## Security architecture

Use two independently revocable grants:

1. **Documents grant:** `https://www.googleapis.com/auth/drive.file`
2. **Mailbox grant:** `https://www.googleapis.com/auth/gmail.readonly`

Docs, Sheets and Slides API methods accept `drive.file`, avoiding account-wide document scopes. Folder IDs are also checked by `WorkspacePolicy`; OAuth and application policy must both permit the operation.

The mailbox grant remains a separate activation gate because `gmail.readonly` is a Google restricted scope and mailbox content can contain personal, confidential and regulated data.

## NotebookLM boundary

Accepted source classes:

- `public_url` + `public`
- `drive_file` + `public` or `sanitised`, only under the dedicated NotebookLM research-folder allowlist

Denied source types/data classes include Gmail, personal, confidential, regulated and secret material. Nothing automatically copies mailbox content into Drive or NotebookLM.

## Verification

```bash
cd /Users/user/CareGist
python3 -m pytest governed-integrations/google_workspace/tests/test_policy.py -q
```

Expected verified result: `13 passed`.

## Remaining activation prerequisites

1. Record the exact Workspace tenant/account owner and assigned folder IDs.
2. Verify MFA, recovery, external-sharing defaults, export/restore and incident controls.
3. Create a dedicated Google Cloud OAuth desktop client without exposing its secret in chat.
4. Integrate the tested policy into the Hermes Workspace adapter.
5. Run synthetic and then live read-back tests against non-sensitive test files.
6. Independently review the implementation with no Critical/High findings.
7. Activate the `drive.file` documents grant first.
8. Resolve the restricted-scope/privacy/AI-provider assessment before activating `gmail.readonly`.
9. Create the first NotebookLM notebook using public sources only; verify citations before any output enters `company-os`.

## Official scope evidence

- Docs per-file scope: https://developers.google.com/docs/api/auth
- Sheets per-file scope: https://developers.google.com/sheets/api/scopes
- Slides `drive.file` methods: https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/batchUpdate
- Restricted-scope verification: https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification
- NotebookLM source handling: https://support.google.com/notebooklm/answer/16215270
