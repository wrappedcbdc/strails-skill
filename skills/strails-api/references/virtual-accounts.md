# Virtual Accounts & Fiat Payout (Bank Accounts)

Virtual accounts are Nigerian bank account numbers Strails generates via
licensed payment providers. A bank transfer into one auto-mints the
equivalent cNGN — no manual conversion step.

## Account types

| Type | Lifetime | Purpose | cNGN destination |
|---|---|---|---|
| **Fintech Permanent** | Permanent | Fintech's own NGN funding channel | Fintech default wallet |
| **User Permanent** | Permanent | Dedicated per-user funding account | User's Strails HSM wallet |
| **Transaction Temporary** | 30 min | One-time collection for a specific amount | Generated Smart Wallet (optionally swept) |

### Fintech Permanent

```bash
curl -X GET https://api.strails.io/v1/getfintechvirtualaccount -H "x-api-key: YOUR_API_KEY"
```
Never expires; any amount; mints to your configured default wallet. Webhook:
`fintech.virtual_account.deposit.received`.

### User Permanent

Auto-created after `/onboarduser` BVN verification completes. Included in
`/getuserdetails` response under `virtualAccounts[]`. **BVN-linked** —
deposits must come from the user's own bank account; third-party/corporate
transfers auto-refund.

Webhooks (in order): `fintech.user.deposit.received` →
`fintech.user.deposit.funding.completed` (success) or
`fintech.user.deposit.refunded` (BVN name mismatch). Wait for
`.funding.completed` before crediting an in-app balance.

### Transaction Temporary

Created via `POST /cngnonramp` (see `transactions.md`). **Expires in 30
minutes** — always surface `expiresAt`. Deposit flow:

1. User transfers NGN to the virtual account.
2. Payment gateway confirms receipt → notifies Strails.
3. BVN validation runs — name mismatch triggers automatic refund.
4. cNGN minted to destination wallet.
5. Auto-swap executes if `autoSwap` was set.
6. Sweep executes if `sweepToOfframp` was set.
7. Webhook delivered (`funding.completed` or `.refunded`).

`autoSwap`/`sweepToOfframp` combinations:

| autoSwap | sweepToOfframp | Result |
|---|---|---|
| false | false | cNGN stays in generated Smart Wallet |
| false | true | cNGN swept to user's default wallet |
| true | false | cNGN → USDC/USDT, stays in generated wallet |
| true | true | cNGN → USDC/USDT → swept to user's default wallet |

## Virtual Accounts API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/getfintechvirtualaccount` | GET | Fintech's pooled virtual account(s) |
| `/getvirtualaccount` | POST | Specific deposit-request virtual account + fee breakdown |

### POST /getvirtualaccount

```json
{ "requestId": "a9f706ad-..." }
```

```json
// Response (key fields)
{
  "data": {
    "virtualAccount": {
      "accountNumber": "0123456789", "bankName": "Example Bank",
      "accountName": "Company Name/John Doe Smith",
      "amount": 528.84, "baseAmount": 520, "feeAmount": 8.84,
      "totalAmountWithFee": 528.84,
      "feeBreakdown": {
        "userRequestedAmount": 520, "fintechFeeAmount": 0, "fintechFeePercentage": 0,
        "strailsFeeAmount": 8.84, "strailsFeePercentage": 1.7,
        "totalFeeAmount": 8.84, "finalAmount": 528.84, "amountToWallet": 520
      }
    },
    "status": "created", "walletAddress": "0x..."
  }
}
```

**Always display `totalAmountWithFee`** to the user — not `baseAmount`. 30-min
expiry; expired accounts (`response_code: "01"`, error `"Virtual account
expired"`) cannot be reactivated — create a new deposit request.

## Fee structure on deposits

| Fee type | Typical range | Notes |
|---|---|---|
| Strails fee | 1-2% | Platform processing |
| Fintech fee | Configurable | via Fee Management API (`fees.md`) |
| Gateway fee | Varies | Charged by payment provider |

---

## Fiat Payout Management (bank accounts for offramp settlement)

At least one verified bank account is required before calling
`/initiateofframp` or `/cngnofframp`. Accounts are synchronously validated
against live bank records — you cannot add a mismatched name/number pair.

| Endpoint | Method | Description |
|---|---|---|
| `/getbankscode` | POST | List all supported Nigerian banks + NIBSS codes |
| `/addbankaccount` | POST | Add + verify a payout bank account |
| `/updatebankaccount` | PUT | Update label/default status |
| `/deletebankaccount` | DELETE | Remove an account (blocked while pending offramps exist) |
| `/getbankaccounts` | GET | Single account by ID |
| `/listbankaccounts` | GET | All accounts + current default |

### POST /addbankaccount

```json
{ "accountNumber": "1234567890", "bankCode": "044", "isDefault": false }
```
Response includes `accountId` (UUID — use in later calls),
`verifiedAccountName`, `isValidated`. Errors: account number not 10 digits,
or verification failed (name doesn't resolve at the bank).

### PUT /updatebankaccount

```json
{ "accountId": "uuid-account-id", "isDefault": true }
```
Cannot change account number/bank code — delete and re-add instead.

### DELETE /deletebankaccount

```
DELETE /deletebankaccount?accountId=uuid-account-id
```
Fails with `PENDING_TRANSACTIONS` if pending offramps reference this account.

### GET /getbankaccounts / /listbankaccounts

Returns `accountId`, `accountName`, `accountNumber`, `bankName`, `bankCode`,
`isDefault`, `isValidated`, `validationDetails` (`validatedAt`,
`accountNameMatch`). `/listbankaccounts` also returns `total` and
`defaultAccount` summary.
