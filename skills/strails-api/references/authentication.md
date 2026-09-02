# Authentication, Rate Limits, Encryption & Webhook Signatures

## Base URLs

| Environment | Base URL |
|---|---|
| Production | `https://api.strails.io/v1/` |
| Test/staging | `https://beta.stablesrail.io/v1/` |
| Mock sandbox | `https://sandbox.stablesrail.io/v1/` |

## API key auth

Every request needs, over HTTPS only:

```
x-api-key: YOUR_API_KEY
Content-Type: application/json
```

The header name **must be lowercase** `x-api-key`. `X-Api-Key` or `Authorization`
will 401 even with a valid key.

```bash
curl --request GET \
  --url https://api.strails.io/v1/transactions \
  --header "x-api-key: YOUR_API_KEY" \
  --header "Content-Type: application/json"
```

To obtain a key, email support@strails.io. Store it as a server-side env var
(`STRAILS_API_KEY`) — never in source, never client-side.

### Rotating your key

`GET /regenerateapikey` — issues a new key and **immediately invalidates the
old one**. The new key is shown only once in the response (`data.apiKey`).

### Sandbox keys

Sandbox keys are created against **production** using a production key:

```http
POST https://api.strails.io/v1/createsandboxapikey
x-api-key: <production-api-key>
```

Returns `data.apiKey` prefixed `sandbox_...`, shown once. Use it as
`x-api-key` against `https://sandbox.stablesrail.io/v1/...`. Keys missing the
`sandbox_` prefix, unregistered, or revoked return 401.

## Rate limits

Endpoints with no explicit limit inherit the default of **30 rpm**. On `429`,
respect the `retry_after` (seconds) in the response and use exponential
backoff.

```json
{
  "status": "Error",
  "response_code": "04",
  "message": "Too many requests. Please try again later.",
  "data": { "error": "Rate limit exceeded", "retry_after": 60 }
}
```

**User management**
| Endpoint | Limit |
|---|---|
| `/onboarduser` | 100 rpm |
| `/onboardstatus` | 200 rpm |
| `/getuserdetails` | 100 rpm |
| `/manageuserstatus` | 30 rpm |
| `/listfintechusers` | 100 rpm |

**Virtual accounts & wallet**
| Endpoint | Limit |
|---|---|
| `/getvirtualaccount` | 10 rpm (configured as 100 per 10-minute window) |
| `/getfintechvirtualaccount` | 30 rpm |
| `/getfintechwallet` | 30 rpm |
| `/addexternalwallet` | 30 rpm |
| `/updateexternalwalletstatus` | 30 rpm |
| `/removeexternalwallet` | 30 rpm |
| `/listuserwallets` | 100 rpm |
| `/migrateuserwallets` | 30 rpm |

**Transactions**
| Endpoint | Limit |
|---|---|
| `/cngnonramp` | 100 rpm |
| `/cngnofframp` | 100 rpm |
| `/cngnonrampstatus` | 30 rpm |
| `/cngnofframpstatus` | 30 rpm |
| `/withdrawasset` | 30 rpm |
| `/fintechtransfer` | 30 rpm |
| `/initiateofframp` | 30 rpm |
| `/getofframpstatus` | 30 rpm |
| `/deposits`, `/payouts`, `/transactions` | 100 rpm |
| `/swaptrigger`, `/swap` | 30 rpm |
| `/swapstatus` | 60 rpm |

**FX orderbook & trading**
| Endpoint | Method | Limit |
|---|---|---|
| `/fx/limit-order` | POST | 30 rpm |
| `/fx/limit-order/update` | PUT | 30 rpm |
| `/fx/limit-order/delete` | DELETE | 30 rpm |
| `/fx/limit-orders` | GET | 100 rpm |
| `/fx/orderbook` | GET | 100 rpm |
| `/fx/orderbook/stats` | GET | 60 rpm |
| `/fx/orderbook-token` | GET | 30 rpm |
| `/fx/quote` | POST | 60 rpm |
| `/fx/trade` | POST | 30 rpm |
| `/fx/market-order` | POST | 30 rpm |
| `/fx/trades/status` | GET | 60 rpm |
| `/fx/trades` | GET | 100 rpm |

`/setwebhook` is separately rate-limited to **10 rpm** — avoid calling it
more than once per deployment.

## Error format & global codes

```json
{
  "status": "Error",
  "response_code": "01",
  "message": "Human-readable error message",
  "data": { "error": "Validation failed", "details": { "field": "..." } }
}
```

`response_code` is always one of the two-digit envelope codes (`00`-`05`) —
never the HTTP status code.

Status casing varies by endpoint family (`Error`, `error`, or `Failed`). Keep
auth/error branching keyed on HTTP + `response_code`, never on the literal
`status` string.

| Code string | HTTP | Meaning |
|---|---|---|
| `AUTHENTICATION_FAILED` | 401 | Invalid/missing API key |
| `AUTHORIZATION_FAILED` | 403 | Caller IP not allowlisted, or action not permitted |
| `VALIDATION_ERROR` | 400 | Invalid request params |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server-side error |

Full status-lifecycle and troubleshooting tables are in
`status-codes-and-errors.md`.

## Payload encryption (X25519 / libsodium sealed-box) — optional, recommended for production

Use for any production integration handling PII, wallet addresses, or
financial data.

1. Generate your own X25519 keypair.
2. Register your **public** key: `POST /storepublickey` with
   `{ "data": "<64-hex-char public key>" }`. Strails then seals all response
   payloads and webhook bodies to this key.
3. Fetch Strails' public key: `GET /getplatformpublickey` → use it to seal
   *your* requests to Strails.
4. Legacy AES key (for legacy AES-GCM payloads / webhook sig fallback):
   `GET /getaeskey`.

### Encrypt a request (Node.js)

```javascript
const sodium = require('libsodium-wrappers');
await sodium.ready;

const strailsPublicKey = sodium.from_hex(process.env.STRAILS_PUBLIC_KEY_HEX);
const payload = JSON.stringify({ bvn: '12345678901', userId: 'user_uniqueID' });
const encrypted = sodium.crypto_box_seal(sodium.from_string(payload), strailsPublicKey);
const base64Payload = sodium.to_base64(encrypted);

await fetch('https://api.strails.io/v1/onboarduser', {
  method: 'POST',
  headers: { 'x-api-key': process.env.STRAILS_API_KEY, 'Content-Type': 'application/json' },
  body: JSON.stringify({ payload: base64Payload }),
});
```

### Decrypt a response (Node.js)

```javascript
const yourPublicKey  = sodium.from_hex(process.env.MY_PUBLIC_KEY_HEX);
const yourPrivateKey = sodium.from_hex(process.env.MY_PRIVATE_KEY_HEX);
const encryptedBytes = sodium.from_base64(responseBody.payload);
const decryptedBytes = sodium.crypto_box_seal_open(encryptedBytes, yourPublicKey, yourPrivateKey);
const data = JSON.parse(sodium.to_string(decryptedBytes));
```

Python keypair generation: `nacl.public.PrivateKey.generate()` (PyNaCl).

Best practices: never expose the private key client-side or in logs; store in
a secrets manager; rotate periodically; test the round-trip against staging
before enabling in production.

## Webhook signature verification (HMAC-SHA256)

Every webhook delivery includes:

| Header | Description |
|---|---|
| `X-Strails-Signature` | HMAC-SHA256 hex digest over `timestamp + "." + raw_body` |
| `X-Strails-Timestamp` | ISO 8601 send time |
| `X-Webhook-ID` | Unique UUID per delivery attempt (use to dedupe retries) |
| `X-Strails-Event` | Event type name |

```
signature = HMAC-SHA256(webhook_secret, timestamp + "." + raw_payload_string)
```

Use the **raw** body string — do not `JSON.parse` then re-serialize before
hashing, or the signature won't match.

### Node.js (Express)

```javascript
const express = require('express');
const crypto  = require('crypto');
const app = express();

app.post('/webhooks/strails', express.raw({ type: 'application/json' }), async (req, res) => {
  const signature = req.headers['x-strails-signature'];
  const timestamp  = req.headers['x-strails-timestamp'];
  const rawBody    = req.body.toString('utf-8');

  if (!signature || !timestamp) return res.status(400).send('Missing signature headers');

  const ageSeconds = (Date.now() - new Date(timestamp).getTime()) / 1000;
  if (ageSeconds > 300) return res.status(400).send('Webhook timestamp too old');

  const expected = crypto.createHmac('sha256', process.env.STRAILS_WEBHOOK_SECRET)
    .update(`${timestamp}.${rawBody}`).digest('hex');

  const isValid = (() => {
    try {
      return crypto.timingSafeEqual(Buffer.from(signature, 'hex'), Buffer.from(expected, 'hex'));
    } catch { return false; }
  })();
  if (!isValid) return res.status(401).send('Invalid signature');

  const event = JSON.parse(rawBody);
  await queue.add({ eventType: event.eventType, payload: event.payload }); // process async
  res.sendStatus(200); // ack immediately
});
```

### Python

```python
import hmac, hashlib

def verify_strails_webhook(raw_body: bytes, timestamp: str, signature: str, webhook_secret: str) -> bool:
    expected = hmac.new(
        webhook_secret.encode('utf-8'),
        f"{timestamp}.{raw_body.decode('utf-8')}".encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Configure the secret via `POST /setwebhook` (see `management-and-security.md`).
Use ≥32 bytes of random data (`openssl rand -hex 32`). Always return `200 OK`
fast and process asynchronously — slow/failing handlers cause retries and
duplicate events.
