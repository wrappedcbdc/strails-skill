# Status Lifecycles, Error Codes & Troubleshooting

## Response codes (recap)

| Code | Status | HTTP |
|---|---|---|
| `00` | SUCCESS | 200 |
| `01` | VALIDATION_ERROR | 400 |
| `02` | NOT_FOUND | 404 |
| `03` | UNAUTHORIZED | 401/403 |
| `04` | RATE_LIMITED | 429 |
| `05` | INTERNAL_ERROR | 500 |

## Transaction status lifecycles

### User Onramp
```
requested → pending → processing → funded → completed
    |          |           |          |
    v          v           v          v
  failed     failed      failed     failed

with autoSwap, `funded` continues instead as:
funded → swap_queued → swap_processing → completed
                |              |
                v              v
             failed          failed
```
Virtual account sub-statuses: `active` → `expired` (30-min window) or `used`.

### User Offramp
```
pending → processing → bank_verification → transfer_pending
   |          |                |                   |
   v          v                v                   v
cancelled   failed           failed              failed

transfer_pending → transfer_confirmed → payout_pending → completed
                            |                 |
                            v                 v
                         failed             failed
```

### FX Trade
```
pending → locked → signing → settling → completed
             |         |          |
             v         v          v
          expired   expired     failed
```
Can only expire from `locked`/`signing` (5-min lock). Once `settling`, it
either completes or fails — cannot expire.

### Swap
`pending` → `requested` → `queued` → `processing` → `completed` (or `failed`
at any stage).

### Fee Withdrawal
`pending` → `processing` → `completed` (or `failed`).

## Common error code strings

| Error code | HTTP | Meaning |
|---|---|---|
| `AUTHENTICATION_FAILED` | 401 | `x-api-key` missing, malformed, or doesn't exist |
| `AUTHORIZATION_FAILED` | 403 | Key valid but IP not allowlisted, or action not permitted |
| `VALIDATION_ERROR` | 400 | Required field missing or fails format rules |
| `NOT_FOUND` | 404 | Resource ID doesn't exist |
| `RATE_LIMIT_EXCEEDED` | 429 | Exceeded per-minute limit |
| `INTERNAL_ERROR` | 500 | Unexpected server error — retry w/ backoff |

## Common issues & fixes

**401 Unauthorized / 403 Forbidden**
- 401: header must be exactly `x-api-key` (lowercase); confirm sandbox vs
  production key; confirm key hasn't been revoked.
- 403: IP not on allowlist — `POST /manageipallowlist` with `action: "add"`;
  allow up to 60s to propagate. Check your IP: `curl -s https://api.ipify.org`.

**429 Too Many Requests**
- Exponential backoff (1s, 2s, 4s, ...). Queue non-urgent requests and
  dispatch at a steady rate. Cache slow-changing data (e.g. bank lists).
- The response carries `data.retry_after` in seconds — wait at least that
  long. It is a body field, not a `Retry-After` header.

**BVN verification fails**
- Must be exactly 11 numeric digits (no whitespace/hyphens).
- BVN already registered to another Strails user.
- Identity provider couldn't resolve the BVN or is unreachable
  (`response_code: "05"`).
- Cannot retry a `failed` onboarding record — submit a new `/onboarduser`.

**Transaction stuck in pending**
1. Call the relevant status endpoint with `requestId`.
2. If unchanged after 10 min: `POST /manualstatusrecovery` with `requestId`.
3. Still stuck: email support@strails.io with `requestId` + timestamp.

**Webhooks not arriving**
- URL must be HTTPS and publicly reachable.
- Handler must return `200` within 10 seconds — slow/non-200 responses
  trigger retries with backoff.
- Check HMAC verification logic for off-by-one bugs / unhandled exceptions
  before the `200` is sent.
- Check firewall/middleware isn't silently rejecting the POST.

**Virtual account expired**
- 30-minute window. Cannot reactivate — create a new `/cngnonramp` request.

## Filter values reference (for list endpoints)

| Resource | Filter | Valid values |
|---|---|---|
| Deposits | `type` | `fintech_deposit`, `user_onramp` |
| Deposits | `status` | `pending`, `processing`, `completed`, `failed`, `cancelled` |
| Payouts | `type` | `fintech_offramp`, `user_offramp` |
| Payouts | `status` | same as above |
| Transactions | `direction` | `in`, `out` |
| Transactions | `type` | `fintech_deposit`, `user_onramp`, `fintech_offramp`, `user_offramp` |
| Transactions | `status` | same as above |
| FX Orders | `pair` | `CNGN-USDC`, `CNGN-USDT` |
| FX Orders | `side` | `buy`, `sell` |
| FX Orders | `status` | `active`, `paused`, `deleted` |
| FX Trades | `pair` | `CNGN-USDC`, `CNGN-USDT` |
| FX Trades | `side` | `buy`, `sell` |
| FX Trades | `status` | `pending`, `locked`, `signing`, `settling`, `completed`, `expired`, `failed` |
| Asset Withdrawals | `tokenType` | `CNGN`, `USDC`, `USDT` |
| Asset Withdrawals | `status` | `pending`, `confirmed`, `failed` |
| Asset Withdrawals | `sortOrder` | `asc`, `desc` |

## Amount format reminders

| Format | Endpoints | Example |
|---|---|---|
| **Naira** | `/cngnonramp`, `/cngnofframp`, virtual accounts | `5000` = ₦5,000 |
| **Kobo** | all fee endpoints (`/feewithdrawal`, `/getwithdrawalhistory`, `/getaccumulatedfees`, `/fees/strails/preview`, `capFee`) | `50000` = ₦500.00 |
| **Human-readable token units** | `/withdrawasset`, `/swap`, `/swaptrigger`, all FX fields | `100.50` = 100.50 USDC |
| **Smallest unit** | `/fintechtransfer`, `/initiateofframp`, balances | `500000000` = 500 cNGN (6 decimals; DAI 18) |

Fee withdrawals are **kobo, not Naira** — `"amount": 50000` withdraws ₦500.00.
Full per-endpoint table: `payload-formats.md`.

If unresolved: email support@strails.io with `requestId`, full request
payload (redact the API key), and timestamp.
