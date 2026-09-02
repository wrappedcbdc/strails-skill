# Quickstart & End-to-End Integration Flow

Best starting point for a new integration. Steps build on each other in order.

Base URL for the walkthrough: `https://beta.stablesrail.io/v1/` (test/staging,
uses your normal API key). Prereqs: API key (support@strails.io), an HTTPS
webhook endpoint you control (use webhook.site or ngrok during dev), a test
BVN (11 digits).

## Step 1 — Test your connection

```bash
curl -X GET https://beta.stablesrail.io/v1/getfintechwallet \
  -H "x-api-key: YOUR_API_KEY" -H "Content-Type: application/json"
```

Success returns `data.smartWallet` (an object with `address`, `owner`,
`deployed`, ...), `externalWallets[]`, and `totalUsers`. If you see your
Smart Wallet address, your key and connectivity are good.

This endpoint returns wallet *configuration*, not balances, and not your MPC
Vault or Managed Wallet addresses:

- Balances → `GET /balance/multi?token=CNGN&networks=base,eth,bsc`
- MPC Vault token wallets → `GET /fx/settings` (`tokenWallets`)
- Per-user Managed Wallets → `POST /listuserwallets`

## Step 2 — Configure your webhook

```bash
curl -X POST https://beta.stablesrail.io/v1/setwebhook \
  -H "x-api-key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"webhookUrl": "https://yourapp.com/webhooks/strails", "secret": "<32+ random bytes>", "enabled": true, "events": ["all"]}'
```

Set up HMAC verification on your handler before proceeding — see
`authentication.md`. Hash the **raw** body over `timestamp + "." + body`,
compare timing-safely, dedupe on `X-Webhook-ID`, and always return `200 OK`
before doing any processing.

## Step 3 — Onboard your first user (BVN KYC)

```bash
curl -X POST https://beta.stablesrail.io/v1/onboarduser \
  -H "x-api-key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"bvn": "12345678901"}'
```

`bvn` is the only field this endpoint accepts — Strails resolves identity from
the BVN record and issues the user id itself, returned as `userHash`.

Poll `POST /onboardstatus` with `{"requestId": "..."}` (the `requestId` from
the call above, **not** a user id), or listen for the `user.onboarded`
webhook. Once `data.status` is `"completed"`, use the returned `userId` for
every subsequent call for that user. Full details: `user-management.md`.

## Step 4 — Fund a user wallet (onramp)

The `/cngnonramp` endpoint's behavior depends on three params:

| `autoSwap` | `assetSwap` | `sweepToOfframp` | Outcome |
|---|---|---|---|
| `false` | - | `false` | NGN deposited → cNGN minted, stays in the generated Smart Wallet |
| `false` | - | `true` | NGN → cNGN → swept to the user's default Smart Wallet |
| `true` | `"USDC"`/`"USDT"` | `false` | NGN → cNGN → auto-swapped to `assetSwap`, stays in the generated wallet |
| `true` | `"USDC"`/`"USDT"` | `true` | NGN → cNGN → swapped → swept to the user's default Smart Wallet |

`sweepToOfframp` sweeps to the user's **default Smart Wallet** — it does not
trigger a bank payout. When set, `destinationAssetSwap` is ignored.

```bash
curl -X POST https://beta.stablesrail.io/v1/cngnonramp \
  -H "x-api-key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"userId": "user_uniqueID", "amount": 5000, "assetSwap": "USDC", "autoSwap": true, "sweepToOfframp": false}'
```

`amount` is plain **Naira** — `5000` means ₦5,000.

Response includes `requestId`, `walletAddress`, and `feeBreakdown`. Then:

```bash
curl -X POST https://beta.stablesrail.io/v1/getvirtualaccount \
  -H "x-api-key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"requestId": "<from above>"}'
```

Returns the bank account number/name, `totalAmountWithFee`, and `expiresAt`
(**30 min window**). Show the user `totalAmountWithFee`, not `baseAmount` —
paying the base amount leaves the deposit short by the fee. Poll
`/cngnonrampstatus` or listen for `wallet.funding.completed` /
`swap.completed`. Full details: `transactions.md`, `virtual-accounts.md`.

## Step 5 — Process a withdrawal (offramp)

```bash
# /getbankscode is POST and takes no body
curl -X POST https://beta.stablesrail.io/v1/getbankscode \
  -H "x-api-key: YOUR_API_KEY" -H "Content-Type: application/json"

curl -X POST https://beta.stablesrail.io/v1/cngnofframp \
  -H "x-api-key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"userId": "user_uniqueID", "amount": 3000, "accountNumber": "0123456789", "bankCode": "058", "ticker": "CNGN"}'
```

`amount` is plain Naira here. (The fintech-level `/initiateofframp` takes the
smallest token unit instead — see `transactions.md`.)

Poll `/cngnofframpstatus`, or listen for `vault.return.transfer.confirmed`
(cNGN moved on-chain) then `vault.return.payout.completed` (bank payout
settled). Store every `requestId` for dispute resolution.

## Step 6 — Execute an FX trade (fintech liquidity)

All FX amounts are human-readable decimal strings — never wei.

```bash
# Create a limit order
curl -X POST https://beta.stablesrail.io/v1/fx/limit-order \
  -H "x-api-key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"pair": "CNGN-USDC", "side": "sell", "price": "1350.00", "spread": 0.5, "minAmount": "1000", "maxAmount": "100000"}'

# Get a quote (POST, 5-minute validity, min 1,000 cNGN)
curl -X POST https://beta.stablesrail.io/v1/fx/quote \
  -H "x-api-key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"pair": "CNGN-USDC", "side": "sell", "cngnAmount": "50000"}'

# Execute against the quote
curl -X POST https://beta.stablesrail.io/v1/fx/trade \
  -H "x-api-key: YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"quoteId": "quote_7f3a9d2c-...", "idempotencyKey": "trade_20260501_001"}'
```

Both sides settle via escrow with a 5-minute lock. **FX emits no webhook
events** — poll `GET /fx/trades/status?tradeId=...` until the trade reaches
`completed`, `expired`, or `failed`. Full details: `fx-trading.md`.

## Common integration patterns

- **Simple wallet funding**: onboard user → generate virtual account → user
  pays NGN → cNGN minted. Use when users just need a cNGN balance.
- **Funding with auto-swap**: `autoSwap: true` + `assetSwap: "USDC"` on the
  onramp call — no extra API calls needed after the deposit confirms.
- **Fintech liquidity management**: post a limit order → wait for match →
  confirm quote → execute. Escrow settles automatically.

## Testing tips

- Use small amounts (₦100–₦500) for onramp/offramp tests.
- Use webhook.site or `ngrok http 3000` to receive webhooks locally.
- Import the Strails Postman collection (see `testing-and-sandbox.md`) with
  `BASE_URL=https://beta.stablesrail.io/v1` and `API_KEY=<your API key>`.

## Quick troubleshooting

| Problem | Fix |
|---|---|
| `401` on every request | Header must be lowercase `x-api-key`; check the key is for the right environment |
| `404` on every request | Missing `/v1` — every path is mounted under it |
| IP not in allowlist | `POST /manageipallowlist` with `action: "add"`, or ask support |
| `429` | Exponential backoff; honour `data.retry_after`; contact support for higher limits |
| BVN verification fails | Confirm exactly 11 digits, and that the BVN isn't already registered |
| Stuck in `pending` >10 min | Query the status endpoint, then `POST /manualstatusrecovery` with `{"requestId": "..."}` |
| Webhooks not arriving | Must be HTTPS, return `200` within 10s, and be publicly reachable |
| FX trade webhook never arrives | There isn't one — poll `/fx/trades/status` |

Full status-code/error reference: `status-codes-and-errors.md`.
