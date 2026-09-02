# Testing & Sandbox

Strails has **two** distinct pre-production surfaces — don't confuse them:

1. **Staging/test environment** (`https://beta.stablesrail.io/v1/`) — full
   real integration flow (uses your normal API key), for exercising the
   actual staged backend before going live.
2. **Mock Sandbox** (`https://sandbox.stablesrail.io/v1/`) — a fully
   isolated mock that mirrors the API surface with **no real blockchain
   transactions, KYC checks, or payment-provider calls**. Requires a
   separate `sandbox_...` key.

## Mock Sandbox

| Environment | Base URL |
|---|---|
| Sandbox | `https://sandbox.stablesrail.io` (all endpoints under `/v1`) |
| Production | `https://api.strails.io` |

Notes: no real funds touched; uses its own `SANDBOX_*` defaults, not
production secrets; default webhook target is `https://httpbin.org/post` if
you don't configure one; supports an async mock mode for delayed webhook
callbacks.

### Creating & using a sandbox key

Sandbox keys are minted against **production** using a production key:

```http
POST https://api.strails.io/v1/createsandboxapikey
x-api-key: <production-api-key>
```
Returns `data.apiKey` (`sandbox_...`), shown once — save immediately. Use it
as `x-api-key` against sandbox endpoints:

```http
POST https://sandbox.stablesrail.io/v1/onboarduser
x-api-key: sandbox_3fe455526c844f91886ea
{ "bvn": "12345678901" }
```
Keys missing the `sandbox_` prefix, unregistered, or revoked/expired → 401.

### Sync vs. async mock mode

Default: synchronous, immediate "completed"-style response. To simulate
async processing + a webhook callback:

```http
POST https://sandbox.stablesrail.io/v1/onboarduser?mockMode=async
```
or header `x-mock-mode: async`. Query param takes precedence over header; no
param/header = sync. Async responses return `status: "processing"` and a
webhook fires after ~3 seconds.

### Sandbox webhooks

| Setting | Default |
|---|---|
| Webhook URL | `https://httpbin.org/post` |
| Webhook Secret | `sandbox-webhook-secret-do-not-use-in-production` |

Override via `POST /setwebhook` (sandbox): the field is `webhookUrl`, same as
production — `{"webhookUrl": "...", "enabled": true}`.
Signed the same way as production: `HMAC-SHA256(secret, timestamp + "." +
payload)`, headers `X-Strails-Signature` / `X-Strails-Timestamp`. The secret
is **global to the sandbox** (not per-fintech) — don't reuse in production.

Sample sandbox webhook payload:
```json
{
  "eventId": "uuid-event-id", "eventType": "user.onboarded",
  "timestamp": "2026-07-29T14:45:00.000Z", "requestId": "req-s-...",
  "fintechId": "...", "version": "1.0.0", "userId": "usr-s-...",
  "payload": { "firstName": "Sandbox", "lastName": "User", "onboardedAt": "..." }
}
```

### Common test values

| Field | Sample | Constraint |
|---|---|---|
| `bvn` | `12345678901` | 11 digits, numeric — sandbox doesn't validate against a real identity service |

`/onboarduser` takes only `{ "bvn": "..." }` in the sandbox, exactly as in
production.

cNGN assumed 6 decimals: 1,000 cNGN = `1000000000` raw; 500 cNGN =
`500000000` raw. Sandbox wallet addresses are deterministic per request and
carry no real on-chain balance.

---

## Staging test scenarios (beta.stablesrail.io)

Staging runs the real staged backend and uses your **normal API key** — the
`sandbox_` key is only for `sandbox.stablesrail.io`.

Required headers on every request:
```
Content-Type: application/json
Accept: */*
x-api-key: YOUR_API_KEY
```

Work through in order — each step uses data from the previous one:

1. **Test connection** — `GET /getfintechwallet`. 401 → check header casing;
   403 → add your IP via allowlist (step 5); 404 → missing `/v1`.
2. **User onboarding** — `POST /onboarduser` with `{"bvn": "..."}` → save the
   `requestId` → poll `POST /onboardstatus` with `{"requestId": "..."}` →
   take `userId` from the completed response.
3. **Fund a wallet (onramp)** — `POST /cngnonramp` (amount in Naira) →
   `POST /getvirtualaccount` with `{"requestId": "..."}` → simulate the bank
   transfer before `expiresAt` (30 min) → poll `/cngnonrampstatus`.
4. **Process withdrawal (offramp)** — `POST /cngnofframp` (`userId`, `amount`
   in Naira, `accountNumber`, `bankCode`, `ticker`) → poll
   `POST /cngnofframpstatus`.
5. **IP allowlist** — `POST /manageipallowlist` with `action: "add"`/`"remove"`
   and `ipAddress`. **Add the replacement IP before removing the old one** —
   removing your own IP locks you out immediately.
6. **FX quote & trade** — `POST /fx/quote` with `{"pair", "side",
   "cngnAmount"}` (human-readable, min 1,000 cNGN) → save `quoteId` (5-min
   validity) → `POST /fx/trade` with `{"quoteId", "idempotencyKey"}`. There is
   no `userId` on FX endpoints. Trade moves `pending` → `locked` → `signing` →
   `settling` → `completed`; poll `GET /fx/trades/status?tradeId=...`, since
   FX emits no webhooks.

### Postman collection

A ready-to-import collection is at
`github.com/wrappedcbdc/strails-docs/blob/main/postman-collection.json`.
Set env vars `BASE_URL=https://beta.stablesrail.io/v1` and
`API_KEY=<your API key>` (a `sandbox_` key only works against
`sandbox.stablesrail.io`). For Newman/CLI use, strip the first line first:
`sed '1d' postman-collection.json > clean-collection.json`.

### Testing tips

- Use ₦100–₦500 for onramp/offramp tests so amount-format mistakes (e.g.
  sending Naira on a token endpoint) surface immediately.
- webhook.site or `ngrok http 3000` for local webhook testing.
- BVNs must be exactly 11 digits or validation fails before the lookup runs.
- Virtual accounts expire after 30 minutes — re-run `/cngnonramp` if your
  test transfer simulation times out.
