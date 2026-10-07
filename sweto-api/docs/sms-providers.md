# SMS providers

Authentication sends OTPs through the `SMSProvider` protocol
(`app/integrations/sms/base.py`). The auth domain never talks to a provider
directly, so a provider can be replaced without touching authentication.

## Contract

- `send_otp(phone_number, otp_code, expires_in_seconds)` returns only when the
  provider has accepted the message. `phone_number` is E.164 and is always a
  mobile number (landlines are rejected before a code is generated).
- Every failure raises `SMSDeliveryError(reason, retryable=...)`: rejection,
  unreachable provider, malformed response. Use short, stable reason strings
  such as `provider_rejected`, `provider_unavailable`, `malformed_response`,
  `insufficient_balance`. They are stored in the audit log and logged.
- Never put the OTP or credentials in exception messages or logs.
- Use `render_otp_message()` (`app/integrations/sms/messages.py`) so every
  provider sends the same copy (one SMS segment).
- The caller enforces `SMS_SEND_TIMEOUT_SECONDS` (default 10 s) around the
  call; providers should also set their own HTTP timeouts below that.

## What the auth service does on failure

The challenge is marked `expired` (so the user is not held in the 60-second
resend cooldown for a code that never arrived), an `otp_delivery_failed`
audit event is recorded with the reason, and the API answers
`503 OTP_DELIVERY_FAILED` ("We couldn't send your verification code. Please
try again."). The per-phone and per-IP rate limits still count the attempt.

## Providers

| Name | Status | Use |
|---|---|---|
| `console` | Implemented | Local, development and testing only. Logs the code. Refused by settings validation in `staging` and `production`. |
| `advanta` | **Not implemented** | Production provider (decision D-004). Blocked on the information below. |

### Information needed to implement Advanta

The adapter will not be written against guessed details. Before implementing,
we need from the Advanta account / official documentation:

1. Base URL and the send endpoint for single messages.
2. Authentication scheme and the exact credential names (for example API key,
   partner ID) and how they are passed.
3. The approved sender ID / shortcode for SWETO and whether it is
   transactional (OTP traffic should not go through a promotional route).
4. Request format, including phone number format (E.164 with or without `+`).
5. Response format for success and for each error, including how per-recipient
   failures and insufficient balance are reported.
6. Rate limits and recommended timeouts.
7. Delivery report (DLR) callback support, if we want delivery status.
8. A sandbox or test credentials, if available.

Credentials go in environment variables / the secrets manager only, never in
the repository.
