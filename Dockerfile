# Variant image: this agent's persona + skills + tools, on top of Plow's
# Hermes base. See plow-pbc/plow-hermes-agent#building-a-variant-image.
#
# TODO(diogo): replace <sha> with the current base-<sha> tag published by
# https://github.com/plow-pbc/plow-hermes-agent before the first build —
# pinning by digest or immutable base-<sha> tag is required, `latest` is not
# an option here.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-<sha>

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

COPY image/s6-overlay/ /etc/s6-overlay/
