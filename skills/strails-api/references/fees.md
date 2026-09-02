# Fee Management API

Configure onramp/offramp fee structures, monitor accumulated fees, and
withdraw them.

| Endpoint | Method | Description |
|---|---|---|
| `/getwithdrawalhistory` | GET | Paginated fee withdrawal history |
| `/feewithdrawal` | POST | Request a fee withdrawal to a bank account |
| `/getaccumulatedfees` | GET | Accumulated fee summary + available balance |
| `/managefees` | PUT | Configure onramp/offramp fee % + caps + toggles |
| `/getfees` | GET | Current fee configuration |
| `/fees/strails/preview` | POST | Preview the Strails platform fee for an amount |
| `/verifywithdrawal` | POST | Check a withdrawal's status |

## GET /getwithdrawalhistory?limit=20&status=completed

`status` ∈ `pending` \| `completed` \| `failed`. Each record: `withdrawalId`,
`amount` (kobo), `bankAccountNumber` (masked), `bankCode`, `accountName`,
`status`, `createdAt`, `processedAt`, `failureReason`.

## POST /feewithdrawal

```json
{
  "bankAccountNumber": "1234567890", "bankCode": "058", "accountName": "YOUR COMPANY NAME",
  "amount": 50000, "narration": "Fee withdrawal for August 2025",
  "metadata": { "reference": "FEE_WITHDRAWAL_AUG_2025", "notes": "Monthly fee withdrawal" }
}
```
`amount` is **kobo** (smallest NGN unit). Must not exceed available balance
or fall below the minimum threshold. Returns `withdrawalId`,
`status: "pending"`, `estimatedProcessingTime` ("1-3 business days"). Poll
via `/verifywithdrawal`.

## GET /getaccumulatedfees

```json
{
  "data": {
    "summary": {
      "totalAccumulatedFees": 125000, "onrampFees": 100000, "offrampFees": 25000,
      "collectedFees": 120000, "pendingFees": 5000, "transactionCount": 150,
      "pendingWithdrawals": 20000, "availableForWithdrawal": 100000
    },
    "details": { "currency": "NGN", "minimumWithdrawal": 1000, "maximumWithdrawal": 10000000 }
  }
}
```
**Every figure in this response is kobo**, like the rest of the fee API:
`availableForWithdrawal: 100000` means ₦1,000.00 and `minimumWithdrawal: 1000`
means ₦10.00. `availableForWithdrawal` = collected fees minus pending
withdrawals — check `/feewithdrawal` amounts against this, not against
`totalAccumulatedFees`.

## PUT /managefees

```json
{
  "onrampFee": { "percentageFee": 1.5, "capFee": 500, "enabled": true },
  "offrampFee": { "percentageFee": 2.0, "capFee": 1000, "enabled": true },
  "metadata": { "description": "Updated fee configuration for Q4", "lastUpdatedBy": "admin@yourfintech.com" }
}
```
Both `onrampFee`/`offrampFee` objects are optional (omit to leave unchanged),
but every field within an included object is required. `capFee` is in kobo;
`percentageFee` is a percent value (`1.5` = 1.5%), not a 0–1 decimal.
Response includes an `exampleCalculation` for sanity-checking.

## GET /getfees

Returns `hasConfiguration` (false = using platform defaults),
`feeConfiguration`, `timestamps`, `version`.

## POST /fees/strails/preview

```json
{ "amount": 150000, "transactionType": "offramp" }
```
`amount` in kobo. `transactionType` ∈ `onramp` \| `offramp`. This is the
**Strails platform fee**, separate from and applied on top of your
configured fintech fee. Response: `feePercentage`, `calculatedFee`,
`fixedFee`, `finalFee`, `wasCapped`, `appliedCap`, `tierUsed`,
`usedFintechOverride`. Use this to show users a transparent breakdown before
they confirm.

## POST /verifywithdrawal

```json
{ "transactionReference": "FTW_your_fintech_id_1725444600000" }
```
`transactionReference` = the `withdrawalId` from `/feewithdrawal`. Returns
`status`, `processedAt`, `failureReason` (null on success/pending).
