import 'package:aether_shell/src/controls.dart';
import 'package:aether_shell/src/hub_connection.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_hub.dart';

void main() {
  late FakeHub hub;
  late ProviderContainer container;

  // Called in the test body, not in setUp: timers must start inside the test's
  // fake clock for tester.pump to move them.
  void start() {
    hub = FakeHub();
    container = ProviderContainer(overrides: [hubProvider.overrideWithValue(hub)]);
    addTearDown(container.dispose);
    container.listen(controlsProvider, (_, __) {});
  }

  ControlsState state() => container.read(controlsProvider);
  Controls controls() => container.read(controlsProvider.notifier);

  test('send goes to the hub as control and waits for the reply', () {
    start();
    controls().send('light.office', 'toggle');
    expect(hub.sent.single['type'], 'control');
    expect(hub.lastPayload, {'entityId': 'light.office', 'action': 'toggle'});
    expect(state().pending, {'light.office'});

    hub.say('action.result', {'ok': true, 'message': 'Comanda a fost trimisă.'}, reply: true);
    expect(state().pending, isEmpty);
    expect(state().notice, isNull);
  });

  test('a second tap while waiting is not sent', () {
    start();
    controls().send('light.office', 'toggle');
    controls().send('light.office', 'toggle');
    controls().send('switch.plug', 'toggle');
    expect(hub.sent, hasLength(2));
    expect(state().pending, {'light.office', 'switch.plug'});
  });

  test('messages that answer something else are ignored', () {
    start();
    controls().send('light.office', 'toggle');
    hub.say('action.result', {'ok': false, 'message': 'Alt ecran.'});
    hub.say('state.update', {'section': 'weather', 'value': null});
    expect(state().pending, {'light.office'});
    expect(state().notice, isNull);
  });

  test('a failed action shows what the hub said', () {
    start();
    controls().send('light.office', 'toggle');
    hub.say('action.result', {'ok': false, 'message': 'Nu a mers. Home Assistant a refuzat comanda.'}, reply: true);
    expect(state().pending, isEmpty);
    expect(state().notice, 'Nu a mers. Home Assistant a refuzat comanda.');
  });

  for (final (code, text) in [
    ('unavailable', 'Home Assistant nu răspunde.'),
    ('not_allowed', 'Acțiunea nu e permisă de aici.'),
    ('unknown_entity', 'Dispozitiv necunoscut.'),
    ('internal', 'Nu a mers.'),
  ]) {
    test('error $code becomes a Romanian sentence', () {
      start();
      controls().send('light.office', 'toggle');
      hub.say('error', {'code': code, 'message': 'English, for the log.'}, reply: true);
      expect(state().pending, isEmpty);
      expect(state().notice, text);
    });
  }

  test('without a connection nothing waits', () {
    start();
    hub.connected = false;
    controls().send('light.office', 'toggle');
    expect(hub.sent, isEmpty);
    expect(state().pending, isEmpty);
    expect(state().notice, Controls.noReply);
  });

  test('a lost connection does not break the controls', () {
    start();
    hub.drop();
    controls().send('light.office', 'toggle');
    expect(state().pending, {'light.office'});
  });

  testWidgets('no reply in time is said, and the tile stops waiting', (tester) async {
    start();
    controls().send('light.office', 'toggle');
    await tester.pump(Controls.replyTimeout - const Duration(milliseconds: 1));
    expect(state().pending, {'light.office'});
    await tester.pump(const Duration(milliseconds: 1));
    expect(state().pending, isEmpty);
    expect(state().notice, Controls.noReply);

    hub.say('action.result', {'ok': true, 'message': 'Prea târziu.'}, reply: true);
    expect(state().notice, Controls.noReply);
    await tester.pump(Controls.noticeDuration);
  });

  testWidgets('the notice clears itself', (tester) async {
    start();
    controls().send('light.office', 'toggle');
    hub.say('error', {'code': 'unavailable', 'message': 'x'}, reply: true);
    expect(state().notice, isNotNull);
    await tester.pump(Controls.noticeDuration);
    expect(state().notice, isNull);
  });

  testWidgets('a new failure restarts the notice', (tester) async {
    start();
    controls().send('light.office', 'toggle');
    hub.say('error', {'code': 'unavailable', 'message': 'x'}, reply: true);
    await tester.pump(Controls.noticeDuration - const Duration(seconds: 1));
    controls().send('light.office', 'toggle');
    hub.say('error', {'code': 'not_allowed', 'message': 'x'}, reply: true);
    await tester.pump(const Duration(seconds: 1));
    expect(state().notice, 'Acțiunea nu e permisă de aici.');
    await tester.pump(Controls.noticeDuration);
    expect(state().notice, isNull);
  });
}
