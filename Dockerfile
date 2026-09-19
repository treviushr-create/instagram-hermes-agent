# Variant image: this agent's persona + skills + tools, on top of Plow's
# Hermes base. See plow-pbc/plow-hermes-agent#building-a-variant-image.
#
# Pinned to the current base, which ships the Agent Index usage reporter
# itself (s6 service agent-index); this repo no longer carries a copy.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-ef0019372ff8bca593611b31ebd2e08f9f1458ff@sha256:a8a2f97ad78b8192d80a984dce81d3bf5a9a883d18cb7b677704913a09b56aee

# Identity: only what is specific to this agent. plow-init writes the home's
# SOUL.md on every boot as the base persona followed by this file.
COPY --chown=0:0 runtime/persona.md /opt/hermes/plow-seed/persona.md
RUN chmod 0644 /opt/hermes/plow-seed/persona.md

# Both copies, as the base image does: one seeds an empty home, the other is
# what later image updates reach. A skill the owner deletes stays deleted.
COPY --chown=10000:10000 skills/ /var/lib/hermes/skills/
COPY --chown=10000:10000 skills/ /opt/hermes/skills/

COPY LICENSE /usr/share/doc/instagram-hermes-agent/

# This agent's own tools, beside the base's plow_chat plugin.
COPY plugins/instagram_tools/ /opt/hermes/plugins/instagram_tools/
RUN find /opt/hermes/plugins/instagram_tools -type d -exec chmod 0755 {} + \
 && find /opt/hermes/plugins/instagram_tools -type f -exec chmod 0644 {} +

# What the supervisor runs is root-owned under /opt/plow, never the home
# copy: everything under $HERMES_HOME belongs to the agent, so scheduling
# that copy would run whatever a turn last wrote there, holding the relay
# credential. Same reasoning as one-thing-hermes-agent's register_cron.py.
COPY scripts/register_cron.py /opt/plow/instagram-cron/register_cron.py
RUN chmod 0644 /opt/plow/instagram-cron/register_cron.py

COPY image/s6-overlay/ /etc/s6-overlay/
