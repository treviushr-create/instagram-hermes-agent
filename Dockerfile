# Variant image: this agent's persona + skills + tools, on top of Plow's
# Hermes base. See plow-pbc/plow-hermes-agent#building-a-variant-image.
#
# Pinned to base-51f83158a70a383f03a4d03dbd8b6ea102cf0361 — the same exact
# base+digest used by at least two other independent, working agents built
# for this same hackathon (each with the identical compose.yml env_file
# pattern this repo uses). Earlier pins (HEAD, and a different older sha)
# each failed differently — this is the one with multiple independent
# confirmations, not a guess.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-51f83158a70a383f03a4d03dbd8b6ea102cf0361@sha256:253d7ed3409effa7fa59113d93b4b79bb731d8264cdaf4cd60294924d0110a2e

# Identity: only what is specific to this agent. plow-init writes the home's
# SOUL.md on every boot as the base persona followed by this file.
COPY --chown=0:0 runtime/persona.md /opt/hermes/plow-seed/persona.md
RUN chmod 0644 /opt/hermes/plow-seed/persona.md

# Both copies, as the base image does: one seeds an empty home, the other is
# what later image updates reach. A skill the owner deletes stays deleted.
COPY --chown=10000:10000 skills/ /var/lib/hermes/skills/
COPY --chown=10000:10000 skills/ /opt/hermes/skills/

COPY LICENSE NOTICE /usr/share/doc/instagram-hermes-agent/

# This agent's own tools, beside the base's plow_chat plugin.
COPY plugins/instagram_tools/ /opt/hermes/plugins/instagram_tools/
RUN find /opt/hermes/plugins/instagram_tools -type d -exec chmod 0755 {} + \
 && find /opt/hermes/plugins/instagram_tools -type f -exec chmod 0644 {} +

# Usage reporter: fetched at build from the commit vendor/client.pin names,
# checked against the hash beside it. Root-owned under /opt/plow so a turn
# cannot rewrite what the supervisor runs unattended.
COPY vendor/client.pin /opt/plow/agent-index-client.pin
RUN set -eu; \
    sha="$(sed -n 's/^sha=//p' /opt/plow/agent-index-client.pin)"; \
    want="$(sed -n 's/^sha256=//p' /opt/plow/agent-index-client.pin)"; \
    path="$(sed -n 's/^path=//p' /opt/plow/agent-index-client.pin)"; \
    curl -fsS --max-time 60 -o /opt/plow/agent-index-client.py \
      "https://raw.githubusercontent.com/plow-pbc/agent-index-client/${sha}/${path}"; \
    got="$(sha256sum /opt/plow/agent-index-client.py | cut -d' ' -f1)"; \
    [ "$got" = "$want" ] || { echo "agent-index client is $got, pin says $want" >&2; exit 1; }; \
    chmod 0644 /opt/plow/agent-index-client.py

# What the supervisor runs is root-owned under /opt/plow, never the home
# copy: everything under $HERMES_HOME belongs to the agent, so scheduling
# that copy would run whatever a turn last wrote there, holding the relay
# credential. Same reasoning as one-thing-hermes-agent's register_cron.py.
COPY --chmod=0644 scripts/register_cron.py /opt/plow/instagram-cron/register_cron.py

COPY image/s6-overlay/ /etc/s6-overlay/
