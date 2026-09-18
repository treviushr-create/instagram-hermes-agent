#!/usr/bin/env python3
"""Keep the periodic Instagram check registered and aimed at the owner's
chat, at boot. Same pattern as plow-pbc/one-thing-hermes-agent's
register_cron.py -- `hermes cron` keeps jobs in
/var/lib/hermes/cron/jobs.json and nothing replays them on a fresh home, so
the supervisor makes sure the one job exists on every boot, and retargets it
if the home outlived a re-mint (the delivery channel changed but the job
didn't).

Never read "could not tell what is registered" as "nothing is": that
duplicates the job. Only a missing jobs.json means empty; anything
unreadable raises.
"""
import json
import os
import subprocess
import sys

HERMES = "/opt/hermes/bin/hermes"
JOBS_FILE = "/var/lib/hermes/cron/jobs.json"
NAME = "instagram-monitor"
SCHEDULE = "*/15 * * * *"
PROMPT = (
    "Run your proactive Instagram check now, per the "
    "'Verificação proativa' section of your instagram-social-selling skill. "
    "If there is nothing worth telling the owner right now, your entire "
    "response must be exactly NO_REPLY."
)


def registered(jobs_path=JOBS_FILE):
    """The instagram-monitor job as hermes persisted it, or None when there is none."""
    try:
        with open(jobs_path) as f:
            jobs = json.load(f)["jobs"]
    except FileNotFoundError:
        return None
    return next((job for job in jobs if job["name"] == NAME), None)


def delivery_target(home_channel):
    if not (home_channel or "").strip():
        raise SystemExit("instagram-monitor: PLOW_HOME_CHANNEL is blank; refusing a cron that delivers nowhere")
    return f"plow_chat:{home_channel.strip()}"


def main(home_channel, jobs_path=JOBS_FILE, run=subprocess.run):
    deliver = delivery_target(home_channel)
    job = registered(jobs_path)
    if job is None:
        return run([HERMES, "cron", "create", SCHEDULE, PROMPT, "--name", NAME,
                    "--skill", "instagram-social-selling", "--deliver", deliver]).returncode
    if job["deliver"] == deliver:
        print(f"instagram-monitor: already registered for {deliver}")
        return 0
    return run([HERMES, "cron", "edit", job["id"], "--deliver", deliver]).returncode


if __name__ == "__main__":
    sys.exit(main(os.environ.get("PLOW_HOME_CHANNEL", "")))
