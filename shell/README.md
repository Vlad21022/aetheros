# Screens (shell/)

- `app/` — the Flutter app every screen runs (Mac for development, Android tablets and
  Linux later, in kiosk mode).
- `packages/aether_design/` — the design system for Flutter. `lib/src/tokens.g.dart` is
  generated from `design/tokens.json` by `tools/gen_tokens.py`.

## First run on the Mac

```sh
cd shell/app
flutter create --platforms=macos,linux,android --project-name aether_shell .
rm -f test/widget_test.dart     # if flutter create added it
```

Then allow outgoing connections on macOS: add this to both
`macos/Runner/DebugProfile.entitlements` and `macos/Runner/Release.entitlements`:

```xml
<key>com.apple.security.network.client</key>
<true/>
```

Start the hub (`cd hub && uv run aether-hub`), then:

```sh
flutter run -d macos
```

To point at a hub on another machine:
`flutter run -d macos --dart-define=AETHER_HUB=ws://192.168.1.20:8765/v1`
