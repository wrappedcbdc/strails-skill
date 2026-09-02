# User Management API

Onboarding users with BVN verification, checking status, retrieving details,
and managing account state.

| Endpoint | Method | Description |
|---|---|---|
| `/onboarduser` | POST | Onboard a new user with BVN verification |
| `/onboardstatus` | POST | Check onboarding status |
| `/getuserdetails` | POST | Retrieve user details incl. wallets & virtual accounts |
| `/manageuserstatus` | POST | Activate/deactivate a user |
| `/listfintechusers` | POST | Paginated list of all your users |

## POST /onboarduser

```json
// Request
{ "bvn": "12345678901" }
```

`bvn` is the **only** field this endpoint accepts. Identity details are
resolved from the BVN record, and the user identifier is issued by Strails
and returned as `userHash` — do not supply your own `userId`.

```json
// Response
{
  "status": "Success", "response_code": "00",
  "message": "User registration initiated",
  "data": {
    "requestId": "7898f29e-...",
    "status": "processing",
    "userHash": "user_uniqueID",
    "estimatedCompletionTime": "2-5 minutes"
  }
}
```

Errors: invalid BVN format (must be 11 digits), user already exists, or BVN
verification failed against identity provider (`response_code: "05"`).

## POST /onboardstatus

```json
{ "requestId": "7898f29e-..." }
```
→ `data.status`: `"processing"` | `"completed"` | `"failed"`. 404
(`response_code: "02"`) if requestId not found.

## POST /getuserdetails

```json
{ "userId": "user_uniqueID" }
```

Returns `personalDetails` (firstName/middleName/lastName), `walletDetails`
(evmWallet, bantuWallet, solanaWallet), and `virtualAccounts[]` (the user's
permanent NGN account — see `virtual-accounts.md`). 404 if user not found or
unverified.

## POST /manageuserstatus

```json
{ "userId": "user_uniqueID", "active": false, "reason": "Account suspended by customer request" }
```

`reason` is **required** when deactivating. Returns `active` + `changedAt`.

## POST /listfintechusers

```json
{ "limit": 20, "offset": 0, "status": "all", "orderBy": "verifiedAt", "orderDirection": "desc" }
```

| Field | Default | Notes |
|---|---|---|
| `limit` | 20 | 1-100 |
| `offset` | 0 | |
| `status` | `"all"` | `"active"` \| `"inactive"` \| `"all"` |
| `orderBy` | `"verifiedAt"` | or `"createdAt"` |
| `orderDirection` | `"desc"` | `"asc"` \| `"desc"` |

Response includes `data.users[]` (each with wallets, virtualAccount summary)
and a standard `pagination` object (see `payload-formats.md`).

## BVN validation notes

- BVN must be exactly 11 numeric digits — whitespace/hyphens fail validation
  immediately (`VALIDATION_ERROR`).
- The BVN must not already be registered to another Strails user.
- If the identity provider can't resolve the BVN or is unreachable, the call
  returns `response_code: "05"`.
- A `failed` onboarding record cannot be retried — submit a fresh
  `/onboarduser` call.

The onboarding webhook event is `user.onboarded` (see `webhook-events.md`).
`"type": "user_registration"` inside the `/onboardstatus` response body is a
data field, not an event name.
