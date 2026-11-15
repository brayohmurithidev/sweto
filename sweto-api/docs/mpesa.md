# M-Pesa renewals (STK Push)

Staff send an M-Pesa PIN prompt to a member's phone for a plan. The
membership is only extended when M-Pesa confirms the money.

## Flow

1. `POST /gyms/{gym_id}/members/{id}/payments/mpesa {"plan_id": ...}` (owner
   or manager). It creates a `pending_payment` membership, a pending `payments`
   row and a `payment_transactions` row, then sends the STK Push. The app
   polls `GET /gyms/{gym_id}/payments/{payment_id}`.
2. Safaricom posts the result to
   `{MPESA_CALLBACK_BASE_URL}/api/v1/payments/mpesa/callback/{MPESA_CALLBACK_TOKEN}`.
   On success the membership's dates are fixed at that moment, by the gym's
   calendar (day after the current paid period, or today), and the member gets
   the welcome or receipt SMS if they agreed to SMS.
3. If the callback never arrives, the reconcile job asks Daraja.

Rules:

- One prompt per member at a time (3 minutes).
- The amount M-Pesa reports must equal the amount requested, or the payment
  isn't activated: staff check the member's M-Pesa message and record it by
  hand.
- Callbacks and status queries settle a payment once: a retried or late
  callback changes nothing.
- Callbacks without the token get a 404. Unreadable or unknown results are
  acknowledged (so Safaricom stops retrying) and logged without the payer's
  number.

## Settings

| Setting | Meaning |
| --- | --- |
| `MPESA_MODE` | `disabled` (default), `simulated` (local only), `sandbox`, `production` |
| `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET` | Daraja app credentials |
| `MPESA_SHORTCODE`, `MPESA_PASSKEY` | Default account for gyms without their own, sandbox only (`174379` and Safaricom's test passkey) |
| `MPESA_CREDENTIALS_KEY` | Fernet key that encrypts gyms' passkeys; required in production |
| `MPESA_TRANSACTION_TYPE` | `CustomerPayBillOnline` (Pay Bill) or `CustomerBuyGoodsOnline` (Till) |
| `MPESA_PARTY_B` | Till number for Buy Goods; defaults to the shortcode |
| `MPESA_CALLBACK_BASE_URL` | Public https base of this API |
| `MPESA_CALLBACK_TOKEN` | Random secret, at least 24 characters, in the callback path |
| `MPESA_PENDING_TIMEOUT_MINUTES` | Give up on an unanswered prompt after this long (default 15) |

The API refuses to start with missing settings, an http callback URL,
`simulated` outside local/development/testing, or `sandbox` in production.

## Reconcile job

```bash
uv run python -m app.jobs.mpesa_reconcile
```

Run it every few minutes (for example `*/5 * * * *` in cron). It queries
prompts still pending after a minute, settles them, and fails those with no
answer after `MPESA_PENDING_TIMEOUT_MINUTES`.

## Trying it locally

Set `MPESA_MODE=simulated` and `MPESA_CALLBACK_TOKEN` to any 24+ character
string. Requests are accepted without touching Safaricom and the API logs the
checkout ID. Complete one yourself:

```bash
curl -X POST "http://localhost:8000/api/v1/payments/mpesa/callback/$MPESA_CALLBACK_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"Body":{"stkCallback":{"MerchantRequestID":"SIM","CheckoutRequestID":"<checkout id from the log>","ResultCode":0,"ResultDesc":"ok","CallbackMetadata":{"Item":[{"Name":"Amount","Value":5000},{"Name":"MpesaReceiptNumber","Value":"SIM123ABC"}]}}}}'
```

Use `"ResultCode":1032` (and no metadata) to see a cancelled prompt.

## Each gym's own till

Money goes to **each gym's own Pay Bill or Till**; SWETO only sends the prompt.
The owner adds it in the app (More → M-Pesa till), or with
`PUT /gyms/{gym_id}/mpesa-account` (owner only):

| Field | Pay Bill | Till (Buy Goods) |
| --- | --- | --- |
| `account_type` | `paybill` | `till` |
| `shortcode` | the Pay Bill number | the store / head-office number the passkey belongs to |
| `till_number` | not used | the till the money goes to |
| `passkey` | Lipa na M-Pesa Online passkey from Safaricom | same |

- The passkey is encrypted with `MPESA_CREDENTIALS_KEY` (Fernet) and never
  returned; leave it out on later saves to keep it. Changing the key makes
  saved passkeys unreadable, so keep it with the other secrets.
- Generate a key with
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- Every prompt and status query for a gym uses that gym's account. In
  production a gym without one can't request M-Pesa payments; in sandbox and
  simulated mode such gyms fall back to `MPESA_SHORTCODE`/`MPESA_PASSKEY`.
- Safaricom must link each gym's shortcode to SWETO's Daraja app (their
  "Go Live" process) before prompts from it work in production.
