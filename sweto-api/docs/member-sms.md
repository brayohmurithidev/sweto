# Member SMS

SWETO texts a gym's members on the gym's behalf, through the same SMS
provider as sign-in codes (`SMS_PROVIDER`: `advanta`, `africastalking`, or
`console` in development, which writes messages to the log instead).

## When members get a message

| Message | Sent when | At most |
| --- | --- | --- |
| Welcome, with a check-in code | The first cash payment is recorded | Once per member |
| Payment receipt | Every later payment | Once per paid period |
| New check-in code | Staff issue a new code | Each time |
| Expiry reminder | 3 days before the last paid day, and on that day (gym's own calendar) | Once each per period |

The welcome carries a check-in code, so recording the first payment issues a
fresh code: only a hash of any earlier code exists, and the earlier code stops
working. Texts are never stored, because they can contain a code.

All texts are plain ASCII and fit one 160-character segment (gym names are
shortened to 24 characters); see `app/modules/members/messages.py`.

## Consent and opting out

A member only gets SMS when staff confirm, while adding them or later
(`PUT /gyms/{gym_id}/members/{id}/sms {"enabled": true}`), that the member
agreed. Who confirmed it and when is recorded. `{"enabled": false}` records
an opt-out, which wins until consent is confirmed again.

Every message ends with how to stop: *"To stop SMS, tell the gym or call
<gym phone>."* It does not say "reply STOP": with an alphanumeric sender ID
(such as `FAZILABS` on Advanta) the channel is one-way and replies never
arrive. **To revisit:** with a two-way shortcode, accept STOP replies and
record the opt-out automatically.

## Failures

Messages are sent after the payment or code change is saved, so a slow or
failing provider can delay the response (up to `SMS_SEND_TIMEOUT_SECONDS`)
but never undoes it. Every attempt is recorded in `member_messages` with
`sent` or `failed` and a reason; failed welcomes and receipts are not retried
automatically.

## Scheduling reminders

Reminders are sent by a command that is safe to run as often as you like:

```bash
cd sweto-api
uv run python -m app.jobs.membership_reminders
```

Each reminder is recorded before it is sent, so repeated or overlapping runs
never send one twice. Run it hourly so members in every gym's time zone get
theirs early in their day, for example with cron:

```cron
0 * * * * cd /srv/sweto/sweto-api && uv run python -m app.jobs.membership_reminders >> /var/log/sweto/reminders.log 2>&1
```

No scheduler is part of the API itself yet.
