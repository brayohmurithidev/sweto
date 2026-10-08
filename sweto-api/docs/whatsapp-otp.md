# WhatsApp sign-in codes (Meta Cloud API)

Kenyan numbers get their sign-in code by SMS. Numbers from the other
supported countries get it on WhatsApp (D-011). WhatsApp messages go
through **Meta's WhatsApp Cloud API directly**: no reseller is used, as
decided on 8 Oct 2026. There is no SMS fallback for non-Kenyan numbers.

**Status:** implemented and tested against mocked Meta responses. It has
not been tested with a real Meta account yet. Keep `WHATSAPP_PROVIDER`
set to `disabled` in production until the end-to-end checks at the
bottom of this page pass.

## How it works

1. **Request.** `POST /api/v1/auth/request-otp` with a non-Kenyan number:
   - `OTPDelivery` chooses WhatsApp;
   - a challenge is created;
   - `MetaWhatsAppProvider` sends the authentication template.
2. **Accepted.** Meta answers with a message ID (`wamid`). The challenge
   stores it as `provider_message_id` and sets
   `delivery_status = accepted`.
   - **Accepted is not delivered.** Meta only says it took the request.
3. **Reports.** Meta later posts status reports (`sent`, `delivered`,
   `read`, `failed`) to the webhook. These update `delivery_status`.
4. **Polling.** The app asks
   `GET /api/v1/auth/otp-challenges/{id}/delivery` while it waits (4 s,
   then backing off to 30 s), so it can tell the user quickly when
   WhatsApp could not deliver the code.
   - The endpoint shows no phone number and nothing about whether the
     code is valid.
   - It is rate limited per IP (`OTP_DELIVERY_STATUS_IP_LIMIT`, default
     120 per 15 minutes).
   - It answers 404 once the code has expired.

### Delivery state and authentication state are separate

| Column | Values | Who changes it |
|---|---|---|
| `status` | pending, verified, expired, blocked | Authentication only. Decides whether the code can be used. |
| `delivery_status` | pending → accepted → sent → delivered → read; failed | The provider (send result) and the webhook. Never makes a code usable. |

**Rules for status reports:**
- They only move `delivery_status` forward. Duplicates and late, older
  reports are ignored, so Meta's retries and out-of-order deliveries are
  safe.
- `failed` is final.
- `failed` is ignored after `delivered` or `read`.

**What a `failed` report does:**
- It retires the challenge only if it is still `pending` (`status = expired`).
  The code never arrived, and the user can request a new one at once
  without the 60-second resend cooldown.
- It never touches a challenge that is already verified, expired or
  blocked.
- It writes an `otp_delivery_failed` audit event (`source: webhook`, Meta
  error code).

**Immediate send failures** (Meta rejects the request, timeout, network
error):
- the challenge is expired right away;
- `delivery_status = failed`;
- the API answers `503 OTP_DELIVERY_FAILED` with `details.channel` and
  `details.retryable`;
- no cooldown applies.

**One usable code per number.** A partial unique index allows only one
`pending` challenge per number and purpose. If two requests race, the
loser gets the normal resend-cooldown response with the real remaining
time, plus an `otp_request_blocked` audit event (`concurrent_request`).
If saving the provider's acceptance fails after a successful send, the
request still succeeds; only delivery tracking for that message is lost.

### Meta error handling

Only Meta's numeric error code is kept, in the audit log as
`provider_code`. Meta's message text is never copied, because it can
contain the phone number.

| Meta code (HTTP) | Reason | Retry? |
|---|---|---|
| 0, 3, 10, 190, 200, 131005 (or HTTP 401/403) | `unauthorized`: token invalid/expired or permission missing | No (fix configuration) |
| 4, 80007, 130429, 131048, 131056 (or HTTP 429) | `rate_limited` | Yes |
| 131026, 131049 | `recipient_undeliverable` | No |
| 132000, 132001, 132005, 132007, 132012, 132015, 132016 | `template_rejected`: missing, unapproved, paused, disabled, wrong parameters | No (fix template) |
| 100, 131008, 131009 | `invalid_request` | No |
| 1, 2, 131000, 131016 (or HTTP 5xx) | `provider_unavailable` | Yes |
| timeout / network error | `timeout` / `provider_unreachable` | Yes |
| 2xx without `messages[0].id` | `malformed_response` | Yes |
| anything else | `provider_rejected` | No |

### Message sent

`POST https://graph.facebook.com/{META_GRAPH_API_VERSION}/{META_WHATSAPP_PHONE_NUMBER_ID}/messages`
with `Authorization: Bearer <token>`:

```json
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "+256701234567",
  "type": "template",
  "template": {
    "name": "<META_WHATSAPP_OTP_TEMPLATE_NAME>",
    "language": {"code": "<META_WHATSAPP_OTP_TEMPLATE_LANGUAGE>"},
    "components": [
      {"type": "body", "parameters": [{"type": "text", "text": "<code>"}]},
      {"type": "button", "sub_type": "url", "index": "0",
       "parameters": [{"type": "text", "text": "<code>"}]}
    ]
  }
}
```

This follows Meta's copy-code authentication template example: the code
goes in the body parameter and in the button parameter. `to` is the full
E.164 number **with the `+`**: Meta prepends the business number's own
country code to numbers sent without it, which would misdeliver codes.

## Configuration

All values come from environment variables, are kept in the deployment's
secret store, and never go in the repository. The app refuses to start
with `WHATSAPP_PROVIDER=meta` unless every value is set.

| Variable | Secret? | Where it comes from |
|---|---|---|
| `WHATSAPP_PROVIDER` | No | `disabled` (default), `console` (local only) or `meta` |
| `META_GRAPH_API_BASE_URL` | No | Default `https://graph.facebook.com` |
| `META_GRAPH_API_VERSION` | No | Graph API version to pin, e.g. `v24.0` |
| `META_WHATSAPP_PHONE_NUMBER_ID` | No | WhatsApp Manager / App Dashboard → API Setup → Phone number ID of the sender number |
| `META_WHATSAPP_ACCESS_TOKEN` | **Yes** | Long-lived system-user token with `business_management`, `whatsapp_business_management` and `whatsapp_business_messaging`; choose "never expires" or plan rotation before its expiry |
| `META_WHATSAPP_OTP_TEMPLATE_NAME` | No | Name of the approved authentication template |
| `META_WHATSAPP_OTP_TEMPLATE_LANGUAGE` | No | The template's language code exactly as approved, e.g. `en` or `en_US` |
| `META_APP_SECRET` | **Yes** | App Dashboard → App settings → Basic → App secret (signs webhooks) |
| `META_WEBHOOK_VERIFY_TOKEN` | **Yes** | A random string you choose and enter in the webhook setup |
| `WHATSAPP_SEND_TIMEOUT_SECONDS` | No | Default 10 |

The WhatsApp Business Account ID is not needed by the API. You only use it
in the setup steps below (subscribing the app, creating the template).

## Authentication template requirements

- Category **AUTHENTICATION**, created in WhatsApp Manager or through the
  API, and **approved**.
- A **copy-code** button (`otp_type: COPY_CODE`). The send call always
  fills the button parameter, so a one-tap or zero-tap template would need
  a code change first.
- Body text is fixed by Meta: "<code> is your verification code." Add the
  security recommendation ("For your security, do not share this code.").
- **Code expiration: 5 minutes**, to match `OTP_EXPIRY_SECONDS=300`. The
  expiry line is part of the template; SWETO does not send it.
- The name uses lowercase letters, digits and underscores, e.g.
  `sweto_login_code`.
- The language must match `META_WHATSAPP_OTP_TEMPLATE_LANGUAGE`.

## Webhook

- **Path:** `GET` and `POST` `/api/v1/webhooks/whatsapp`, e.g.
  `https://api.<your-domain>/api/v1/webhooks/whatsapp`. Both answer 404
  unless `WHATSAPP_PROVIDER=meta`.
- **Verification (GET):** answers `hub.challenge` as plain text when
  `hub.mode=subscribe` and `hub.verify_token` matches
  `META_WEBHOOK_VERIFY_TOKEN`; otherwise 403.
- **Notifications (POST):**
  - **Signature:** `X-Hub-Signature-256` must equal the HMAC-SHA256 of
    the raw body keyed with `META_APP_SECRET`, compared in constant time.
    A bad or missing signature gets 401, invalid JSON gets 400, and
    neither changes anything.
  - **Filtering:** only `messages` status reports for our own phone
    number ID are used.
  - **Response:** 200 once processed. Meta retries non-200 answers for up
    to 7 days, and retries are harmless.
- **Logging:** bodies, phone numbers, codes and secrets are never logged;
  only counts are.
- **Early reports:** a report can reach us before the send response has
  been saved. Such reports are kept in `otp_unmatched_delivery_reports`
  and applied as soon as the challenge stores its message ID, so a fast
  `failed` is not lost. Rows older than a day are purged (they belong to
  messages SWETO didn't send).

## Countries offered to the app

`GET /api/v1/auth/phone-countries` lists the supported countries whose
channel is switched on, Kenya first. The app only offers these. While
`WHATSAPP_PROVIDER=disabled`, only Kenya is offered, so there is no
dead-end international sign-up.

## Meta setup steps (Business Manager / Developer Dashboard)

1. **App.** In the App Dashboard, use the app connected to the approved
   WhatsApp Business Account (use case "Connect with customers through
   WhatsApp"). Note the **App secret** (App settings → Basic).
2. **Sender number.** Register the sender phone number on the WhatsApp
   Business Account and set its display name. Note its **Phone number ID**.
3. **Access token.** Business Settings → Users → System users:
   - create (or reuse) a system user;
   - give it the app and the WhatsApp Business Account;
   - generate a token with `business_management`,
     `whatsapp_business_management` and `whatsapp_business_messaging`.
     Meta calls system-user tokens long-lived with an expiry you choose:
     pick "never" or put a rotation date in the calendar.

   The temporary token from API Setup expires quickly; don't use it.
4. **Template.** Create the authentication template described above and
   wait for **Approved**. Note its exact name and language code.
5. **Webhook.** Configure it in App Dashboard → WhatsApp → Configuration:
   - Callback URL: `https://<api host>/api/v1/webhooks/whatsapp`. Deploy
     with `WHATSAPP_PROVIDER=meta` first, or verification will get 404.
   - Verify token: the value of `META_WEBHOOK_VERIFY_TOKEN`.
   - Subscribe to the **messages** field.
6. **Subscribe the app to the WhatsApp Business Account:**
   `POST https://graph.facebook.com/<version>/<WABA_ID>/subscribed_apps`
   with the system-user token. It should answer `{"success": true}`.
7. **Staging configuration.** Put the values in staging's secret store and
   set `WHATSAPP_PROVIDER=meta`.

## Manual validation before turning it on in production

- [ ] Staging starts with `WHATSAPP_PROVIDER=meta` (settings validation
      passes).
- [ ] Meta's webhook verification succeeds (green tick in the dashboard).
- [ ] A Ugandan or Tanzanian test number receives the template on
      WhatsApp. The copy-code button copies the code, and signing in
      works.
- [ ] The challenge goes `accepted` → `sent` → `delivered` → `read` in
      the database.
- [ ] A number that is not on WhatsApp ends `failed` (expect 131026). The
      app shows the WhatsApp failure message, and requesting a new code
      works at once.
- [ ] A wrong token in staging produces `unauthorized` (code 190), with no
      token in the logs.
- [ ] The logs contain no codes, tokens or phone numbers.
- [ ] Kenyan sign-in still goes by SMS.
- [ ] Production: same configuration, then switch `WHATSAPP_PROVIDER=meta`.

Sources (checked 8 Oct 2026):
- https://developers.facebook.com/documentation/business-messaging/whatsapp/reference/whatsapp-business-phone-number/message-api
- https://developers.facebook.com/docs/whatsapp/business-management-api/authentication-templates/copy-code-button-authentication-templates
- https://developers.facebook.com/documentation/business-messaging/whatsapp/support/error-codes
- https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/create-webhook-endpoint
- https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages/status
- https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview
- https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started
