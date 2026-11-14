# SMS providers

Kenyan sign-in codes go by SMS. Codes for other supported countries go on
WhatsApp (`whatsapp-otp.md`). Which **SMS provider** carries them is a
configuration choice: switching from Advanta to Africa's Talking means
changing environment variables. The auth service, OTP logic, API and mobile
app don't change.

**Status (9 Oct 2026):** the Advanta and Africa's Talking adapters are built
from each provider's published documentation and tested against mocked HTTP
responses only. **Neither has sent a real SMS yet.** Don't treat either as
working until the checks at the bottom of this page pass.

## Layers

| Layer | Where | Knows about |
|---|---|---|
| Notification use case | `AuthenticationService.request_login_otp` (`app/modules/auth/service.py`) | The OTP challenge and its rules. No provider details. |
| Channel selection | `OTPDelivery.channel_for` (`app/modules/auth/otp_delivery.py`) | Country policy: Kenya → SMS; other supported countries → WhatsApp; others rejected. Never falls back from WhatsApp to SMS. |
| SMS provider registry | `build_sms_provider` (`app/integrations/sms/registry.py`) | `SMS_PROVIDER` → adapter. Unknown or misconfigured providers fail; there is no silent fallback to console. |
| SMS provider contract | `SMSProvider` (`app/integrations/sms/base.py`), shared `OTPSender` / `OTPDeliveryError` (`app/integrations/delivery.py`) | The same request, result (provider message ID) and errors for every adapter. |
| Adapters | `console.py`, `advanta.py`, `africastalking.py` in `app/integrations/sms/` | Each provider's HTTP request, authentication and response format. |
| WhatsApp | `WhatsAppOTPProvider` and the Meta adapter (`app/integrations/whatsapp/`) | Its own contract (authentication templates), not forced into the SMS one. |
| Delivery state | `otp_challenges.delivery_status`, `provider_message_id`, `delivery_error_code` | pending → accepted → sent → delivered → read; failed; unknown. Separate from whether the code is valid. |

## Contract

- **Call:** `send_otp(phone_number, otp_code, expires_in_seconds)`.
  - `phone_number` is E.164 and is always a mobile number.
  - Every adapter sends the same text, from `render_otp_message()`: one SMS
    segment, GSM-7 characters only.
- **Success:** the adapter returns once the provider has **accepted** the
  message, with the provider's message ID when there is one. Acceptance is
  not delivery: the challenge records `delivery_status = accepted`.
- **Failure:** every failure raises
  `SMSDeliveryError(reason, retryable, provider_code, outcome_unknown)`.
  - `reason` comes from one shared vocabulary (table below).
  - `provider_code` is the provider's own code, for the audit log.
  - Provider message text is never copied or logged, because it can echo
    the phone number.
- **`outcome_unknown`** is True when the request may have reached the
  provider: a read timeout, a dropped connection, or a success response we
  can't read. A refused connection is not unknown, because the provider got
  nothing.
- **Logging:** codes, API keys and phone numbers are never logged.
- **Timeout:** the caller enforces `SMS_SEND_TIMEOUT_SECONDS` (default 10 s),
  and each adapter's HTTP client uses the same timeout.

### Shared failure reasons

| Reason | Meaning | Retry? |
|---|---|---|
| `unauthorized` | Bad or missing credentials | No (fix configuration) |
| `sender_id_rejected` | Sender ID / shortcode not allowed | No (fix configuration) |
| `insufficient_balance` | Account out of credit | No (top up) |
| `invalid_recipient` | Number or network not accepted | No |
| `recipient_blocked` | Number blacklisted / opted out | No |
| `invalid_request` | Request rejected as malformed | No |
| `rate_limited` | Too many requests | Yes |
| `provider_unavailable` | Provider-side error | Yes |
| `provider_rejected` | Any other refusal | No |
| `provider_unreachable` | Connection failed or dropped | Yes |
| `timeout` | No answer in time (outcome unknown) | Yes |
| `malformed_response` | Unreadable success response (outcome unknown) | Yes |

## What the auth service does on failure

- **The challenge is retired** (`status = expired`). The user can ask for a
  new code at once, without the 60-second cooldown, and there is never more
  than one usable code.
- **Delivery status:** set to `failed`, or to `unknown` when the outcome is
  unknown. An unknown-outcome SMS may still arrive, but its code no longer
  works.
- **Audit event:** `otp_delivery_failed` records the reason, the provider
  code, `outcome_unknown` and the channel.
- **Response:** `503 OTP_DELIVERY_FAILED` with `details.channel` and
  `details.retryable`.

There is **no automatic fallback** to another provider. A send that timed
out may still arrive, so retrying it elsewhere could deliver two codes. A
fallback can be added later inside `OTPDelivery.send`, and only for failures
where `outcome_unknown` is False.

## Configuration

Credentials live in environment variables or the deployment's secret store,
never in the repository. Settings are validated at startup:
- a selected provider with a missing setting stops the API with a message
  that **names** the missing settings;
- values are never shown, because `get_settings()` strips Pydantic's echo of
  the input.

| Variable | Secret? | Used by |
|---|---|---|
| `SMS_PROVIDER` | No | `console` (default; local, development and testing only), `advanta` or `africastalking` |
| `SMS_SEND_TIMEOUT_SECONDS` | No | All; default 10 |
| `ADVANTA_API_KEY` | **Yes** | Advanta (`apikey`) |
| `ADVANTA_PARTNER_ID` | No | Advanta (`partnerID`) |
| `ADVANTA_SHORTCODE` | No | Advanta sender ID (`shortcode`) |
| `ADVANTA_BASE_URL` | No | Advanta; default `https://quicksms.advantasms.com` |
| `AFRICASTALKING_ENVIRONMENT` | No | Africa's Talking: `sandbox` or `live` |
| `AFRICASTALKING_USERNAME` | No | Africa's Talking app username (`sandbox` in the sandbox) |
| `AFRICASTALKING_API_KEY` | **Yes** | Africa's Talking (`apiKey` header) |
| `AFRICASTALKING_SENDER_ID` | No | Optional registered sender ID / shortcode (`from`). Without it, Africa's Talking's default sender is used. |

**Startup refusals:**
- `SMS_PROVIDER=console` in staging and production (it logs codes);
- the Africa's Talking sandbox in staging and production (it never reaches a
  phone);
- a sandbox whose username isn't `sandbox`.

## Providers

### Console (`console`)

Writes the code to the application log. It is for local development and
automated tests only, and is refused in staging and production.

### Advanta (`advanta`): built, not yet tested live

Source: Advanta's API page, https://www.advantasms.com/bulksms-api (checked
9 Oct 2026).

- **Request:** `POST {ADVANTA_BASE_URL}/api/services/sendsms/` with JSON
  `{"apikey", "partnerID", "message", "shortcode", "mobile"}`. `mobile` is
  sent as `254712345678`, without the `+`, as in Advanta's example.
- **Success:** `{"responses": [{"respose-code": 200, "messageid": …}]}`.
  Advanta's page spells the key `respose-code`; `response-code` is accepted
  too. `messageid` is stored as the provider message ID.
- **Result codes:**

| Code | Reason |
|---|---|
| 1001 | `sender_id_rejected` |
| 1002, 1003 | `invalid_recipient` |
| 1004 | `insufficient_balance` |
| 1005, 1007, 4090 | `provider_unavailable` |
| 1006, 4091, 4092 | `unauthorized` |
| 1009, 1010 | `invalid_request` |
| others | `provider_rejected` |

- **HTTP errors:** 401/403 → `unauthorized`; 5xx → `provider_unavailable`;
  other 4xx → `provider_rejected`.
- **Not built:**
  - **Delivery reports.** Advanta offers them only by polling `getdlr`, and
    its page doesn't document the reply.
  - **The OTP / transactional route.** The page doesn't mention it. Ask
    Advanta whether OTP traffic needs a different route or `pass_type`.

### Africa's Talking (`africastalking`): built, not yet tested live

Sources:
- the Africa's Talking help centre:
  - endpoints: https://help.africastalking.com/en/articles/2232953
  - status codes: https://help.africastalking.com/en/articles/16150386
  - Kenya sender IDs: https://help.africastalking.com/en/articles/407085
- the official Python and Node SDKs (github.com/AfricasTalkingLtd).

All checked 9 Oct 2026. The developer documentation site needs JavaScript
and couldn't be read directly.

- **Request:** `POST https://api.africastalking.com/version1/messaging`
  (sandbox: `https://api.sandbox.africastalking.com/version1/messaging`).
  - Encoding: form-encoded, with headers `apiKey` and
    `Accept: application/json`.
  - Fields: `username`, `to` (E.164 **with** `+`), `message`,
    `bulkSMSMode=1` and, if set, `from`.
  - This is the endpoint the official SDKs use.
- **Success:** HTTP 201 with `SMSMessageData.Recipients[0]`.
  - `statusCode` 100 Processed, 101 Sent or 102 Queued means accepted;
    `messageId` is stored.
  - Africa's Talking says these mean accepted, not delivered.
- **Recipient codes:**

| Code | Reason |
|---|---|
| 401 RiskHold, 407 CouldNotRoute, 502 RejectedByGateway | `provider_rejected` |
| 402 InvalidSenderId | `sender_id_rejected` |
| 403, 404 | `invalid_recipient` |
| 405 | `insufficient_balance` |
| 406 | `recipient_blocked` |
| 500, 501 | `provider_unavailable` |
| others | `provider_rejected` |

- **HTTP errors:** 401/403 → `unauthorized`; 429 → `rate_limited`;
  5xx → `provider_unavailable`; other 4xx → `provider_rejected`.
- **Not built:**
  - **Delivery-report callbacks.** The field names, the content type, and
    any way to check that a callback is genuine aren't in documentation we
    could confirm. Africa's Talking documents no callback signature. When
    added, the callback URL should carry a secret token, match the `id` to
    a stored message ID, and update `delivery_status` through the same
    forward-only rules as WhatsApp.
- **Kenya:**
  - **Sender ID:** must be registered (at most 11 characters, not
    generic). Using the default sender while you own one can trigger
    RiskHold.
  - **Transactional route:** the transactional route for OTP traffic is
    arranged with Africa's Talking.

## Delivery status

- **Shared state model:** pending → accepted → sent → delivered → read;
  failed; unknown.
- **Order rules:** reports only move a challenge forward; `failed` is final;
  duplicates are ignored.
- **Effect on the code:** a `failed` report retires a still-pending code. It
  never touches a verified one.
- **Who reports today:**
  - WhatsApp (Meta webhook) is the only provider sending reports.
  - SMS challenges stop at `accepted`, `failed` or `unknown` until a
    provider's delivery reports are added.

## Before an SMS provider goes live

For the chosen provider:

- [ ] Credentials are in the staging secret store and the selected
      `SMS_PROVIDER` starts cleanly.
- [ ] The sender ID / shortcode is approved for SWETO, on a transactional
      (OTP) route.
- [ ] A Kenyan test number receives the code from the SWETO sender, and
      signing in with it works.
- [ ] The challenge shows `delivery_status = accepted` and the provider's
      message ID.
- [ ] A wrong API key gives `503 OTP_DELIVERY_FAILED` with reason
      `unauthorized`, and no key in the logs.
- [ ] The logs contain no codes, keys or phone numbers.
- [ ] Resend after the cooldown works.
- [ ] Repeat on production with production credentials.
