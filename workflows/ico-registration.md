# ICO Registration Runbook

**Owner action required — complete before taking signups.**

CareGist processes personal data as a data controller under UK GDPR and the Data Protection Act 2018.
Registration with the Information Commissioner's Office (ICO) is a legal requirement under Section 17
of the Data Protection (Charges and Information) Regulations 2018. Operating without registration
is a civil offence subject to a fine of up to £4,350.

---

## Steps

### 1. Go to the ICO registration portal

Navigate to: [https://ico.org.uk/registration](https://ico.org.uk/registration)

Click **"Register or renew"**.

---

### 2. Select the organisation type

Select **"Organisation or sole trader"**. Enter the company details:

| Field | Value |
|-------|-------|
| Organisation name | CareGist Ltd |
| Company number | [Company number — from Companies House] |
| Registered address | [Company registered address] |
| ICO sector | Technology / Software / Data services |
| Main contact | [Director name] |
| Privacy contact email | privacy@caregist.co.uk |

---

### 3. Describe your processing activities

Use the descriptions below, drawn from the privacy policy:

**What personal data do you process?**
- Names and email addresses of registered users.
- Password hashes (hashed; not plain text).
- IP addresses and session logs.
- Payment metadata (Stripe customer ID; no card data).
- User-authored reviews (names, ratings, review text).
- Care provider claim data (name, email, phone, role).

**What do you use it for?**
- Providing account and subscription services.
- Processing payments via Stripe.
- Publishing care-provider reviews.
- Verifying care-provider claims.
- Operating security monitoring and rate limiting.
- Sending transactional and marketing emails (marketing: consent only).

**Do you process special category data?** No.

**Do you share data with third parties?** Yes — sub-processors: Stripe, Resend, Sentry, AWS, Neon (see privacy policy, section 5).

**Do you transfer data outside the UK?** Yes — US-based sub-processors (Stripe, Resend, Sentry) under Standard Contractual Clauses.

---

### 4. Pay the annual fee

| Tier | Annual turnover | Fee |
|------|----------------|-----|
| Tier 1 (micro) | Under £632,000 **or** fewer than 10 employees | £40 |
| Tier 2 (small) | £632,000 – £36m **or** 10–250 employees | £60 |
| Tier 3 (medium/large) | Over £36m **or** more than 250 employees | £2,900 |

Pay by debit/credit card or direct debit. The ICO issues a receipt immediately.

---

### 5. Receive your ICO registration number

The ICO typically issues the registration number **within 24 hours** (often instantly on payment).
You will receive it by email. The reference is in the format `ZB123456`.

---

### 6. Update the privacy policy

Once you have your ICO registration number:

1. Open `frontend/app/privacy/page.tsx`.
2. Find the placeholder:
   ```
   [ICO reg number — owner fills post-registration]
   ```
3. Replace it with your actual number, e.g.:
   ```
   ZB123456
   ```
4. Commit and deploy.

---

### 7. Add to standing-hygiene calendar

ICO registration must be renewed **annually**. Set a recurring calendar event:

- **Title:** ICO registration renewal — CareGist Ltd
- **Date:** [Date of registration + 364 days]
- **Action:** Log in to [https://ico.org.uk/registration](https://ico.org.uk/registration), review processing activities for any changes, pay renewal fee.
- **Reminder:** 30 days before expiry.

Failure to renew is the same offence as not registering in the first place.

---

## Useful contacts

| Contact | Details |
|---------|---------|
| ICO registration helpline | 0303 123 1113 (option 4) |
| ICO registration portal | [https://ico.org.uk/registration](https://ico.org.uk/registration) |
| ICO fee guidance | [https://ico.org.uk/for-organisations/data-protection-fee/](https://ico.org.uk/for-organisations/data-protection-fee/) |
| CareGist privacy contact | privacy@caregist.co.uk |

---

*This runbook should be completed by the data controller (CareGist Ltd director) before the service takes any user signups.*
