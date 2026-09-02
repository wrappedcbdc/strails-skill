# Production Launch Checklist

Work through every section before switching from staging
(`beta.stablesrail.io`) to production (`api.strails.io`).

## 1. Credentials & Environment
- [ ] Production API key received via secure onboarding.
- [ ] Base URL switched from `https://beta.stablesrail.io/v1/` to
      `https://api.strails.io/v1/` everywhere.
- [ ] Key stored in a secret manager (AWS Secrets Manager, GCP Secret
      Manager, Vault) — not in source control, `.env` committed to git, or
      CI/CD logs.
- [ ] If the key was ever shared/emailed/exposed, it's been regenerated
      (`GET /regenerateapikey`).

## 2. IP Allowlisting
- [ ] Public IPs of all production servers/load balancers gathered.
- [ ] Added via `/manageipallowlist` (or sent to support).
- [ ] Test request made **from production**, not laptop/staging, to confirm.

## 3. Payload Encryption
- [ ] Production X25519 keypair generated, separate from staging.
- [ ] Production public key registered via `POST /storepublickey`.
- [ ] Production Strails public key received and stored securely.
- [ ] Encrypt/decrypt round-trip verified end to end.
- [ ] Production services use production keys, not staging keys.

See `authentication.md` for the encryption flow.

## 4. Webhooks
- [ ] Production HTTPS webhook URL registered via `/setwebhook`, publicly
      reachable with valid TLS.
- [ ] Handler returns `200 OK` immediately; processes logic async.
- [ ] Strong random webhook secret (≥32 bytes entropy) in secret manager.
- [ ] Handler verifies `X-Strails-Signature` (HMAC-SHA256) on every request.
- [ ] Handler rejects `X-Strails-Timestamp` older than 5 minutes (replay
      protection).
- [ ] Handler confirmed to process all critical event types you depend on
      (`user.onboarded`, `wallet.funding.completed`, `swap.completed`,
      `vault.return.payout.completed`, `fintech.offramp.completed`).
      FX trades emit no webhooks — poll `/fx/trades/status`.

See `webhook-events.md` and `authentication.md`.

## 5. Wallets & Liquidity
- [ ] `/getfintechwallet` called against production and the Smart Wallet
      address confirmed; MPC Vault token wallets confirmed via
      `/fx/settings`.
- [ ] MPC Vault registered and auto-signing configured for FX trading.
- [ ] `natExternalIp` from `/fx/settings` retrieved and whitelisted in
      MPCVault.
- [ ] Production wallets hold sufficient cNGN and USDC/USDT liquidity for
      expected launch volume.
- [ ] Understood that active FX orders lock corresponding wallet balances —
      accounted for in liquidity planning.

## 6. Fees & Bank Accounts
- [ ] Current fee configuration reviewed via `/getfees`; matches product
      pricing.
- [ ] Production fee structure set via `/managefees`.
- [ ] Production settlement bank account added + verified via
      `/addbankaccount`.
- [ ] Small-value offramp (₦100–₦500) processed end to end in production to
      confirm correct settlement.

## 7. End-to-End Testing (run once against production before opening to users)

- [ ] User onboarding: BVN submission → verification → `user.onboarded`
      webhook received.
- [ ] Virtual account creation: onramp initiation → account details
      returned → correctly expires after 30 min if unused.
- [ ] Wallet funding (onramp): NGN deposit → cNGN minted →
      `wallet.funding.completed` webhook → balance visible.
- [ ] Auto-swap: onramp with `autoSwap: true` → cNGN minted → USDC/USDT
      credited → `swap.completed` webhook.
- [ ] Withdrawal (offramp): offramp initiated → bank transfer processed →
      `vault.return.payout.completed` (user) or `fintech.offramp.completed`
      (fintech) webhook → correct bank amount.
- [ ] FX trading: limit order posted → quote fetched → trade executed →
      `/fx/trades/status` polled through to `completed` → both wallet
      balances updated correctly.

## 8. Monitoring & Support
- [ ] Logging in place for every Strails request/response (`requestId`,
      HTTP status, response time).
- [ ] Alerting on elevated API error rates or missing critical webhooks.
- [ ] Runbook for `429 Too Many Requests` (exponential backoff + jitter;
      how to request a higher limit).
- [ ] Know how to reach support: support@strails.io.

If any item is unchecked or unclear, don't switch production traffic yet —
contact support@strails.io first.
