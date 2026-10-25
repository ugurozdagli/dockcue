# Contributing

Use a fresh Windows Python 3.11+ environment and the pinned requirements. Run
`python -m unittest discover -s tests -v` before submitting changes. Keep protocol
and state logic in `dockcue/core.py` testable without real hardware.

Describe the headset model, firmware version and reproduction steps. Device
compatibility claims must be backed by real hardware tests. Do not submit local
configuration, private diagnostics, raw reports containing serials, personal
paths, credentials, or developer-specific startup commands.

Microphone audio must never be captured. The runtime must remain local-only;
avoid adding telemetry, update checks or remote-control servers. English is the
fallback language; keep Turkish and English translation keys in sync.

AI-assisted contributions are welcome but must be understood, reviewed and
tested by the contributor. Generated text is not evidence of hardware support.
