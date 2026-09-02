# strails-skill

A Claude Code skill for the [Strails](https://api.strails.io) API: NGN onramp
and offramp, multi-chain wallets, the P2P FX orderbook, virtual accounts, fees
and webhooks, for cNGN, USDC and USDT.

Install it and Claude writes Strails calls against the real endpoint contracts
instead of guessing. It knows `/cngnofframp` takes Naira while
`/initiateofframp` takes the smallest token unit, that webhook signatures cover
`timestamp + "." + body`, and that FX trades are polled rather than pushed.

The repo is also a Claude Code plugin and its own marketplace, so installing
takes two commands.

## Install

### Claude Code

```bash
claude plugin marketplace add wrappedcbdc/strails-skill
claude plugin install strails-api@strails
```

The same thing works inside a session: `/plugin marketplace add
wrappedcbdc/strails-skill`, then `/plugin install strails-api@strails`.
Restart Claude Code afterwards and the skill picks itself up whenever you
mention Strails, cNGN, `api.strails.io`, or paste a Strails endpoint.

It installs for your user account by default, so it works in every project.
Use `--scope project` to commit it to the repo you're in and share it with the
team, or `--scope local` to keep it to one checkout.

Day to day:

```bash
claude plugin list                  # what's installed
claude plugin details strails-api   # components and token cost
claude plugin update strails-api    # pull a new version
claude plugin uninstall strails-api
```

### Without the plugin system

Copy the skill into wherever Claude Code looks for skills:

```bash
cp -r skills/strails-api ~/.claude/skills/   # every project
cp -r skills/strails-api .claude/skills/     # just this one
```

### claude.ai

Upload `strails-api.skill` under Settings > Capabilities > Skills.

## What's in it

`SKILL.md` holds what matters on every call: base URLs, auth headers, the
response envelope, the four amount formats, and a map that points a request at
the right endpoint family. It's deliberately small, roughly 250 tokens sitting
in a session until something triggers it.

The other fourteen files live in `skills/strails-api/references/` and load only
when a task actually needs them:

`authentication`, `quickstart-and-flows`, `user-management`, `wallets`,
`virtual-accounts`, `transactions`, `fx-trading`, `fees`,
`management-and-security`, `webhook-events`, `payload-formats`,
`status-codes-and-errors`, `testing-and-sandbox`, `going-live`.

## Layout

| Path | Purpose |
|---|---|
| `skills/strails-api/` | The source. `SKILL.md` plus 14 reference files. Edit here. |
| `.claude-plugin/plugin.json` | Plugin manifest: name, version, author. |
| `.claude-plugin/marketplace.json` | Marketplace manifest, so the repo works as a plugin source on its own. |
| `strails-api.skill` | Zipped bundle for claude.ai uploads. Generated, so don't edit it by hand. |
| `build.py` | Checks the repo, then packages the bundle. |

Content comes from the public docs at
[github.com/wrappedcbdc/strails-docs](https://github.com/wrappedcbdc/strails-docs).
When those change, edit `skills/strails-api/` and rebuild.

## Building

```bash
python3 build.py           # check, then write strails-api.skill
python3 build.py --check   # check only
```

The build stops if `SKILL.md` is missing its `name` or `description`
frontmatter, if `name` doesn't match the directory it sits in, if a reference
file is orphaned or missing, if the plugin and marketplace manifests disagree,
or if an example URL leaves off the `/v1` prefix.

Claude Code has its own validator, worth running too:

```bash
claude plugin validate . --strict
```

## Releasing

Bump `version` in `.claude-plugin/plugin.json`, rebuild, then tag:

```bash
claude plugin tag .
```

That writes a `strails-api--v<version>` tag once it has confirmed
`plugin.json` and the marketplace entry agree.

## Open questions

The upstream docs contradicted themselves on the points below. In each case the
API reference won, and the result is at least self-consistent, but none of it
has been tried against a live API. Check these before you lean on them in
production.

| Topic | What we went with |
|---|---|
| `/onboarduser` body | Takes `bvn` and nothing else. Strails issues the user id and hands it back as `userHash`. Guides that also sent `userId`, `email`, `phoneNumber`, `firstName` or `lastName` were brought in line with the API reference. |
| `sweepToOfframp` | `true` sweeps to the user's default Smart Wallet. It does not trigger a bank payout. |
| FX endpoint paths | `/fx/limit-order`, `/fx/limit-order/update`, `/fx/limit-order/delete`, `/fx/limit-orders`, `/fx/trades/status`, and `/fx/quote` as a POST. The `/fx/orders*` and `/fx/trades/:tradeId` spellings turned up only in a rate-limit table. |
| Fee amounts | Every Fee Management endpoint is in kobo, `/getaccumulatedfees` included, though its units were never written down. |
| `/getfintechwallet` | Returns `smartWallet` as an object, plus `externalWallets[]` and `totalUsers`. No `mpcVault` or `managedWallet` addresses, and no balances. |
| FX webhooks | There aren't any. Nothing in the 22 events covers trading, so poll `/fx/trades/status`. |
| `/manualstatusrecovery` | Documented as a POST. It has no reference page of its own and shows up only in troubleshooting advice. |
