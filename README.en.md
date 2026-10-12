# Jev Phone

**A multimodal visual interaction SDK for Android, iOS, and HarmonyOS.**

[English](README.en.md) · [中文](README.md)

The model chooses a numbered region in the current screen. The SDK binds that choice to a real device location and executes the tap. Integrate it into an existing AI agent, planner, test system, or script for individual taps and sequential steps.

<p align="center"><b>Android · iOS · HarmonyOS</b> / Physical devices · Emulators<br>Independent Python SDK · Same execution path in SDK and Demo · MIT</p>

[Demos](#demos) · [Why it exists](#why-it-exists) · [How it works](#how-it-works) · [Timing](#timing) · [Quick start](#quick-start)

## Demos

### Choose hard difficulty and start a challenge

A real Android phone: open practice settings → select the rightmost orange difficulty card → start the challenge. The final question is marked as hard. Playback is at original speed; the upper-right stopwatch continuously shows execution time.

![Three-step hard challenge](docs/media/demo-hard-challenge.gif)

| Action | Model request round trip |
|---|---:|
| Open practice settings | 1944.83ms |
| Select hard difficulty | 1025.65ms |
| Start the challenge | 765.28ms |

Total execution: **6570.28ms**, including capture, candidate generation, model requests, taps, and transitions between steps. [Video](docs/media/demo-hard-challenge.mp4) · [Timing record](docs/media/demo-hard-challenge.json)

### Browse sections and open practice settings

Select “Basic relations between sets” → “Basic operations on sets” → the yellow pencil in the upper-right corner to open practice settings.

![Section navigation and settings](docs/media/demo-section-switch.gif)

Model request round trips: **827.78ms / 693.05ms / 1999.53ms**. Every model request in these two recordings is below two seconds. This measures model request round trips, not complete step execution. [Video](docs/media/demo-section-switch.mp4) · [Timing record](docs/media/demo-section-switch.json)

## Why it exists

An existing system may already know what to do next, but still needs a reusable component to locate and tap the target on the current phone screen. Jev Phone connects the semantic target, visible region, and device action while leaving planning, caching, and business decisions in the calling system.

| Integration need | What the SDK handles |
|---|---|
| UI trees describe geometry but may not express an icon's appearance or meaning | Combine tree bounds with screenshot semantics to build candidate regions. |
| A model's interpretation must correspond to an executable device location | Ask the model to select a numbered region, then map that region to a tap on the current frame. |
| Platforms expose different trees, dimensions, and coordinate units | Provide platform adapters, including screenshot pixel to WDA point conversion on iOS. |
| Tuned device channels should be reusable outside a complete framework | Expose the existing AI Phone V3 capture, tap, and transition channels through an independent SDK. External planners and caches remain external. |
| A new screen may still be animating or loading after a tap | Reuse V3 image comparison between steps and carry its final frame into the next step. |

The device channels and step transitions reuse the tuned V3 implementation. The SDK does not depend on the AI Phone framework.

The figures below preserve the original Demo artwork and Chinese labels. English explanations accompany the same modules; full original images remain available.

![Visual grounding and device action binding](docs/media/modules/core.png)

## How it works

**Current target → UI tree and screenshot → numbered regions → constrained model choice → platform tap.**

The model returns a candidate ID, `NOT_FOUND`, or `UNCERTAIN`. Each request contains only the current target, candidate attributes, and annotated screenshot. The chosen ID binds to a region in that frame; the SDK taps its center.

![Region annotation and finite action space](docs/media/modules/flow.png)

Tree nodes provide geometry and attributes. Screenshots supply text, icons, and appearance. In the original illustration, a node has no text, but the model can still identify the avatar in its visual region.

![Geometry and visual semantics](docs/media/modules/grounding.png)

### Responsibilities and sequential execution

The caller owns targets, order, and business outcome checks. The SDK owns capture, candidates, model choice, taps, and transitions, returning events, annotated images, coordinates, and timing. A driver response does not establish business success.

![Caller and component responsibilities](docs/media/modules/responsibility.png)

`click(target)` executes one tap. `run(text)` splits at English or Chinese commas, semicolons, periods, question marks, exclamation marks, and newlines, up to 20 steps. Each model request contains only that step's target. Grounding or tap failures stop subsequent steps. The Demo uses the same `run()` path.

## Platform adapters

Physical-device and emulator paths are connected on all three platforms. The original website cards appear with enlarged target regions below. Source images come from Android physical-device, iOS simulator, and HarmonyOS emulator experiments; supported environments and individual image provenance are distinct.

### Android · Physical devices / Emulators

![Android website card](docs/media/modules/android.png)

![Android target detail](docs/media/modules/android-detail.png)

[Full annotated image](docs/media/android-grounding.png) · Native UiAutomator2 capture, UI tree, and coordinate taps.

### iOS · Physical devices / Simulators

![iOS website card](docs/media/modules/ios.png)

![iOS target detail](docs/media/modules/ios-detail.png)

[Full annotated image](docs/media/ios-grounding.png) · On-demand WDA screenshots, XCTest hierarchy, and pixel/point mapping.

### HarmonyOS · Physical devices / Emulators

![HarmonyOS website card](docs/media/modules/harmony.png)

![HarmonyOS target detail](docs/media/modules/harmony-detail.png)

[Full annotated image](docs/media/harmony-grounding.png) · Native capture, UITest hierarchy, and direct tap completion responses.

## Timing

**Millisecond-level timing describes individual channel operations; it does not mean every tap finishes in a few tens of milliseconds.** Model requests, capture, taps, and transitions are measured separately.

![Channel timing and measurement boundaries](docs/media/modules/timing.png)

The website's **15–50ms** figure covers local candidate processing, annotation, and encoding in an earlier experiment. **620ms** is the median Android non-model round, and **493–729ms** is the range across nine runs of the same navigation sample. These exclude model requests, initialization, and step transitions, and are not speed guarantees for every platform or screen. The recordings above separately document current SDK model round trips and sequence execution.

A single tap chain consists of the model round trip plus component processing. A sequence also includes image comparison between steps. No transition wait is added after the final step, and no extra result screenshot is taken after every tap.

| Platform | Additional V3 sampling interval |
|---|---:|
| Android | 100ms |
| iOS | 200ms |
| HarmonyOS | 0ms |

Capture itself still takes time. All three adapters reuse the comparison's final frame. If the comparison budget expires, the existing V3 behavior returns the last frame and continues without an extra stop. Execution flow and tuned parameters remain unchanged.

## Quick start

Python 3.10+. Install from source or a wheel; the package is not yet published to PyPI. Prepare your platform's device service and model credentials first.

```sh
git clone https://github.com/dongxinsuperman/jev-phone.git
cd jev-phone
python3 -m venv .venv
.venv/bin/pip install -e '.[android]'
# iOS: .venv/bin/pip install -e .
# HarmonyOS: .venv/bin/pip install -e '.[harmony]'
```

```python
from getpass import getpass
from jev_phone import AndroidClicker

with AndroidClicker(
    serial="YOUR_DEVICE_SERIAL",
    api_key=getpass("OpenRouter Key: "),
    provider="openrouter",  # Use openai for the official provider
) as phone:
    report = phone.run("Open practice settings; select hard difficulty; start the challenge")
    print(report["results"])
```

Use `IOSClicker(wda_url=..., api_key=...)` on iOS and `HarmonyClicker(serial=..., api_key=...)` on HarmonyOS. Integration requires no website or database. OpenRouter multimodal Decisions and official OpenAI Decisions use their respective credentials.

![Original integration module](docs/media/modules/integration.png)

[SDK guide, Chinese](docs/接入指南.md) · [Device preparation, Chinese](docs/三端设备准备.md) · [Example](examples/click.py) · [Parallel devices](examples/parallel.py)

## Demo and delivery scope

The Demo shows a read-only live mirror, step logs, the actual annotated model input, selected regions, coordinates, and timing. The web experience currently uses Android; three-platform SDK usage is independent of that interface.

![Full Demo interface](docs/media/site-demo.png)

Install the Demo dependencies and launch:

```sh
.venv/bin/pip install -e '.[demo]'
.venv/bin/jev-phone-demo
```

Prepare `adb`, `scrcpy`, and `ffmpeg`, then open `http://127.0.0.1:8765/`. Enter credentials in the page; refreshing clears them. SDK callers provide their own credentials. Screenshots and execution records remain local artifacts.

![Capabilities and practical notes](docs/media/modules/practice.png)

The current SDK delivers single and sequential taps. Planning, caching, business assertions, app launch, and device scheduling remain with external systems. Text input, scrolling, and long press are outside the current delivery scope. Users prepare device authorization, WDA signing, and emulator lifecycles.

[Validation overview, Chinese](docs/验证概览.md) · [MIT](LICENSE) · [Attribution](NOTICE.md) · [Full original website guide](docs/media/site-guide.png)
