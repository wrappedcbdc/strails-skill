# Request/Response Payload Formats

## Standard request

```
Content-Type: application/json
Accept: */*
x-api-key: YOUR_API_KEY
```

## Standard response envelope

```json
// Success
{ "status": "Success", "response_code": "00", "message": "...", "data": { ... } }

// Error
{ "status": "Error", "response_code": "01", "message": "Validation error: Invalid amount",
  "error": { "field": "amount", "reason": "Must be greater than 0" } }
```

Real integrations should not assume only `Success`/`Error` values. Across
endpoint families and versions you may see `Success`, `Error`, `Failed`,
`success`, or `error`. Parse `response_code` and HTTP status as canonical, and
normalize `status` to lowercase only for UI/logging.

Example (Node.js):

```javascript
function classifyResponse(httpStatus, body) {
  const code = String(body?.response_code ?? "");
  const normalized = String(body?.status ?? "").toLowerCase();

  const okByCode = code === "00";
  const okByHttp = httpStatus >= 200 && httpStatus < 300;
  const okByStatus = normalized === "success";

  return {
    success: okByCode || (okByHttp && okByStatus),
    responseCode: code,
    status: normalized,
    message: body?.message ?? "",
  };
}
```

| response_code | Status | HTTP | Description |
|---|---|---|---|
| `00` | SUCCESS | 200 | OK |
| `01` | VALIDATION_ERROR | 400 | One or more fields failed validation |
| `02` | NOT_FOUND | 404 | Resource doesn't exist |
| `03` | UNAUTHORIZED | 401/403 | Auth failed or access denied |
| `04` | RATE_LIMITED | 429 | Rate limit exceeded |
| `05` | INTERNAL_ERROR | 500 | Server-side error |

## Pagination shape (all list endpoints)

```json
{
  "data": {
    "items": [],
    "pagination": {
      "total": 243, "limit": 50, "offset": 0,
      "currentPage": 1, "totalPages": 5,
      "hasNextPage": true, "hasPreviousPage": false
    }
  }
}
```
Control with `limit`/`offset` query params, e.g.
`GET /transactions?limit=50&offset=100`. FX trade listings are the
exception: `GET /fx/trades` uses cursor pagination via `startAfter`.

## Amount formatting — read this before sending any amount

Four formats are in use. Which applies is a property of the individual
endpoint — there is no blanket "fiat vs blockchain" rule.

| Format | Meaning | Endpoints |
|---|---|---|
| **Naira** | `5000` = ₦5,000 | `/cngnonramp`, `/cngnofframp`, virtual-account amounts (`amount`, `baseAmount`, `totalAmountWithFee`, `feeBreakdown.*`) |
| **Kobo** | `50000` = ₦500.00 | All fee endpoints: `/feewithdrawal`, `/getwithdrawalhistory`, `/getaccumulatedfees`, `/fees/strails/preview`, `capFee` on `/managefees` |
| **Human-readable token units** | `100.50` = 100.50 USDC | `/withdrawasset`, `/swap`, `/swaptrigger`, and all FX fields (`price`, `minAmount`, `maxAmount`, `cngnAmount`, `tokenAmount`) |
| **Smallest unit (wei)** | `5000000` = 5.0 cNGN | `/fintechtransfer`, `/initiateofframp`, balances, `amount` in blockchain status responses |

Two pairs that look symmetrical but are not:

- `/cngnofframp` takes **Naira** (`5000` = ₦5,000); `/initiateofframp` takes
  the **smallest unit** (`5000000` = 5.0 cNGN).
- `/withdrawasset` takes **human-readable units** (`100` = 100 cNGN);
  `/fintechtransfer` takes the **smallest unit** (`5000000` = 5.0 cNGN).

Both are accepted either way — the amount is simply wrong by a factor of a
million.

### Token decimals

| Token | Decimals | 1 unit smallest form |
|---|---|---|
| cNGN | 6 | `1000000` |
| USDC | 6 | `1000000` |
| USDT | 6 | `1000000` |
| DAI | 18 | `1000000000000000000` |

### Conversion helpers

```javascript
// Work on the string form: `amount * 10 ** decimals` overflows
// Number.MAX_SAFE_INTEGER at 18 decimals and loses precision before that.
function toSmallestUnit(amount, decimals) {
  const [whole, frac = ""] = String(amount).split(".");
  if (frac.length > decimals) {
    throw new RangeError(`${amount} has more than ${decimals} decimal places`);
  }
  return (BigInt(whole) * 10n ** BigInt(decimals) +
          BigInt((frac + "0".repeat(decimals)).slice(0, decimals) || "0")).toString();
}
// Returns a string — an 18-decimal balance loses precision as a JS Number.
function fromSmallestUnit(raw, decimals) {
  const padded = String(raw).padStart(decimals + 1, "0");
  const whole = padded.slice(0, -decimals);
  const frac = padded.slice(-decimals).replace(/0+$/, "");
  return frac ? `${whole}.${frac}` : whole;
}
function formatNaira(amount) {
  return `₦${Number(amount).toLocaleString("en-NG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
// toSmallestUnit(500, 6)         === "500000000"  (500 cNGN)
// fromSmallestUnit(500000000, 6) === "500"
```

```python
from decimal import Decimal

def to_smallest_unit(amount: float, decimals: int) -> int:
    return int(Decimal(str(amount)) * (10 ** decimals))

def from_smallest_unit(raw: int, decimals: int) -> Decimal:
    return Decimal(raw) / (10 ** decimals)

def format_naira(amount: float) -> str:
    return f"₦{amount:,.2f}"
```

```php
function toSmallestUnit(float $amount, int $decimals): string {
    return bcmul((string) $amount, bcpow('10', (string) $decimals, 0), 0);
}
function fromSmallestUnit(string $raw, int $decimals): string {
    return bcdiv($raw, bcpow('10', (string) $decimals, 0), $decimals);
}
```

## Webhook payload formats — two shapes exist

Detect which one you got by top-level key:

```javascript
function detectPayloadFormat(payload) {
  if (payload.notify && payload.Data) return "virtual_account";
  if (payload.event && payload.data) return "legacy";
  return "unknown";
}
```

| | Legacy | Virtual Account |
|---|---|---|
| Event type | `event` | `notify` |
| Status | `data.status` | `notifyType` + `Data.Status` |
| Transaction ID | `data.transaction_id` | `Data.Id` |
| Amount | `data.amount` | `Data.Amount` |
| Reference | `data.reference` | `Data.TransactionReference` |
| Timestamp | `data.timestamp` | `Data.Timestamp` |
| Sender name | `data.sender_name` | `Data.SenderName` |
| Virtual account | `data.virtual_account_id` | `Data.VirtualAccountId` |

Legacy example: `{"event": "wallet_funding", "data": {"status": "successful", ...}}`.
Virtual Account example: `{"notify": "wallet_funding", "notifyType": "successful", "Data": {...}}`.

Note: this legacy/VA split is a separate, older convention from the
"22-events" `eventType`/`payload` schema documented in `webhook-events.md` —
some integrations may still see either shape depending on the originating
flow. Always validate the signature before processing regardless of shape.

## Data type & validation reference

| Field type | Format | Example |
|---|---|---|
| User ID | opaque string issued by Strails (typically 64-char hex) — echo back what `/onboardstatus` returns; never construct one | `77aefb50d96d0a63...` |
| Email | RFC 5321 | `user@example.com` |
| Phone | Nigerian intl format | `+2348012345678` |
| BVN | exactly 11 numeric digits | `12345678901` |
| Bank code | 3-digit numeric string | `058` |
| Currency | ISO 4217 uppercase | `NGN` |
| Fiat amount | int or decimal | Naira on onramp/offramp/virtual accounts; **kobo** on all fee endpoints |
| Token amount | integer or decimal string | smallest unit or human-readable, per endpoint — see above; use BigInt in JS for smallest-unit values |
| Percentage | percent value | `1.5` = 1.5% (`percentageFee`, `strailsFeePercentage`, `spread`) |
| Timestamps | ISO 8601 UTC | `2023-12-07T10:30:00Z` |

## HTTP status codes

| Code | Meaning | When |
|---|---|---|
| 200 | OK | Success |
| 400 | Bad Request | Missing/malformed fields |
| 401 | Unauthorized | API key missing/invalid |
| 403 | Forbidden | Key valid, IP not allowlisted, or insufficient permission |
| 404 | Not Found | Endpoint/resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected failure — contact support if persistent |
