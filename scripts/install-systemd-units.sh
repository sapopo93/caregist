#!/usr/bin/env bash
# install-systemd-units.sh
# Installs CareGist systemd timer units, replacing the bare-cron schedule in
# /etc/cron.d/caregist.  The cron file is left in place; disable it there once
# the timers are confirmed healthy (see below).
#
# Run as a user with sudo access on the EC2 instance:
#   bash scripts/install-systemd-units.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
UNIT_DIR="${REPO_ROOT}/deploy/systemd"
SYSTEMD_DIR="/etc/systemd/system"

echo "==> Copying unit files from ${UNIT_DIR} to ${SYSTEMD_DIR}"
sudo cp "${UNIT_DIR}"/*.service "${SYSTEMD_DIR}/"
sudo cp "${UNIT_DIR}"/*.timer   "${SYSTEMD_DIR}/"

echo "==> Setting permissions"
sudo chmod 644 "${SYSTEMD_DIR}"/caregist-*.{service,timer}

echo "==> Reloading systemd daemon"
sudo systemctl daemon-reload

echo "==> Enabling and starting all CareGist timers"
sudo systemctl enable --now caregist-incremental-update.timer
sudo systemctl enable --now caregist-feed-cycle.timer
sudo systemctl enable --now caregist-flush-email-queue.timer
sudo systemctl enable --now caregist-pipeline-watchdog.timer
sudo systemctl enable --now caregist-daily-alerts.timer
sudo systemctl enable --now caregist-weekly-movers.timer

echo ""
echo "==> Timer status:"
systemctl list-timers 'caregist-*' --no-pager

echo ""
echo "==> All done.  Tail logs with:"
echo "    journalctl -u caregist-incremental-update -f"
echo "    journalctl -u caregist-feed-cycle -f"
echo "    journalctl -u caregist-flush-email-queue -f"
echo "    journalctl -u caregist-pipeline-watchdog -f"
echo "    journalctl -u caregist-daily-alerts -f"
echo "    journalctl -u caregist-weekly-movers -f"
echo ""
echo "==> Once the timers are confirmed healthy, you can disable the cron entries:"
echo "    sudo mv /etc/cron.d/caregist /etc/cron.d/caregist.disabled"
