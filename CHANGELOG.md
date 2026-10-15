# Changelog

## 0.2.0 — 2026-10-15

- Add one process-wide `configure(visual_enhancement=True)` switch, off by default, for available H5 and native drawing enhancements across Android, iOS and HarmonyOS.
- Android: use DOM and native View drawing information to refine display regions when the respective channels are available.
- iOS: combine existing WebKit H5 fitting with same-snapshot UID / visibleFrame clipping; include an optional read-only WDA patch and check/apply tool. Stock WDA falls back to ordinary capture.
- HarmonyOS: use enriched UiTest identities and process-scoped RenderService backgrounds and supported rounded corners, with foreground-application scope checks.
- Preserve candidate order, IDs, original action bounds and tap centers. Unavailable, ambiguous or unsupported geometry keeps the original drawing; unsafe label placement falls back to the baseline image. H5 and native results remain independent.
- Keep existing click sequencing and V3 page-stability parameters; add no stability wait, click retry or final screenshot.
- Package the WDA extension and its license notice, expose enhancement status/timing, and document installation and upgrades.
- Validation: 62 automated tests, 20 saved business-page replays and scoped live SDK checks on iOS hardware / HarmonyOS emulator. This does not guarantee coverage of every application or OS version.

## 0.1.1 — 2026-10-13

- Synchronize the existing V3 point-centered annotations across all three platforms; candidate bounds and tap coordinates remain unchanged.
- Reuse settled Android frames and their dimensions without another screenshot or device-size query.
- Retain the approved 180-second model connection keepalive and require Pillow 10.1+ for the existing renderer.
- Add the qualified four-step Demo recording, bilingual timing breakdown, upgrade and maintenance instructions.
- Maintain compatibility with existing public call signatures.

## 0.1.0 — 2026-10-12

- Standalone Android, iOS and HarmonyOS click SDK.
- Symbol-separated sequence execution, image-comparison transitions and frame reuse.
- V3-aligned platform channels and timing parameters.
- Android Demo, illustrated README, local GIF and integration examples.
- iOS StaticText candidate coverage and duplicate-region filtering.
