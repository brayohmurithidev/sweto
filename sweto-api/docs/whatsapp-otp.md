# WhatsApp sign-in codes

Numbers from supported countries other than Kenya get their sign-in code on
WhatsApp (decision D-011). There is no SMS fallback for those countries yet.

## What is built

- `OTPDeliveryChannel` (`sms`, `whatsapp`) on every OTP challenge
  (`otp_challenges.delivery_channel`) and in the `request-otp` response as
  `delivery_channel`.
- `OTPDelivery` (`app/modules/auth/otp_delivery.py`) chooses the channel:
  - SMS for `OTP_SMS_REGIONS` (default `["KE"]`);
  - WhatsApp for the other `OTP_SUPPORTED_REGIONS` (default: the eight EAC
    members);
  - any other country gets `422 INVALID_PHONE_NUMBER`.
- `WhatsAppOTPProvider` protocol and `WhatsAppDeliveryError`
  (`app/integrations/whatsapp/base.py`).
- `WHATSAPP_PROVIDER` is either:
  - `disabled` (the default): WhatsApp numbers get
    `503 OTP_CHANNEL_UNAVAILABLE` before any challenge is created;
  - `console`: local, development and testing only. It logs the code and
    settings refuse it in staging and production.
- Failures: the API returns `503 OTP_DELIVERY_FAILED` with
  `details.channel = "whatsapp"`, expires the challenge and writes an audit
  event with the reason and channel. It never retries by SMS.

## Facts the design relies on

Taken from Meta's documentation, checked on 8 October 2026:

- **No pre-send check exists.** The Cloud API has no way to ask whether a
  number uses WhatsApp. The old On-Premises contacts endpoint stopped
  reporting this from v2.43, and the On-Premises API expired on
  23 October 2025. So we don't build a pre-check: we send, then handle the
  failure.
- **A successful send only means "accepted".** A number that isn't on
  WhatsApp fails later, through the `messages` webhook (`statuses[].status =
  "failed"`, error `131026`, "Message undeliverable"). Errors can also come
  back synchronously, so the adapter must handle both.
- **Codes must use an authentication template** (category
  `AUTHENTICATION`):
  - the body text is fixed by WhatsApp ("<code> is your verification
    code.");
  - it can add a security line and an expiry line;
  - it supports copy-code, one-tap or zero-tap buttons;
  - the code goes in the body parameter and, for button templates, in the
    button parameter too;
  - free-form text is not used.
- **Authentication templates have a 10-minute default time-to-live.** That
  is longer than our 5-minute OTP expiry.

Sources:
- https://developers.facebook.com/docs/whatsapp/on-premises/sunset
- https://developers.secure.facebook.com/docs/whatsapp/api/contacts
- https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages
- https://developers.facebook.com/documentation/business-messaging/whatsapp/support/error-codes
- https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/authentication-templates/authentication-templates

## Needed before the live provider can be written

The adapter will not be written against guessed details. We need:

1. **Provider decision.** Meta Cloud API directly, or a Business Solution
   Provider (for example Twilio, Infobip or 360dialog). The request format,
   authentication and error codes depend on this.
2. **Account identifiers.** The WhatsApp Business Account ID and the sender
   phone number ID (or the BSP's equivalents), and the display name shown to
   users.
3. **Access credential.** A permanent system-user access token with WhatsApp
   messaging permission (or the BSP's API key). It is stored as a secret,
   never in the repo.
4. **Approved authentication template.**
   - its name and language code(s);
   - the button type (copy code is recommended for the first release);
   - whether to add the security line and the expiry line (5 minutes).
5. **Webhook setup** for delivery reports:
   - the public callback URL;
   - the verify token;
   - the app secret used to check `X-Hub-Signature-256`.
6. **Limits.** The messaging tier, the rate limits and any per-country
   restrictions on the account.
7. **A sandbox or test number** for staging.
8. **Product decision on async failures** (D-011 follow-up).
   - Today a code that WhatsApp accepts but can't deliver just never
     arrives. The user waits for the resend timer.
   - With webhooks, the API could mark the challenge `failed` and the app
     could say "This number isn't on WhatsApp" right away.
   - That needs the webhook (item 5), so it isn't built yet.

## Adding a fallback later

The authentication service only calls `OTPDelivery.channel_for()` and
`OTPDelivery.send()`. A fallback, such as SMS for a country when WhatsApp
fails, goes inside `OTPDelivery.send()`. It also needs a setting that lists
fallback channels per country, and the challenge's `delivery_channel` must be
updated to the channel that actually carried the code. Nothing in the auth
service or the app's API contract has to change.
