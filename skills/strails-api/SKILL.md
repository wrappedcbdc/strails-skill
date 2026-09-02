---
name: strails-api
description: Reference for integrating the Strails API — stablecoin orchestration for cNGN, USDC, and USDT covering NGN onramp/offramp, multi-chain wallets (Smart Wallet, Multi-Chain/Managed Wallet, MPC Vault), P2P FX orderbook trading, virtual accounts, fees, and webhooks. Use this skill whenever the user is writing code against Strails, mentions "Strails", "cNGN", "stablesrail.io", or api.strails.io, or is building onramp/offramp, wallet, or FX trading features for a Nigerian fintech/stablecoin product. Trigger even if they just paste a Strails endpoint or curl command without naming the skill.
---

# Strails API

Strails is a stablecoin orchestration and P2P FX orderbook platform for cNGN
(Naira-pegged stablecoin), USDC, and USDT. It provides NGN bank-rail
onramp/offramp, multi-chain wallet infrastructure, and cNGN↔USDC/USDT trading
between fintechs.

This skill is a programming reference — use it to write correct API calls,
webhook handlers, and integration code. Read only the reference file(s)
relevant to the task; don't load everything.

## Base URLs & auth (always relevant)

| Environment | Base URL |
|---|---|
| Production | `https://api.strails.io/v1/` |
| Test/staging | `https://beta.stablesrail.io/v1/` |
| Mock sandbox | `https://sandbox.stablesrail.io/v1/` |

Every path is mounted under `/v1` — omitting it 404s.

Every request needs these headers (header name is case-sensitive — must be lowercase):

```
x-api-key: YOUR_API_KEY
Content-Type: application/json
```

All requests must be HTTPS. A 401 almost always means the header was cased
wrong (`X-Api-Key` fails; it must be `x-api-key`) or the key is wrong/revoked.
A 403 means the key is valid but the caller's IP isn't on the allowlist.

Test/staging uses your normal API key. The mock sandbox is a separate,
fully-isolated environment that needs a `sandbox_`-prefixed key minted against
production — see `references/testing-and-sandbox.md`.

## Response envelope (every response, every endpoint)

```json
{
  "status": "Success",       // may also be "Error", "Failed", "success", or "error"
  "response_code": "00",     // 00 success, 01 validation, 02 not found, 03 unauthorized, 04 rate limited, 05 internal
  "message": "...",
  "data": { ... }             // or "error": {...} on failure
}
```

Two rules that prevent most integration bugs:

- **Never branch on `status`.** Its casing varies across endpoint families.
  Key control flow on `response_code` + HTTP status; normalize `status` only
  for display/analytics.
- **`response_code` is always `00`–`05`**, never the HTTP status code.

Most operations are **asynchronous**: the initial call returns a `requestId`
immediately; poll the matching status endpoint or listen for a webhook to
learn the final outcome.

## Amount formats — the #1 source of bugs

Strails uses **four** amount formats. Which one applies is a property of the
individual endpoint, not of whether the operation is "fiat" or "on-chain".
Always check this table before sending an amount.

| Format | Meaning | Endpoints |
|---|---|---|
| **Naira** | `5000` = ₦5,000 | `/cngnonramp`, `/cngnofframp`, all virtual-account amounts |
| **Kobo** | `50000` = ₦500.00 | Every fee endpoint: `/feewithdrawal`, `/getwithdrawalhistory`, `/getaccumulatedfees`, `/fees/strails/preview`, and `capFee` on `/managefees` |
| **Human-readable token units** | `100.50` = 100.50 USDC | `/withdrawasset`, `/swap`, `/swaptrigger`, and every FX field (`price`, `minAmount`, `maxAmount`, `cngnAmount`, `tokenAmount`) |
| **Smallest unit (wei)** | `5000000` = 5.0 cNGN | `/fintechtransfer`, `/initiateofframp`, balances, and `amount` in blockchain status responses |

Two pairs look symmetrical but are not — these are the classic 10⁶-factor bugs:

- `/cngnofframp` takes **Naira**; `/initiateofframp` takes the **smallest unit**.
- `/withdrawasset` takes **human-readable units**; `/fintechtransfer` takes the **smallest unit**.

| Token | Decimals | 1 unit in smallest form |
|---|---|---|
| cNGN | 6 | `1000000` |
| USDC | 6 | `1000000` |
| USDT | 6 | `1000000` |
| DAI | 18 | `1000000000000000000` |

See `references/payload-formats.md` for conversion helpers (JS/Python/PHP)
and the full data-type/validation reference. Don't use
`amount * 10 ** decimals` in JS — it overflows at 18 decimals.

## Reference files — read what's relevant to the task

| File | Covers |
|---|---|
| `references/authentication.md` | API keys, rate limits (per-endpoint table), error codes, X25519 payload encryption, HMAC webhook verification |
| `references/quickstart-and-flows.md` | End-to-end walkthrough: connect → webhook → onboard user → fund wallet → withdraw → FX trade. Best starting point for a new integration |
| `references/user-management.md` | `/onboarduser` (BVN KYC), onboarding status, get/list/activate users |
| `references/wallets.md` | Wallet management API (`/getfintechwallet`, external wallets, balances) plus the three wallet types: Smart Wallet (EIP-1167), Multi-Chain/Managed Wallet (HSM), MPC Vault |
| `references/virtual-accounts.md` | Virtual account types (fintech permanent / user permanent / transaction temporary), fee breakdown fields, deposit lifecycle, payout bank accounts |
| `references/transactions.md` | `/cngnonramp`, `/cngnofframp`, `/withdrawasset`, `/fintechtransfer`, `/initiateofframp`, swaps, deposits/payouts/transactions listing, status and recovery flows |
| `references/fx-trading.md` | FX settings, MPC registration, auto-signing controls (`/fx/auto-signing/*`), orderbook (limit orders, public orderbook), and trade execution/status lifecycle |
| `references/fees.md` | Fee configuration (`/managefees`), accumulated fees, fee withdrawal, Strails fee preview — all in kobo |
| `references/management-and-security.md` | Webhook registration/toggle, IP allowlist, API key rotation + sandbox key creation, X25519/AES key endpoints, per-user asset preferences |
| `references/webhook-events.md` | All 22 webhook event types with payload schemas, by category |
| `references/payload-formats.md` | Request/response envelope, pagination shape, amount conversion helpers, data type validation rules |
| `references/status-codes-and-errors.md` | Every status lifecycle (onramp/offramp/swap/trade/fee-withdrawal), error code strings, common-issue fixes |
| `references/testing-and-sandbox.md` | Test/staging environment, mock sandbox, sync/async mock mode, test values, Postman collection |
| `references/going-live.md` | Production launch checklist |

## Capability map (fast endpoint routing)

Use this map to route user requests to the right endpoint families quickly.

- User onboarding/KYC: `/onboarduser`, `/onboardstatus`, `/getuserdetails`, `/manageuserstatus`, `/listfintechusers`
- Wallets: `/getfintechwallet`, `/addexternalwallet`, `/updateexternalwalletstatus`, `/removeexternalwallet`, `/listuserwallets`, `/migrateuserwallets`
- Balances: `/balance/multi`, `/balance/address`, `/balance/user/:userId`
- Virtual accounts: `/getvirtualaccount`, `/getfintechvirtualaccount`
- Onramp/offramp and transfers: `/cngnonramp`, `/cngnofframp`, `/withdrawasset`, `/fintechtransfer`, `/initiateofframp`
- Transaction status: `/cngnonrampstatus`, `/cngnofframpstatus`, `/getofframpstatus`, `/manualstatusrecovery`
- Histories: `/deposits`, `/payouts`, `/transactions`
- Swap: `/swaptrigger`, `/swap`, `/swapstatus`
- FX orderbook: `/fx/limit-order`, `/fx/limit-order/update`, `/fx/limit-order/delete`, `/fx/limit-orders`, `/fx/orderbook`, `/fx/orderbook/stats`, `/fx/orderbook-token`
- FX trading: `/fx/quote`, `/fx/trade`, `/fx/market-order`, `/fx/trades`, `/fx/trades/status`
- FX controls: `/fx/settings`, `/fx/mpc/register`, `/fx/auto-signing/enable`, `/fx/auto-signing/disable`, `/fx/auto-signing/status`, `/fx/auto-signing/stats`, `/fx/auto-signing/threshold`
- Fees (all amounts in kobo): `/managefees`, `/getfees`, `/getaccumulatedfees`, `/feewithdrawal`, `/verifywithdrawal`, `/getwithdrawalhistory`, `/fees/strails/preview`
- Webhook + security management: `/setwebhook`, `/togglewebhookstatus`, `/getwebhook`, `/manageipallowlist`, `/regenerateapikey`, `/createsandboxapikey`, `/storepublickey`, `/getplatformpublickey`, `/getaeskey`, `/updateonrampasset`, `/autosigning/config`
- Fiat payout bank management: `/getbankscode`, `/addbankaccount`, `/getbankaccounts`, `/updatebankaccount`, `/deletebankaccount`, `/listbankaccounts`

## Quick example — onramp a user (most common integration)

```bash
# 1. Onboard user with BVN. `bvn` is the ONLY field this endpoint accepts —
#    Strails issues the user id and returns it as `userHash`.
curl -X POST https://api.strails.io/v1/onboarduser \
  -H "x-api-key: $STRAILS_API_KEY" -H "Content-Type: application/json" \
  -d '{"bvn": "12345678901"}'

# 2. Poll onboarding with the requestId from step 1 (not the user id)
curl -X POST https://api.strails.io/v1/onboardstatus \
  -H "x-api-key: $STRAILS_API_KEY" -H "Content-Type: application/json" \
  -d '{"requestId": "<from step 1>"}'

# 3. Fund their wallet (₦5,000 — plain Naira, auto-swap to USDC)
curl -X POST https://api.strails.io/v1/cngnonramp \
  -H "x-api-key: $STRAILS_API_KEY" -H "Content-Type: application/json" \
  -d '{"userId": "<from step 2>", "amount": 5000, "assetSwap": "USDC", "autoSwap": true}'

# 4. Give the user the bank account to pay into
curl -X POST https://api.strails.io/v1/getvirtualaccount \
  -H "x-api-key: $STRAILS_API_KEY" -H "Content-Type: application/json" \
  -d '{"requestId": "<from step 3>"}'
```

Virtual accounts expire 30 minutes after creation — always surface `expiresAt`,
and show the user `totalAmountWithFee`, not `baseAmount`.

## Webhooks — always verify signatures

```
X-Strails-Signature: HMAC-SHA256(webhook_secret, timestamp + "." + raw_body)
X-Strails-Timestamp: ISO 8601
X-Webhook-ID:        unique per delivery attempt — dedupe on this
```

Hash the **raw** body — parsing and re-serializing changes the digest. Reject
anything older than 5 minutes and any signature that doesn't match (timing-safe
compare, guarded against length-mismatch throws). Return `200 OK` immediately,
then process asynchronously — slow handlers cause Strails to retry and
duplicate events. Full verification code (Node.js + Python) is in
`references/authentication.md`; the event list is in `references/webhook-events.md`.

**FX trades emit no webhook events.** None of the 22 events cover the orderbook
or trading flow — poll `GET /fx/trades/status?tradeId=...` instead.
