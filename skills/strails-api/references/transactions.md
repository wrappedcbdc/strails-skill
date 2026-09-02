# Transactions API — Onramp, Offramp, Swaps, Transfers

Every operation is asynchronous — returns a `requestId` immediately; poll the
matching status endpoint or use webhooks (`webhook-events.md`).

| Endpoint | Method | Description |
|---|---|---|
| `/cngnonramp` | POST | Fund a user wallet: NGN → cNGN (+ optional swap) |
| `/cngnofframp` | POST | User's cNGN → NGN, paid to their bank account |
| `/getfintechvirtualaccount` | GET | Fintech's persistent virtual account (see `virtual-accounts.md`) |
| `/initiateofframp` | POST | Fintech's own cNGN → NGN payout |
| `/withdrawasset` | POST | Withdraw a user's tokens to an external wallet |
| `/fintechtransfer` | POST | Withdraw fintech Smart Wallet tokens to a registered external wallet |
| `/cngnonrampstatus` | POST | Status of a user onramp |
| `/cngnofframpstatus` | POST | Status of a user offramp |
| `/getofframpstatus` | GET | Status of a fintech offramp |
| `/deposits` | GET | List deposits (filterable) |
| `/payouts` | GET | List payouts (filterable) |
| `/transactions` | GET | List all transactions (in + out) |
| `/swaptrigger` | POST | Async swap on any wallet address |
| `/swap` | POST | Swap on a user's default Smart Wallet |
| `/swapstatus` | GET | Status of a swap |

## POST /cngnonramp — amounts in plain **Naira**

```json
{
  "userId": "user_uniqueID", "amount": 500,
  "assetSwap": "USDC", "autoSwap": true, "sweepToOfframp": false,
  "destinationAssetSwap": "0xDestinationAddress"
}
```

| Field | Notes |
|---|---|
| `amount` | **Naira**, e.g. `500` = ₦500 |
| `assetSwap` | `USDC`/`USDT` — used only if `autoSwap: true` |
| `autoSwap` | swap funded cNGN into `assetSwap` |
| `sweepToOfframp` | route to user's default Smart Wallet after confirmation (ignores `destinationAssetSwap` when set) |
| `destinationAssetSwap` | alt destination wallet for swapped assets |
| `owner` | your EOA to own the generated Smart Wallet (Strails then cannot withdraw from it) |

autoSwap behavior matrix: see `quickstart-and-flows.md` Step 4 or
`virtual-accounts.md`.

Response: `requestId`, `walletAddress`, `feeBreakdown` (`baseAmount`,
`fintechFee`, `strailsFee`, `totalFee`, `totalAmount`). Get the payment
account via `/getvirtualaccount` (see `virtual-accounts.md`).

## POST /cngnofframp — amounts in plain **Naira**

```json
{ "userId": "user_uniqueID", "amount": 5000, "accountNumber": "0123456789", "bankCode": "058", "ticker": "CNGN" }
```

Response: `requestId`, `status: "payout_pending"`, `stage: "payout"`. Errors
include `Insufficient wallet balance` listing required vs. available across
networks.

## POST /initiateofframp (fintech-level) — amounts in **smallest unit**

```json
{ "amount": 1000000, "bankAccountId": "uuid-of-bank-account" }
```
`amount` is lowest-unit token (e.g. `1000000` = 1.00 cNGN, `1000000000` =
1,000.00 cNGN — NOT ₦1,000,000). Contrast `/cngnofframp`, which takes Naira.
Get `bankAccountId` from `/listbankaccounts` (`virtual-accounts.md`). Errors:
bank account not found, or insufficient Smart Wallet cNGN balance.

## POST /withdrawasset — user wallet → external wallet

```json
{
  "userId": "user_uniqueID", "internalWallet": "0xInternalWalletAddress",
  "destinationWallet": "0xExternalWalletAddress", "amount": 100,
  "ticker": "CNGN", "network": "base"
}
```
`amount` is **human-readable token units** (`100` = 100 cNGN) — unlike
`/fintechtransfer`, which takes the smallest unit. `network` ∈ `base` (default) \| `bsc`
\| `sol` \| `eth` \| `xbn` \| `asc` \| `arc` \| `lisk` — routes through a
bridge if non-base. Response includes `transactionHash`, `gasUsed`,
`feeBreakdown` (`requestedAmount`, `totalFee`, `netAmount`).

## POST /fintechtransfer — fintech Smart Wallet → registered external wallet

```json
{ "destinationAddress": "0xExternalRegisteredAddress", "amount": 5000000, "ticker": "CNGN", "note": "Withdrawal to cold storage" }
```
`amount` is the **smallest unit** (`5000000` = 5.0 cNGN) — unlike
`/withdrawasset`, which takes human-readable units. Destination must be
pre-registered via `/addexternalwallet` (`wallets.md`). Active orders/escrows
reduce available balance — response shows `commitmentsSafeguarded`
(`activeOrders`, `activeEscrows`, `totalCommitted`, `remainingBalance`).

## Status endpoints

- `POST /cngnonrampstatus` `{"walletAddress": "..."}` → `data.status`
  (`requested`→`pending`→`processing`→`funded`→`completed`, or `failed`; if
  autoSwap: →`swap_queued`→`swap_processing`→`completed`). Also returns
  `fxQuote` when a swap is pending.
- `POST /cngnofframpstatus` `{"requestId": "..."}` → includes
  `tokenTransfer` and `payout` sub-objects with their own status/hash.
- `GET /getofframpstatus?requestId=...` (fintech-level) → `transferDetails`,
  `payoutDetails`.

Full status value lists: `status-codes-and-errors.md`.

## List endpoints (deposits / payouts / transactions)

All support `limit` (default 20, max 100), `offset`, `status` filter
(`pending`/`processing`/`completed`/`failed`/`cancelled`), `startDate`/
`endDate` (ISO 8601), `userId`.

- `GET /deposits?type=fintech_deposit|user_onramp&status=...`
- `GET /payouts?type=fintech_offramp|user_offramp&status=...`
- `GET /transactions?direction=in|out&type=...&status=...` — combined view
  with a `summary` object (`totalDeposits`, `totalPayouts`, `depositVolume`,
  `payoutVolume`).

Each returns a standard `pagination`-style shape with `total`, `limit`,
`offset`, `hasMore`.

## Swaps

### POST /swaptrigger — async, any wallet address

```json
{ "walletAddress": "0xGeneratedWalletAddress", "sellToken": "CNGN", "buyToken": "USDC", "amount": 500, "slippage": 2 }
```
`buyToken` falls back to the wallet's configured `tokenBuy`; `amount` falls
back to the wallet's funded amount if omitted. `slippage` defaults to `5`.

### POST /swap — user's default Smart Wallet, primarily USDC→cNGN

```json
{
  "sellToken": "USDC", "buyToken": "CNGN", "amount": 100.50, "slippage": 2,
  "userId": "user_hash", "smartWalletAddress": "0xSmartWalletAddress",
  "destinationAssetSwap": "0xDestinationAddress"
}
```
`slippage` defaults to `2`. Response includes
`smartWalletExecutionDetails.validationSummary` (`balanceCheck`,
`allowanceCheck`).

### GET /swapstatus?requestId=...

Works for `requestId` from either `/swaptrigger` or `/swap`. Returns
`txHash`, `amountOut`, `executionRate`, `executionMethod`.
