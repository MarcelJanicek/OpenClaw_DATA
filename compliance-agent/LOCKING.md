# Cron locking (to prevent overlapping runs)

Because the GDPR builder runs on a schedule, we prevent overlap by using an atomic lock.

## Lock spec
- Lock path: `/root/.openclaw/workspace/compliance-agent/.gdpr-build.lock`
- Acquisition: create directory (atomic)
  - `mkdir /root/.openclaw/workspace/compliance-agent/.gdpr-build.lock`
- Release: remove directory
  - `rmdir /root/.openclaw/workspace/compliance-agent/.gdpr-build.lock`

## Behavior
- If lock exists: exit the run immediately with no changes.
- Always attempt to release lock on successful completion.
- If a run crashes, the lock may remain; manual recovery: remove the directory.
