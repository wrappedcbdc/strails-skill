# Management API — Webhooks, IP Allowlist, Keys, Preferences

| Endpoint | Method | Description |
|---|---|---|
| `/regenerateapikey` | GET | Rotate API key (invalidates old immediately) |
| `/storepublickey` | POST | Register your X25519 public key (payload encryption) |
| `/getplatformpublickey` | GET | Strails' X25519 public key |
| `/getaeskey` | GET | Raw AES key (legacy) |
| `/setwebhook` | POST | Configure webhook URL + secret + event subscriptions |
| `/togglewebhookstatus` | POST | Enable/disable delivery without changing config |
| `/getwebhook` | GET | Current webhook configuration |
| `/manageipallowlist` | POST | list/add/remove/check IP allowlist entries |
| `/updateonrampasset` | POST | Per-user default onramp asset preferences |
| `/autosigning/config` | GET | Auto-approval threshold for cNGN buying |
| `/createsandboxapikey` | POST | Create a sandbox-only API key |

## POST /setwebhook

```json
{ "webhookUrl": "https://your-domain.com/webhook", "secret": "your_webhook_secret_key", "enabled": true, "events": ["all"] }
```
`events`: pass `["all"]` for every type, or specific names from
`webhook-events.md`. The field is `webhookUrl` (not `url`), in every
environment including the mock sandbox. **Rate-limited to 10 rpm** — don't call more than once
per deployment. Response: `webhookUrl`, `enabled`, `hasSecret`,
`urlValidated` (Strails reached the URL), `updatedAt`.

## POST /togglewebhookstatus

```json
{ "enabled": true }
```
Pause/resume delivery without touching URL or secret.

## GET /getwebhook

Returns `webhookUrl` (masked), `enabled`, `hasSecret`, `events[]`,
`updatedAt`.

## POST /storepublickey / GET /getplatformpublickey / GET /getaeskey

See `authentication.md` "Payload encryption" section for the full
encrypt/decrypt flow. `/storepublickey` body: `{ "data": "<64-hex X25519 public key>" }`.

## POST /manageipallowlist

```json
{ "action": "list" }              // or "add" / "remove" / "check"
{ "action": "add", "ipAddress": "203.0.113.45", "description": "Office network IP" }
{ "action": "remove", "ipAddress": "10.0.0.5" }   // or by "index" (0-based, from "list")
{ "action": "check" }             // check the caller's current IP
```
Changes propagate to all servers within **~30 seconds**. `"check"` returns
`yourIp`, `isAllowed`, `matchedRule`, `totalConfiguredIps`. **Never remove
your only active IP without adding the replacement first** — you'll lock
yourself out immediately.

## POST /updateonrampasset

```json
{
  "userId": "user_hash",
  "preferences": { "defaultAsset": "USDC", "autoSwap": true, "slippageTolerance": "0.5" }
}
```
Sets per-user default onramp target asset, auto-swap-on-receipt, and
slippage tolerance for that user's future onramps.

## GET /autosigning/config

Returns `enabled`, `thresholdAmount` (max cNGN auto-approved),
`currency` (`"CNGN"`), `maxDailyAmount`, `restrictToFintech`. This is
distinct from the FX auto-signing config in `fx-trading.md` — this one
governs cNGN buying/minting auto-approval, not FX trade signing.

## POST /createsandboxapikey

```http
POST https://api.strails.io/v1/createsandboxapikey
x-api-key: <production-api-key>
```
Requires a **production** key to call. Returns a `sandbox_...`-prefixed key,
shown once. See `testing-and-sandbox.md`.

## GET /regenerateapikey

Immediately invalidates the current key. New key (`data.apiKey`) shown only
once — store it before making further calls.
