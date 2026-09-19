# Instagram Social Selling

A [Hermes agent](https://github.com/plow-pbc/plow-hermes-agent) that helps an
Instagram seller never miss a lead in the Direct — it watches for new DMs and
comments, drafts a reply, and only sends after the owner approves it by text.

Built for the [Hermes Hackathon](https://luma.com/3uftu95w) (AI Worth Using ×
Plow). MIT licensed. Agent Index page:
[aiworthusing.com/agent-index/instagram-social-selling](https://aiworthusing.com/agent-index/instagram-social-selling).

## The loop

```
New DM / comment
      │
      ▼
instagram_fetch_signals ──► score it (hot / warm / cold)
      │                            │
      │                            ▼
      │                    instagram_qualify
      │                            │
      ▼                            ▼
              draft a reply, grounded only in what
              the owner has confirmed — never invented
                            │
                            ▼
              text the owner: "here's the draft, ok?"
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
          approved        edited       declined
              │             │             │
              └──────┬──────┘             ✕ (nothing sent)
                     ▼
           instagram_send_reply
        (official Meta Graph API)
```

**The one rule that doesn't bend:** nothing reaches a lead with wording the
owner hasn't seen, and nothing is ever posted publicly on the agent's own
initiative. No auto-send, no exceptions.

A second, separate loop watches the account's reputation instead of chasing
sales: `instagram_fetch_mentions` (someone tagged the account in their own
post) and `instagram_fetch_own_comments` (a comment on the account's own
posts) both feed `instagram_assess_reputation`, which triages tone —
`flag` (negative/accusatory, tell the owner now), `watch` (neutral, mention
later), `info` (positive, no urgency). This loop only ever *tells* the
owner something — it never replies or posts on its own. Useful for anyone
with a public-facing account who wants to know fast if something wrong is
being said about them, not just for selling.

## Status

| Piece | State |
|---|---|
| Persona + skills (`runtime/persona.md`, `skills/instagram-social-selling/`) | **Working** |
| Sales qualification (`instagram_qualify`) | **Working** — no external dependency, `python3 demo_local.py` to see it live |
| Reputation monitoring (`instagram_fetch_mentions`, `instagram_fetch_own_comments`, `instagram_assess_reputation`) | **Working** — tested against the real Graph API |
| Tool registration with Hermes (`register(ctx)` / `ctx.register_tool`) | **Working** — confirmed by the model calling tools directly and getting real answers back |
| Agent Index usage reporting | **Working** — https://aiworthusing.com/agent-index/instagram-social-selling |
| **Hosted on Plow's own cloud** (`plow-agents deploy <image> --line`, no `--local`) | **Working** — root cause of the earlier `provider_unreachable` found: the GHCR package silently reverts to *private* visibility when a same-named source repo gets created (bit another hackathon participant too). Fix: package Settings → Danger Zone → Change visibility → Public. Check this first if it recurs. |
| Instagram Graph API (all `instagram_*` tools) | **Working** — real Meta app, real dedicated Instagram Business account, real token, confirmed against `graph.instagram.com` |
| Running self-hosted (`docker compose up`) | **Working**, kept as the developer path — cloud is the primary deploy now |

## Architecture

```
instagram-hermes-agent/
├── Dockerfile                    variant image: base + persona + skills + tools
├── Dockerfile.dockerignore       allowlist for plow-agents' own credential scanner
├── compose.yml                   self-hosted run: docker compose up --build -d
├── .env.example                  INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_BUSINESS_ACCOUNT_ID
│
├── runtime/
│   └── persona.md                who the agent is, appended to the base persona at boot
│
├── skills/instagram-social-selling/
│   └── SKILL.md                  the loop above, in the agent's own words
│
├── plugins/instagram_tools/      the tools the model can actually call
│   ├── plugin.yaml                name/kind/provides_tools manifest
│   ├── __init__.py                Tool wrappers + register(ctx) — the real Hermes contract
│   ├── qualification.py           hot/warm/cold scoring (no external dependency)
│   ├── reputation.py              flag/watch/info triage for mentions/comments about you
│   ├── graph_api.py                the Instagram Graph API client (urllib, stdlib only)
│   ├── state.py                    JSON-file dedup so a re-poll doesn't resurface old signals
│   └── engine/
│       ├── domain.py               Signal / Qualification / ReputationAssessment / Draft
│       └── ports.py                the interfaces graph_api.py implements against
│
├── scripts/
│   └── onboard_customer.sh        mint a line + deploy a dedicated instance for one customer
│
├── docs/                          served by GitHub Pages
│   ├── index.html                  privacy policy (Meta app requirement)
│   └── como-funciona.html          plain-language explainer for non-technical shop owners
│
└── demo_local.py                  see instagram_qualify work with zero setup
```

**Why tools live *inside* `plugins/instagram_tools/`, not at the repo root:**
the Dockerfile only copies `plugins/instagram_tools/` into the image — a
top-level `engine/` would never reach the container. Learned this the hard
way; keeping it documented here so it doesn't regress.

**Why `qualification.py` is a handful of keyword checks, not a large guard
system:** every draft this feeds goes to the owner for approval before
anything sends (see the loop above). The human approval step is the safety
net — this function only decides how loudly to ask for the owner's
attention, not whether a message is safe to send.

## Who this is actually for, and how it scales

The setup below is real, but it's a *developer* path — clone a repo, run
Docker, read Graph API docs. That's the right path for another hackathon
participant or engineer. It is not a path a small shop owner will ever walk.

Most Instagram sellers who'd actually benefit from this — a clothing shop,
a home baker, a small studio — don't run a terminal and shouldn't have to.
The adoption model for that audience isn't "self-host it," it's the same
model every small business already uses for software it didn't build:
**someone sets it up for them.** [`docs/como-funciona.html`](docs/como-funciona.html)
is the plain-language page for that audience — no Docker, no tokens, no
jargon, just "give us access to your Instagram, we hand you back a phone
number."

Making that real for more than one customer needs a repeatable operational
step, not a repeat of six manual commands each time — that's what
[`scripts/onboard_customer.sh`](scripts/onboard_customer.sh) is: given a new
customer's Instagram credentials, it mints a Plow line and deploys their own
dedicated instance of this same image. No multi-tenancy inside the agent
itself (that's unneeded complexity for what's actually one image deployed
many times) — the same pattern already proven working for this repo's own
instance, just not done by hand anymore.

## Running it yourself

Everything below is self-hosted and free — no cloud costs, no CNPJ, no
Meta App Review needed to get real usage going.

### 1. Prerequisites

- Docker. On Apple Silicon without Docker Desktop, [Colima](https://github.com/abiosoft/colima)
  works with zero interactive setup:
  ```sh
  brew install colima && colima start
  brew install docker-compose
  mkdir -p ~/.docker/cli-plugins
  ln -sfn "$(brew --prefix)/opt/docker-compose/bin/docker-compose" ~/.docker/cli-plugins/docker-compose
  ```
- Python 3.11+ (for `plow-agents` and the usage-registration script).
- A phone that can receive an SMS.

### 2. Get a Plow line

```sh
git clone https://github.com/plow-pbc/plow-agents.git
export PATH="$PWD/plow-agents/bin:$PATH"
plow-agents login      # texts an activation code — copy/paste it, don't type it (autocorrect will mangle it)
plow-agents lines      # pick a free line, note its ln_xxx id
```

### 3. Clone this repo and mint a credential

```sh
git clone https://github.com/treviushr-create/instagram-hermes-agent.git
cd instagram-hermes-agent
plow-agents mint ln_xxx
```

### 4. Register on the Agent Index

```sh
curl -O https://raw.githubusercontent.com/plow-pbc/agent-index-client/f900ff144076f0a766584b6ec4d0993600779b16/standalone/agent_index_client.py
set -a; . ./plow-credentials; set +a
python3 agent_index_client.py --register --agent "<your-agent-id>" --name "<name>" --blurb "<one line>"
```
Set `AGENT_ID` in `compose.yml` to match what you registered.

### 5. Run it

```sh
docker compose up --build -d
docker compose logs -f
```
Wait for `plow-init: configured ... as cht_...`, then text your line's
number — any greeting works to open the first chat.

If the container exits with code 139 on first boot: that's QEMU emulating
the amd64 base image on Apple Silicon, not your setup. `docker compose up -d`
again — it reconnects to the same identity.

### 6. Meta setup

Fill in `.env` (copy from `.env.example`) with `INSTAGRAM_ACCESS_TOKEN` and
`INSTAGRAM_BUSINESS_ACCOUNT_ID` from your own Meta app — no CNPJ or App
Review required to get real usage going:

1. Instagram account → Settings → switch to **Business** or **Creator**.
2. Create a Facebook Page and connect it to that Instagram account.
3. [developers.facebook.com/apps](https://developers.facebook.com/apps) →
   Create app → **Other** → pick a use case that fits (Instagram-only use
   cases aren't always offered at creation — Facebook Login's variant works
   too, see [Instagram API with Facebook Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/get-started)).
4. Add your account as an **Instagram Tester** (App Roles) — skips the App
   Review queue entirely for your own real usage.
5. Use the **Graph API Explorer** with `pages_show_list`, `instagram_basic`,
   `instagram_manage_messages` to get a token, then:
   - `GET /me/accounts` → your Page ID
   - `GET /{page-id}?fields=instagram_business_account` → your
     `INSTAGRAM_BUSINESS_ACCOUNT_ID`
   - exchange for a long-lived Page token → `INSTAGRAM_ACCESS_TOKEN`
6. `docker compose up --build -d` again to pick up `.env`.

## License

MIT, see [LICENSE](LICENSE).
