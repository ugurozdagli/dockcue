# Security

DockCue is a local utility, not a remote-access tool. No incoming TCP ports or
cloud services are required. The only application socket is the fixed loopback
G HUB connection documented in [PRIVACY.md](PRIVACY.md).

Please report reproducible security problems without including credentials,
serial numbers, raw USB captures, private logs, personal paths or identifying
screenshots. Prefer GitHub's private vulnerability-reporting option if enabled;
otherwise open a minimal issue requesting a private reporting channel without
posting exploit details or private data publicly.

Contributions that add network listeners, remote control, telemetry, credentials,
or unrestricted G HUB requests require explicit design review and are outside
the current purpose of this application. Do not disable OS security tools to run
a build; inspect the source and build it yourself if a binary is not trusted.
