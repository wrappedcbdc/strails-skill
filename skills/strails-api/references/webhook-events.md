# Webhook Events — Complete Reference (22 events)

For HMAC signature verification, see `authentication.md`.

## Common envelope (every event)

```json
{
  "eventId": "uuid",
  "eventType": "user.onboarded",
  "timestamp": "ISO 8601",
  "requestId": "originating request id",
  "fintechId": "your fintech id",
  "version": "1.0.0",
  "userId": "present when user-scoped, omitted for fintech-level events",
  "payload": { /* event-specific, see below */ }
}
```

## HTTP headers on every delivery

| Header | Description |
|---|---|
| `X-Strails-Signature` | HMAC-SHA256 hex digest over `timestamp + "." + raw_body` |
| `X-Strails-Timestamp` | ISO 8601 send time |
| `X-Webhook-ID` | Unique per delivery attempt — use to dedupe retries |
| `X-Strails-Event` | Event type name, matches `eventType` |

## Retry behavior

Any non-2xx response or timeout triggers exponential-backoff retry.
Acknowledge with `200 OK` immediately and process async. Dedupe using
`X-Webhook-ID` since retries can deliver the same event more than once.

---

## User & Onboarding

**`user.onboarded`** — user completes onboarding.
Key fields: `firstName`, `lastName`, `onboardedAt`.

---

## Virtual Account & Payment

**`virtual.account.created`** — reserved/checkout virtual account created.
Key fields: `vaId`, `accountNumber`, `bankName`, `accountName`, `createdAt`.

**`payments.confirmed`** — inbound payment to a virtual account confirmed by
gateway. Key fields: `txRef`, `reference`, `amount`, `currency`, `status`,
`confirmedAt`, `metadata.vaId`, `metadata.provider`, `metadata.walletAddress`.

**`fintech.virtual_account.deposit.received`** — deposit landed on the
**fintech's permanent** virtual account. Key fields: `depositId`,
`virtualAccount.accountNumber`, `deposit.amount`, `deposit.reference`,
`depositor.name`, `depositor.bankName`, `metadata.provider`.

**`fintech.user.deposit.received`** — deposit landed on a **user's**
permanent virtual account, before minting. First event in the user deposit
flow. Key fields: `depositId`, `virtualAccount.accountNumber`,
`deposit.amount`, `deposit.reference`, `depositor.name`,
`depositor.bankCode`, `metadata.provider`.

**`fintech.user.deposit.funding.completed`** — user deposit fully processed,
cNGN sent to their HSM Smart Wallet. Final success event. Key fields:
`depositId`, `amount`, `currency`, `transactionReference`,
`smartWalletAddress`, `transactionHash`, `depositor`, `bvnVerified`,
`completedAt`.

**`fintech.user.deposit.refunded`** — deposit auto-refunded due to BVN name
mismatch. Key fields: `depositId`, `amount`, `refundReference`,
`refundReason`, `depositor`, `bvnVerification.isMatch`,
`bvnVerification.confidenceScore`, `bvnVerification.rejectionReasons`,
`refundedAt`.

---

## Wallet Funding

**`wallet.funding.completed`** — cNGN minting complete, credited to user's
smart wallet after confirmed payment. Key fields: `walletAddress`, `amount`,
`transactionHash`, `completedAt`.

---

## Swap

**`swap.completed`** — token swap from a user's smart wallet succeeded. Key
fields: `walletAddress`, `sellToken`, `buyToken`, `amountIn`, `amountOut`,
`swapTxHash`, `transferTxHash`, `completedAt`,
`swapMetrics.executionTime`/`.gasUsed`/`.slippage`.

**`swap.failed`** — swap failed. Key fields: `walletAddress`, `sellToken`,
`buyToken`, `amountIn`, `failedAt`, `error.code`, `error.message`,
`retryable`, `metadata.attemptNumber`.

---

## Asset Transfer

**`fintech.asset.transfer.completed`** — fintech Smart Wallet → external
wallet transfer succeeded. Key fields: `smartWalletAddress`,
`destinationAddress`, `destinationLabel`, `amount`, `ticker`,
`transactionHash`, `blockNumber`, `gasUsed`, `commitmentsSafeguarded`,
`completedAt`.

**`fintech.asset.transfer.failed`** — fintech transfer failed (e.g.
insufficient balance after FX commitments). Key fields: `error`, `failedAt`.

**`fintech.user.asset.transfer.completed`** — user's smart wallet → external
wallet transfer succeeded. Key fields: `smartWalletAddress`,
`destinationAddress`, `amount`, `ticker`, `network`, `transactionHash`,
`blockNumber`, `gasUsed`, `completedAt`.

**`fintech.user.asset.transfer.failed`** — user transfer failed. Key fields:
`smartWalletAddress`, `destinationAddress`, `amount`, `ticker`, `network`,
`error`, `failedAt`.

---

## Offramp

**`vault.return.transfer.confirmed`** — cNGN sent from user's smart wallet
to the Strails vault (step 1 of offramp). Key fields: `transferId`,
`vaultReturnId`, `amount`, `tokenAddress`, `transactionHash`, `confirmedAt`,
`blockNumber`.

**`vault.return.payout.completed`** — fiat payout to user's bank confirmed,
offramp flow complete. Key fields: `payoutId`, `vaultReturnId`, `amount`,
`recipientAccountNumber`, `recipientBankCode`, `transactionReference`,
`completedAt`.

**`vault.return.payout.failed`** — fiat payout failed. Check `retryable`.
Key fields: `payoutId`, `vaultReturnId`, `amount`, `recipientAccountNumber`,
`recipientBankCode`, `failedAt`, `error.message`, `error.code`, `retryable`.

**`fintech.offramp.initiated`** — fintech-level offramp initiated. Key
fields: `amount`, `currency`, `status`, `bankAccount.accountNumber`,
`bankAccount.bankName`, `wallet.source`, `wallet.address`, `wallet.network`.

**`fintech.offramp.transfer.completed`** — on-chain cNGN transfer to Strails
settlement wallet confirmed; bank payout not yet started. Key fields:
`amount`, `currency`, `status`, `burnDetails.txHash`, `burnDetails.cNgnAmount`,
`burnDetails.blockNumber`, `burnDetails.confirmations`, `metadata.gasUsed`.

**`fintech.offramp.payout.initiated`** — bank payout submitted to provider.
Key fields: `amount`, `currency`, `status`, `bankAccount`,
`payoutDetails.reference`, `payoutDetails.provider`, `payoutDetails.status`.

**`fintech.offramp.completed`** — full offramp flow complete (burn confirmed
+ payout settled). Key fields: `amount`, `currency`, `status`, `bankAccount`,
`wallet`, `burnDetails.txHash`, `payoutDetails.reference`,
`payoutDetails.status`, `completedAt`, `metadata.processingTime`.

**`fintech.offramp.failed`** — offramp failed at any stage. Key fields:
`amount`, `currency`, `status`, `bankAccount`, `burnDetails`,
`error.message`, `error.code`, `metadata.retryable`, `metadata.attemptNumber`.

---

## Practical notes

- For user onramp funding, wait for `wallet.funding.completed` (and
  `swap.completed` if auto-swap is on) before crediting an in-app balance.
- For user permanent-account deposits, wait for
  `fintech.user.deposit.funding.completed`, not just `.received`.
- For fintech offramps, `fintech.offramp.completed` is the terminal success
  signal — earlier events (`.initiated`, `.transfer.completed`,
  `.payout.initiated`) are intermediate progress markers.
- **FX trades emit no webhook events.** None of the 22 events above cover the
  orderbook or trading flow — poll `GET /fx/trades/status?tradeId=...` until
  the trade reaches `completed`, `expired`, or `failed`.
