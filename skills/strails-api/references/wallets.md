# Wallets — API & Wallet Types

Strails fintechs operate three wallet types:

| Wallet | Holds | Control |
|---|---|---|
| **Smart Wallet** | cNGN, USDC, USDT | Fintech- or Strails-controlled (EIP-1167 contract) |
| **Multi-Chain / Managed Wallet** | cNGN, USDC, USDT | Strails-controlled, HSM-backed |
| **MPC Vault** | USDC, USDT | Fintech-controlled via threshold (MPC) signing |

## Wallet Management API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/getfintechwallet` | GET | Your Smart Wallet + all registered External Wallets |
| `/addexternalwallet` | POST | Register a new external wallet |
| `/updateexternalwalletstatus` | PUT | Activate/deactivate an external wallet |
| `/removeexternalwallet` | DELETE | Remove an external wallet |
| `/listuserwallets` | POST | All wallets + balances for one end-user |
| `/migrateuserwallets` | POST | Provision default wallets for legacy users |
| `/balance/multi` | GET | Fintech Smart Wallet balance across EVM networks |
| `/balance/address` | POST | Token balance for any arbitrary EVM address |
| `/balance/user/:userId` | GET | End-user's balance across all their wallets |

### GET /getfintechwallet

Returns `fintechId`, `fintechName`, `smartWallet` (an **object**: address,
owner, deployed, createdAt, saltVersion, deploymentTxHash),
`externalWallets[]` (address, label, blockchain, type, status, isDefault,
purpose), and `totalUsers`.

It does **not** return MPC Vault or Managed Wallet addresses, and it returns
no balances. MPC token wallets come from `GET /fx/settings`
(`tokenWallets`); per-user Managed Wallets from `POST /listuserwallets`;
balances from `/balance/multi`.

### POST /addexternalwallet

```json
{
  "address": "0xAbCd...", "blockchain": "base", "type": "hot",
  "label": "Hot Wallet - Operations", "purpose": "Daily operations",
  "isDefault": true,
  "metadata": { "custodian": "Internal", "location": "AWS KMS", "backupExists": true }
}
```
`type` ∈ `hot` \| `cold` \| `custodial` \| `other`. Must whitelist an address
here **before** calling `/fintechtransfer` to it.

### PUT /updateexternalwalletstatus

```json
{ "address": "0x...", "status": "inactive" }
```

### DELETE /removeexternalwallet

```json
{ "address": "0x..." }
```

### POST /listuserwallets

```json
{ "userId": "user_uniqueID" }
```
Returns `wallets[]`: each has `walletAddress`, `status`, `blockchain`
(base/bantu/solana), `balances` per token. Note that on this endpoint
`status` carries the **wallet type** — `smart_wallet` or `multi_chain` — not
an active/inactive state. Every user gets a primary EVM Smart Wallet on Base
plus multi-chain wallets on Bantu and Solana.

### POST /migrateuserwallets

```json
{ "userId": ["userId_abc123", "userId_def456"], "force": true }
```
For users created before automated wallet provisioning. Ensure funds are out
of legacy wallets first — migration may issue new addresses.

### Balance endpoints

- `GET /balance/multi?token=CNGN&networks=base,eth,bsc` — fintech's own
  Smart Wallet, aggregated + per-network, flags `bridgingRequired` if funds
  are scattered cross-chain.
- `POST /balance/address` — `{"address": "0x...", "token": "CNGN", "networks": ["base","eth"]}`
  for any arbitrary address.
- `GET /balance/user/:userId?token=CNGN` — end-user's balance across their
  wallets.

All balance responses include per-network `error` fields when an RPC call
fails for that network (doesn't fail the whole request).

---

## Smart Wallet (EIP-1167 minimal proxy)

Contract-based wallet deployed via a `WalletFactory`, owner-controlled — no
bundlers, no ERC-4337, no paymasters. ~90% cheaper to deploy than a full
contract via the minimal-proxy (Clones) pattern. Deterministic addresses
(derived from a salt), predictable before deployment.

Key functions: `owner`, `nonce` (replay protection), `initialize(address)`,
`execute(address to, uint256 value, bytes data)` (only callable by owner),
`changeOwner(address)`.

### Withdraw tokens by calling execute()

```javascript
const { ethers } = require("ethers");
const provider = new ethers.JsonRpcProvider("https://mainnet.base.org");
const signer = new ethers.Wallet("YOUR_PRIVATE_KEY", provider);

const smartWallet = new ethers.Contract(
  "0xYourSmartWalletAddress",
  ["function execute(address to, uint256 value, bytes data) returns (bytes)"],
  signer
);

const transferData = new ethers.Interface(["function transfer(address to, uint256 amount)"])
  .encodeFunctionData("transfer", ["0xRecipientAddress", ethers.parseUnits("1000", 6)]); // cNGN = 6 decimals

const tx = await smartWallet.execute("0xTokenContractAddress", 0, transferData);
await tx.wait();
```

(viem equivalent uses `encodeFunctionData` + `writeContract` with the same
`execute(to, value, data)` ABI — see docs if needed.) Owner EOA pays gas in
native token (ETH on Base/Ethereum). Active FX orders lock a portion of
balance as collateral — available balance = total minus locked.

---

## Multi-Chain Wallet (Managed Wallet) — HSM-backed

Strails-controlled, AWS KMS-backed (HSM), supports ECDSA + EdDSA, SLIP-0044
HD derivation. This is the execution layer for all API-initiated ops
(transfers, swaps, bridging) — private keys never leave the HSM, Strails
pays all gas fees.

Supported networks: Base (primary), Ethereum, BNB Chain (USDT only), Solana,
Bantu (cNGN only).

Used by `/withdrawasset`, `/fintechtransfer`, `/swap`, `/swaptrigger` (see
`transactions.md`). For cross-chain, pass the `network` param on
`/withdrawasset`.

---

## MPC Vault — threshold-signed stablecoin custody for FX

Holds USDC/USDT for the FX orderbook's stablecoin leg (cNGN leg is always the
Smart Wallet). Multi-Party Computation signing — no single exposed private
key. Fintech-controlled.

**Settlement rule:** whoever sends stablecoins from their MPC Vault signs.

| Order side | Stablecoin sender | Signer |
|---|---|---|
| BUY | Maker's MPC Vault | Maker |
| SELL | Taker's MPC Vault | Taker |

| Asset leg | Custody source |
|---|---|
| cNGN | Smart Wallet |
| USDC/USDT | MPC Vault |

### Setup flow

1. Complete MPCVault API user setup at mpcvault.com to get
   `mpcVaultApiKey`, `callbackClientSignerPublicKey`,
   `mpcClientSignerPrivateKey`.
2. `POST /fx/mpc/register` — see `fx-trading.md` for full body/response.
   Goes to `pending` until Strails admin approves.
3. `POST /fx/auto-signing/enable` then `POST /fx/auto-signing/threshold`
   (USD value below which trades auto-sign; above requires manual approval
   in MPCVault).
4. `GET /fx/settings` → confirm `mpcConfigStatus: "active"` and
   `autoSigning.vmStatus: "running"`. Copy `natExternalIp` and add it to
   **both** the API User IP Whitelist and API Client Signer IP Whitelist in
   your MPCVault account — auto-signing won't work otherwise. If
   auto-signing fails, Strails falls back to manual approval automatically.

Liquidity: BUY orders (you're maker) need cNGN in Smart Wallet; SELL orders
(you're taker) need USDC/USDT in MPC Vault. Active orders lock balance as
collateral — available balance = total minus locked.
