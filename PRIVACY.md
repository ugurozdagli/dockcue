# Privacy and local control

DockCue has no account system, analytics, telemetry, advertising, automatic
upload, update service, remote command handler, or inbound network listener.
It does not record microphone audio or inspect files outside its own portable
data directory. It does not access browser cookies, GitHub credentials, or a
developer's computer. Nothing in the application is tied to a developer's PC.

## Local operations

- Reads A50 X status/mix HID reports from the local USB base. Enumeration paths
  remain in memory and are never written to a log or uploaded.
- Plays generated microphone notification tones through Windows' default output.
- Sends the Windows play/pause media key on the selected mix direction.
- Connects as a client only to the fixed loopback address `127.0.0.1:9010` to read
  the local G HUB device list and restore the headset's Game/Voice mix. All
  requests use a narrow path/verb/value allowlist. Environment proxies are bypassed.
- Uses same-user, local-session Windows events for single-instance show/quit.
- Writes preferences and a bounded local log in the application's `data/` folder.
- Changes only its own Windows Run/StartupApproved entries when the user opts in
  or opts out of starting with Windows.

Logs contain fixed application event names, version, language choice, uptime,
and sanitized error type / module basename / line number. They intentionally
omit raw reports, serial numbers, device paths, exception messages, tokens,
account names, audio, and personal filesystem paths. A local session marker
detects an unclean previous shutdown; that can include an OS-forced shutdown,
not only an application crash.

## Publishing and support

Source control excludes `data/`, settings, logs, credentials, build directories,
and binaries. Release packaging includes only the executable, public documents,
and dependency licenses. Public binaries are built in GitHub Actions. No runtime
data is uploaded by the workflow. Review any file before choosing to share it in
a public support issue; DockCue never submits it automatically.

Dependency installation and GitHub website usage are separate from the running
application. These services have their own network activity and policies.
