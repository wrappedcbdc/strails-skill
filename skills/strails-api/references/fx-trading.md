# FX Orderbook & Trading

P2P FX between fintechs: cNGN ↔ USDC/USDT. cNGN leg settles from the Smart
Wallet; USDC/USDT leg settles from the MPC Vault (see `wallets.md` for the
signing model).

**All FX amounts are human-readable decimal strings — never wei.** That
covers `price`, `spread`, `minAmount`, `maxAmount`, `availableLiquidity`,
`cngnAmount`, and `tokenAmount`. `"price": "1600.50"` means 1,600.50 cNGN per
token and `"minAmount": "1000"` means 1,000 cNGN.

**FX emits no webhook events** — none of the 22 events in `webhook-events.md`
cover trading. Poll `GET /fx/trades/status?tradeId=...` for settlement.

## FX Settings & Auto-Signing

| Endpoint | Method | Description |
|---|---|---|
| `/fx/mpc/register` | POST | Register MPC vault config |
| `/fx/settings` | GET | Full FX config incl. MPC + wallets |
| `/fx/auto-signing/enable` | POST | Enable auto-signing |
| `/fx/auto-signing/disable` | POST | Disable auto-signing |
| `/fx/auto-signing/threshold` | POST | Set USD auto-sign threshold |
| `/fx/auto-signing/status` | GET | Config + today's stats |
| `/fx/auto-signing/stats` | GET | Rolling-window stats |

### POST /fx/mpc/register

```json
{
  "mpcVaultApiKey": "your-mpc-vault-api-key",
  "callbackClientSignerPublicKey": "ssh-ed25519 AAAA...",
  "mpcClientSignerPrivateKey": "-----BEGIN OPENSSH PRIVATE KEY-----\n<b64>\n-----END OPENSSH PRIVATE KEY-----",
  "vaultId": "your-mpc-vault-id",
  "tokenWallets": { "USDT": "0x...", "USDC": "0x..." },
  "notificationEmails": ["admin@yourcompany.com"]
}
```
`mpcClientSignerPrivateKey` newlines must be literal `\n` escapes, not real
line breaks. Sensitive fields are masked in responses. Returns
`status: "pending"` — cNGN wallet auto-assigned to your Smart Wallet; awaits
Strails admin approval.

### GET /fx/settings

Returns `mpcConfigStatus` (`active`/`pending`/`inactive`), `autoSigning`
(`available`, `enabled`, `threshold`, `vmStatus`, `natExternalIp` — whitelist
this IP in MPCVault), `tokenWallets`, `notificationEmails`.

### Enable/disable/threshold

```
POST /fx/auto-signing/enable   {}
POST /fx/auto-signing/disable  {}
POST /fx/auto-signing/threshold  { "usdThreshold": "10000" }
```
Trades at/below threshold auto-sign; above requires manual MPCVault approval.
If auto-signing fails, Strails falls back to manual approval automatically.

### GET /fx/auto-signing/status | /fx/auto-signing/stats?days=7

Status returns `todayStats` (totalAutoSigned, totalUsdAutoSigned,
fallbackCount, successRate, avgExecutionTimeMs). Stats returns `daily[]` +
`totals` over the requested window (default 7 days).

---

## Orderbook Management (create liquidity)

| Endpoint | Method | Description |
|---|---|---|
| `/fx/limit-order` | POST | Create a limit order |
| `/fx/limit-order/update` | PUT | Update price/spread/amounts/status |
| `/fx/limit-order/delete` | DELETE | Permanently delete an order |
| `/fx/limit-orders` | GET | List your own orders |
| `/fx/orderbook` | GET | Public orderbook for a pair |
| `/fx/orderbook/stats` | GET | Aggregated stats for a pair |
| `/fx/orderbook-token` | GET | Firebase token for real-time orderbook |

### POST /fx/limit-order

```json
{ "pair": "CNGN-USDC", "side": "buy", "price": "1600.50", "spread": 0.5, "minAmount": "1000", "maxAmount": "100000" }
```
`pair` ∈ `CNGN-USDT` \| `CNGN-USDC`. `side`: `buy` = buy tokens with cNGN
(need cNGN liquidity), `sell` = sell tokens for cNGN (need USDC/USDT
liquidity). `spread` min 0.1%. `minAmount`/`maxAmount` in cNGN.
`availableLiquidity` in the response is queried live from your wallet —
informational only, re-validated at match time.

### PUT /fx/limit-order/update

```json
{ "orderId": "...", "price": "1605.00", "spread": 0.6, "minAmount": "2000", "maxAmount": "150000", "status": "active" }
```
At least one field required; `status` ∈ `active` \| `paused`. Can't update a
deleted order.

### DELETE /fx/limit-order/delete

```json
{ "orderId": "..." }
```
Permanent. Use `status: "paused"` on update instead if you may reactivate.

### GET /fx/limit-orders?pair=&status=&limit=

`status` ∈ `active` \| `paused` \| `deleted`.

### GET /fx/orderbook?pair=CNGN-USDC&limit=20

Returns `buyOrders[]` / `sellOrders[]` with price, spread, min/maxAmount,
availableLiquidity, status.

### GET /fx/orderbook/stats?pair=CNGN-USDC

Returns `totalActiveOrders`, `buyOrderCount`, `sellOrderCount`,
`totalBuyLiquidity`, `totalSellLiquidity`, `bestBidPrice`, `bestAskPrice`,
`spreadPercentage`.

### GET /fx/orderbook-token

Firebase custom token (`signInWithCustomToken`) for live orderbook
subscriptions, `expiresIn` seconds, `tradingPairs[]`, `firebaseConfig`.

### Order status lifecycle

`active` ↔ `paused` (via update) → `deleted` (via delete, one-way).

---

## Trading (execute trades)

| Endpoint | Method | Description |
|---|---|---|
| `/fx/quote` | POST | Price quote matched to orderbook liquidity |
| `/fx/trade` | POST | Execute (3 modes — see below) |
| `/fx/market-order` | POST | Immediate execution at best price |
| `/fx/trades/status` | GET | Single trade status |
| `/fx/trades` | GET | List trades (filterable, cursor-paginated) |

### POST /fx/quote

```json
{ "pair": "CNGN-USDC", "side": "sell", "cngnAmount": "50000" }
```
`cngnAmount` human-readable decimal, min 1,000 cNGN. Returns `quoteId`
(5-min validity), `usdcAmount`/`usdtAmount` (dynamic field name), `price`,
`matchedOrders[]`, `expiresAt`.

### POST /fx/trade — 3 modes

**Mode 1 (recommended) — against a quote:**
```json
{ "quoteId": "quote_...", "idempotencyKey": "trade_20260501_001" }
```

**Mode 2 — direct at best market price:**
```json
{ "pair": "CNGN-USDC", "side": "sell", "cngnAmount": "50000", "destinationWalletAddress": "0x..." }
```

**Mode 3 — targeted at a specific LP's order:**
```json
{ "orderId": "order_abc123", "cngnAmount": "25000" }
```

Response: `tradeId`, `status: "pending"`, `lockId` (escrow lock id),
`expiresAt` (5-min lock window), `strailsFeePercentage`. Ensure cNGN is in
your Fintech Smart Wallet before calling (address via `/getfintechwallet`,
balance via `/balance/multi`). There is no `userId` on this endpoint — trades
execute as the fintech that owns the API key.

### POST /fx/market-order

```json
{ "pair": "CNGN-USDC", "side": "sell", "cngnAmount": "50000", "destinationWalletAddress": "0x...", "idempotencyKey": "market_20260501_001" }
```
Skips the quote step; fill price may differ slightly from displayed
orderbook stats if liquidity shifts between request and match.

### GET /fx/trades/status?tradeId=...

Returns `status`, `fintechNetAmount` (after fees), `priceLockExpiresAt`,
`errorMessage`/`failedAt` (null unless failed).

### GET /fx/trades?pair=&side=&status=&limit=&startAfter=

Cursor-paginated with `startAfter` = last `tradeId` from previous page.

## Trade status lifecycle

```
pending → locked → signing → settling → completed
              ↓        ↓          ↓
           expired   expired    failed
```
A trade can only expire from `locked`/`signing` (5-min window) — once
`settling`, it completes or fails, never expires. On expire/fail, escrowed
cNGN auto-releases back to your wallet.

## Common trading errors

| Code | Error | Meaning |
|---|---|---|
| 01 | `VALIDATION_ERROR` | Bad request fields |
| 01 | `INVALID_QUOTE` | quoteId expired or doesn't exist |
| 02 | `NO_LIQUIDITY` | Insufficient orderbook liquidity |
| 02 | `NOT_FOUND` | Trade/order not found or no access |
| 03 | `AUTHENTICATION_FAILED` / `IP_BLOCKED` | Key invalid / IP not allowlisted |
| 04 | `RATE_LIMIT_EXCEEDED` | Back off and retry |
| 05 | `INTERNAL_ERROR` | Contact support if persistent |
