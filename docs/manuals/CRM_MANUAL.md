# CareGist CRM manual

Updated 15 October 2026. For authorised organisation members. CRM is a restricted staff workspace, not a feature included in the current public Brief or Digest. These instructions describe implemented controls; they do not certify live calls, campaigns, recordings or AI. Anonymous access was observed redirecting to login. No authenticated production workflow was exercised for this revision.

## Sign in and choose the right workspace

Open [CRM](https://www.caregist.co.uk/crm) and sign in with your assigned account. A manager must establish membership and role. If access fails, ask the manager to check the organisation and role; do not share credentials or use another person's session. On expiry, sign in again. Keep customer, prospect and payment records in the approved private workspace.

Check the workspace summary and feature status before working. A visible tab does not mean the underlying feature is enabled. Current public health reported calling enabled while recording, AI and TPS automation were disabled; this is a configuration observation and not campaign approval or a successful call test.

## Work contacts and tasks

In **Call queue**, select the intended contact and check company/provider identity, telephone number, lifecycle stage, permission status and existing notes before creating another record. A public provider record is not evidence of interest or permission. Resolve duplicates through the manager's process; do not combine different organisations simply because names match.

Record factual conversation notes and the source of any statement. Add a task with type, title, due time and priority, then verify it appears. Update lifecycle/deal stage only after the underlying event occurs. A deal marked won does not independently establish merchant payment or customer receipt.

If a save fails, retain the visible error and refresh/check whether the record exists before retrying. Do not repeatedly create duplicate contacts, tasks or payments. Report the time, affected reference and error to the manager without exposing private data in public logs.

## Place a permitted call

Confirm independent campaign authority and approved script first. Select the correct contact and obey the call eligibility shown by the system. Unknown, stale, suppressed or blocked status requires resolution by the authorised manager. A green status is a permission-control result and is not proof that the buyer wants a call or that the campaign is approved.

Allow browser microphone access only for the approved calling workspace. If calling or device setup fails, keep the failed state visible and ask the manager; do not bypass the authorisation step with a personal phone. Test-number restrictions, when enabled, must remain in force.

Finish the call and record its actual outcome/disposition and next task. Resolve a pending disposition before starting another call when prompted. If someone asks not to be called, use the completed call outcome **Do not call**, then **Don't call me again** in **Call queue**, and verify the call block. For an email or all-channel opt-out, stop contact immediately and ask the authorised manager to apply the approved suppression process; the email-permission form has no general suppression checkbox. Record the request and verify the relevant block before any further marketing. A lifecycle label alone does not prove suppression.

## Manager controls

Open **Safety**. Only an authorised manager uses **Workspace team**, **Import TPS/CTPS results**, **Check one contact** and **Email permission**. Membership changes require the correct organisation and least necessary role.

Screening import requires an approved source and reference with CSV columns `phone_e164`, `status`, `screened_at`; the interface accepts `clear`, `tps`, `ctps` or `invalid`. Check the import result and affected counts. A one-contact screening entry needs auditable source/reference evidence; specific-consent override is not a shortcut for missing evidence. Do not fabricate a current timestamp to refresh an old check.

Email permission records subscriber type, basis and evidence. Select a supported status only from actual evidence. Unknown stays unknown. Suppression takes precedence over eligibility. The present interface keeps UK SMS disabled; a normal email permission record does not enable SMS.

Campaign creation, recipient selection and sending require separate approval, enabled functionality and eligible recipients. Check exact recipients, copy, sender identity and suppression before an authorised send. This manual does not request a live campaign, a screening import or membership change.

## Review calls and recover

Open **Reports**. Where authorised and enabled, **Recent calls** shows call state, duration and disposition. Recording playback, transcript and AI evaluation depend on separate feature and access controls. An AI summary is advisory: compare material statements with the authorised recording or source, and correct records through the approved process. Do not represent an AI score as a customer statement.

The interface describes a 30-day retention cycle for call intelligence; actual retention and access are governed by the approved configuration and policy. If a recording or transcript has been purged, do not promise recovery. Report failed processing or missing disposition with its reference to the manager.

Managers own screening/permission failures, wrong-organisation access, complaints and feature exceptions. For an apparent cross-organisation record, stop access, retain only the necessary private incident reference and escalate. A failed API or unavailable feature must remain failed until observed recovery; do not mark a contact, call or campaign complete on a button click alone.
