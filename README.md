# strails-skill

Claude Code skill bundle for working with the [Strails](https://api.strails.io)
platform — stablecoin orchestration for cNGN, USDC and USDT.

This repository is both a **Claude Code plugin** and its own single-plugin
marketplace, so it installs with two commands and no manual file copying.

## Layout

| Path | Purpose |
|---|---|
| `skills/strails-api/` | **Source of truth.** The unpacked skill: `SKILL.md` plus 14 reference files. Edit here. |
| `.claude-plugin/plugin.json` | Plugin manifest — name, version, author. |
| `.claude-plugin/marketplace.json` | Marketplace manifest, so the repo can be added as a plugin source directly. |
| `strails-api.skill` | Built bundle (a zip of the skill) for claude.ai uploads. Generated — don't edit by hand. |
| `build.py` | Validates the repo and packages the bundle. |

The skill is generated from the public documentation at
[github.com/wrappedcbdc/strails-docs](https://github.com/wrappedcbdc/strails-docs).
When the docs change, update `skills/strails-api/` and rebuild.

## Build

```bash
python3 build.py           # validate, then write strails-api.skill
python3 build.py --check   # validate only
```

Validation fails the build if `SKILL.md` has no `name`/`description`
frontmatter, if `name` doesn't match the directory, if a `references/` file is
orphaned or missing, if the plugin and marketplace manifests disagree, or if
any API URL omits the required `/v1` prefix.

Check the plugin manifests with Claude Code's own validator too:

```bash
claude plugin validate . --strict
```

## Releasing

Bump `version` in `.claude-plugin/plugin.json`, rebuild, then tag:

```bash
claude plugin tag .
```

That creates a `strails-api--v<version>` tag after checking that
`plugin.json` and the marketplace entry agree.

## Install

**Claude Code (recommended)** — add this repo as a marketplace, then install:

```bash
claude plugin marketplace add wrappedcbdc/strails-skill
claude plugin install strails-api@strails
```

Or from inside a session: `/plugin marketplace add wrappedcbdc/strails-skill`
then `/plugin install strails-api@strails`.

`--scope` controls where it lands: `user` (default, every project), `project`
(committed to the current repo for your team), or `local`.

```bash
claude plugin list                  # what's installed
claude plugin details strails-api   # components and token cost
claude plugin update strails-api    # pull a new version
claude plugin uninstall strails-api
```

**Manual** — copy the skill directly, no plugin machinery:

```bash
cp -r skills/strails-api ~/.claude/skills/   # available in every project
cp -r skills/strails-api .claude/skills/     # or scoped to one project
```

**claude.ai** — upload `strails-api.skill` in Settings → Capabilities → Skills.

## Contents

`SKILL.md` carries what is always relevant — base URLs, auth headers, the
response envelope, the four amount formats, and a capability map that routes a
request to the right endpoint family. Everything else is a reference file
loaded only when the task needs it:

`authentication` · `quickstart-and-flows` · `user-management` · `wallets` ·
`virtual-accounts` · `transactions` · `fx-trading` · `fees` ·
`management-and-security` · `webhook-events` · `payload-formats` ·
`status-codes-and-errors` · `testing-and-sandbox` · `going-live`

## Open questions

The upstream documentation contradicted itself on these points. The API
reference was taken as authoritative in each case, and the result is
internally consistent — but none of it has been checked against a running API.
Confirm before relying on them in production.

| Topic | Resolution taken |
|---|---|
| `/onboarduser` body | Takes `bvn` only. Strails issues the user id and returns it as `userHash`. Guides that also sent `userId`/`email`/`phoneNumber`/`firstName`/`lastName` were aligned to the API reference. |
| `sweepToOfframp` | `true` sweeps to the user's default Smart Wallet — it does not trigger a bank payout. |
| FX endpoint paths | `/fx/limit-order`, `/fx/limit-order/update`, `/fx/limit-order/delete`, `/fx/limit-orders`, `/fx/trades/status`, and `/fx/quote` as POST. The `/fx/orders*` and `/fx/trades/:tradeId` forms appeared only in a rate-limit table. |
| Fee amounts | Every Fee Management endpoint is denominated in kobo, including `/getaccumulatedfees`, whose units were previously undocumented. |
| `/getfintechwallet` | Returns `smartWallet` as an object plus `externalWallets[]` and `totalUsers` — not `mpcVault`/`managedWallet` addresses, and no balances. |
| FX webhooks | None exist. No event in the 22-event list covers trading; poll `/fx/trades/status`. |
| `/manualstatusrecovery` | Documented as POST. It has no reference page of its own — it appears only in troubleshooting guidance. |
