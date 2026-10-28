# Add Throne VPN — supporting draft

Use this text within the repository's [current PR template](https://github.com/noctalia-dev/community-plugins/blob/main/.github/PULL_REQUEST_TEMPLATE.md). Keep the PR **Draft** until the required tests and attestations are true. Do not remove the template's marker or replace its required checkboxes with this supporting checklist.

Adds native Noctalia bar widget `bar`, attached panel `panel` and singleton service `backend` under `lonefrogg/throne-vpn`.

The plugin controls an already-running Throne via thronectl, lists profiles sorted by saved download speed, shows saved latency/upload/download and accumulated traffic, and changes the bar icon from Throne's reported connection/TUN state. Search and a constrained native scroll list keep large profile lists usable.

## AI disclosure

The implementation and documentation were produced with AI assistance. The maintainer is sharing and maintaining the project and does not claim to have manually authored the implementation. Please confirm that this submission is eligible under the repository's generated-code policy before reviewing it for merge.

## Runtime side effects

- Commands: `python3 <plugin-dir>/backend.py`, then `thronectl` with argument arrays. No shell interpolation or execution of profile names.
- Network: thronectl contacts the configured Throne API, loopback `127.0.0.1:9095` by default. No telemetry or other plugin network calls, remote code downloads, subscriptions or speed-test jobs.
- Reads: the helper tests existence of the configured API key file; thronectl reads the key. The plugin never embeds or prints its value. Snapshot data contains operational profile names/statistics.
- Writes: a private action-lock directory/file under XDG_RUNTIME_DIR, or a user cache fallback. Noctalia persists its normal settings.
- Actions: read-only `status`/`profiles` polls; explicit connection requests may run `tun on` before `connect`; explicit disconnection runs `disconnect`.
- No sudo, pkexec, Polkit install, route/profile/subscription edits or auto-connect at startup. Existing TUN privileges must be granted outside the plugin.
- Dependencies declared: `python3`, `thronectl`. The Python helper is bundled, readable and non-UI.

## Validation to fill in before opening the PR

- [ ] Confirm the directory name is still available (the namespace is already lonefrogg/throne-vpn).
- [ ] Maintainers confirmed how the generated-code rule applies to this project.
- [ ] Python tests and release checker pass; attach actual output and versions.
- [ ] Current upstream repository validator passes; attach actual output/version.
- [ ] Public package tested on a real Wayland desktop, including final-row scrolling, all pointer controls, settings changes, unavailable API and permission errors.
- [ ] Sanitized real thumbnail and screenshot/video attached; illustrative cover replaced.
- [ ] Personal data, API keys, subscription URLs and private configuration excluded.

The AI-assisted preparation used synthetic CLI responses and a mock host; the scrolling approach was separately checked against Noctalia 5.3.0's C++ Flex/ScrollView code with rendering/input dependencies stubbed. Those checks do not replace the unchecked real-session tasks above.

The current PR template requires a ready-for-review attestation that the code is not generated. Do not check that box merely because the source was reviewed or its AI origin was disclosed. Ask the maintainers how the requirement applies and leave it unchecked while unresolved.
