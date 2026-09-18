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
owner hasn't seen. No auto-send, no exceptions.

## Status

| Piece | State |
|---|---|
| Persona + skill (`runtime/persona.md`, `skills/instagram-social-selling/`) | **Working** |
| Qualification (`instagram_qualify`) | **Working** — no external dependency, `python3 demo_local.py` to see it live |
| Tool registration with Hermes (`register(ctx)` / `ctx.register_tool`) | **Working** — confirmed by the model calling `instagram_fetch_signals` and getting a real answer back |
| Agent Index usage reporting | **Working** — reports every 5 min once the agent has real usage |
| Running self-hosted (`docker compose up`) | **Working** — connects to a real Plow phone line, replies over SMS/iMessage |
| Instagram Graph API (`instagram_fetch_signals` / `instagram_send_reply`) | **Blocked on credentials** — needs a Meta app + a connected Instagram Business/Creator account (see [Meta setup](#meta-setup) below); until then, both return a clear `{"ok": false, "error": ...}` instead of pretending to work |
| Hosted on Plow's own cloud (`plow-agents deploy <image> --line`, no `--local`) | **Not working yet** — fails with `failed(provider_unreachable)` even on the base image other hackathon agents deploy successfully with. Self-hosting via `docker compose` is the working path for now. |

## Architecture

```
instagram-hermes-agent/
├── Dockerfile                    variant image: base + persona + skills + tools
├── Dockerfile.dockerignore       allowlist for plow-agents' own credential scanner
├── compose.yml                   self-hosted run: docker compose up --build -d
├── .env.example                  INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_BUSINESS_ACCOUNT_ID
├── vendor/client.pin             pinned+checksummed Agent Index usage-reporter client
│
├── runtime/
│   └── persona.md                who the agent is, appended to the base persona at boot
│
├── skills/instagram-social-selling/
│   └── SKILL.md                  the loop above, in the agent's own words
│
├── image/s6-overlay/s6-rc.d/agent-index/
│   ├── run                       longrun: reports token usage to the Agent Index every 5 min
│   ├── type                      "longrun"
│   └── dependencies.d/plow-init  waits for identity before it starts
│
├── plugins/instagram_tools/      the tools the model can actually call
│   ├── plugin.yaml                name/kind/provides_tools manifest
│   ├── __init__.py                Tool wrappers + register(ctx) — the real Hermes contract
│   ├── qualification.py           hot/warm/cold scoring (no external dependency)
│   ├── graph_api.py                the Instagram Graph API client (urllib, stdlib only)
│   ├── state.py                    JSON-file dedup so a re-poll doesn't resurface old signals
│   └── engine/
│       ├── domain.py               Signal / Qualification / Draft — the shared vocabulary
│       └── ports.py                the interfaces graph_api.py implements against
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
