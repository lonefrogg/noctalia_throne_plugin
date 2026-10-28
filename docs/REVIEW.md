# Review and validation

Initially prepared on 2026-10-25; publication guide updated on 2026-10-26. This review was performed with AI assistance; it is not an independent security audit. The public package is version 2.1.1.

## Changes made for a reusable public package

- Replaced the personal installer/embedded-code layout with readable standalone Luau entries and a bundled, non-UI Python helper. No dependency on a separately installed `throne-menu` remains.
- Made the Throne endpoint, API key filename, thronectl executable and polling interval plugin settings. There is no personal home path, fixed profile selection or routing choice in the package. The key filename defaults to empty, requiring configuration.
- Excluded the original environment's keys, profile/subscription data, routes, screenshots, logs, installed Polkit rules and Git identity/history. Test names and CLI data are synthetic. The included cover is explicitly illustrative.
- Retained the scrolling fix: both the script root and scroll node receive their height through `flexGrow = 1`, leaving fixed controls outside the list. Profile IDs, rather than display names, identify actions and retained rows.
- Changed metric alignment to the documented `end` value and moved UI messages to nested English translation objects. The manifest, README, settings, source catalog and IPC examples agree on entry IDs and dependencies.
- Prevented CLI stderr from entering UI errors. The helper passes the key filename to thronectl and does not read or print the key value. Commands use argument arrays; names and settings are never interpolated into a shell.
- Validate IDs, JSON shape, status fields and finite metric values before passing them to the UI. Sorting compares numeric speeds; measured, untested and failed profiles remain distinct.
- Serialize explicit actions with a private per-user lock. Reject busy actions and failed TUN activation; do not silently start a proxy-only connection. Do not modify profiles, routes or permission rules.
- Reject stale poll/action callbacks after an action or a settings change. Keep one service for all panel/widget instances and suppress overlapping polls. Right click closes without toggling the VPN.
- Configured the public owner lonefrogg, removed the account-name setup script, and retained repository checks, backend tests, a mock-host test and a minimal GitHub Actions workflow. No runtime downloads or additional UI runtime were introduced.

## Automated validation

The bundled suite contains 17 unittest cases: backend unit tests, synthetic thronectl process tests and one mock-host case covering all three native entry scripts. The mock-host case exercises settings changes, stale callbacks, actions, icon state, search, pointer callbacks and the scroll constraint contract. It requires liblua5.4; CI installs that development-only dependency.

The public plugin was checked with the current `noctalia-dev/community-plugins` validator, including its manifest/README checks and thumbnail dimensions. The manifest, catalog, widget target and README examples are checked for the fixed public namespace. Passing the repository checker does not certify the upstream plugin API.

The scrolling approach was separately exercised against Noctalia v5.3.0's actual C++ Flex and ScrollView code in a headless harness, with rendering/input dependencies stubbed: 108 combinations of list length, panel height, scale and error-card presence. The harness checked clipping, retained offsets, wheel/touchpad handlers and final-row bounds. It demonstrated the earlier unconstrained-height failure and the corrected allocation. That external investigation is not included in the distributable repository and is not a full Noctalia test.

The privacy review checked the proposed release files for personal paths, the original environment's known identifying strings, private keys and profile/subscription URLs. This is a targeted review, not a guarantee that an automated scan can recognize every possible secret.

## Documentation update in 2.1.1

The English and Russian READMEs now include version-pinned downloads, checksum verification, a hidden API-key prompt with private file permissions, API checks, manual core privileges, ZIP/Git installation, widget setup and updates. The public namespace is fixed to lonefrogg. The old author-configuration script and its references were removed. A scoped optional DNS rule is documented but is not installed or executed by the plugin.

Download asset names, archive layout, GUI key-copy behavior and privilege requirements were checked against pinned upstream sources. Documentation examples were checked for Bash/Python syntax, the real CLI archive/checksums, key-file creation and rule scope. No live desktop or administrator setup was executed here.

## Still required before a catalog submission

- The public owner is already configured as lonefrogg; publish the intended repository with that identity.
- Test this public configurable package in a real Noctalia/Wayland session, including long lists, the final row, display scaling, settings changes and unavailable/permission-denied Throne. Noctalia itself was not available for an end-to-end test here.
- Replace the illustrative cover with a sanitized screenshot through the official thumbnail generator, and attach actual screenshots/video to the PR.
- Read the current community rules and PR template. Confirm eligibility with maintainers under their generated-code rule. A disclosure does not make the mandatory “not generated” attestation true; keep a PR Draft while that issue or real-session testing remains unresolved.
- Review the MIT license and publish only material you have the right to distribute. No claim of affiliation with upstream projects is made.

See [PUBLISHING.md](PUBLISHING.md) for the exact publication steps and [PR_DRAFT.md](PR_DRAFT.md) for supporting text. Nothing has been pushed to GitHub or submitted to Noctalia by this preparation.
