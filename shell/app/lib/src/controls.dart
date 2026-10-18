import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'hub_connection.dart';
import 'protocol.dart';

/// What the screen knows about the controls it sent.
class ControlsState {
  const ControlsState({this.pending = const {}, this.notice});

  /// Entities with a control on its way: sent, not answered yet.
  final Set<String> pending;

  /// Why the last control did not work. Clears itself after a few seconds.
  final String? notice;
}

/// Sends `control` to the hub and follows the reply.
///
/// The screen never changes a tile on its own: the new state comes from the hub as
/// state.update. This only tracks what is waiting and what failed.
class Controls extends Notifier<ControlsState> {
  static const replyTimeout = Duration(seconds: 5);
  static const noticeDuration = Duration(seconds: 4);
  static const noReply = 'Hub-ul nu a răspuns.';

  final _waiting = <String, ({String entityId, Timer timer})>{};
  Timer? _noticeTimer;

  @override
  ControlsState build() {
    final subscription = ref.watch(hubProvider).messages.listen(_onMessage, onError: (_) {});
    ref.onDispose(() {
      subscription.cancel();
      _noticeTimer?.cancel();
      for (final waiting in _waiting.values) {
        waiting.timer.cancel();
      }
      _waiting.clear();
    });
    return const ControlsState();
  }

  void send(String entityId, String action) {
    if (state.pending.contains(entityId)) return;
    final id = Envelope.newId();
    final sent = ref.read(hubProvider).send('control', {'entityId': entityId, 'action': action}, id: id);
    if (!sent) {
      _show(noReply);
      return;
    }
    _waiting[id] = (entityId: entityId, timer: Timer(replyTimeout, () => _finish(id, notice: noReply)));
    state = ControlsState(pending: {...state.pending, entityId}, notice: state.notice);
  }

  void _onMessage(Envelope msg) {
    final id = msg.replyTo;
    if (id == null || !_waiting.containsKey(id)) return;
    switch (msg.type) {
      case 'action.result':
        final result = ActionResult.fromJson(msg.payload);
        _finish(id, notice: result.ok ? null : result.message);
      case 'error':
        _finish(id, notice: errorText(HubError.fromJson(msg.payload).code));
    }
  }

  void _finish(String id, {String? notice}) {
    final waiting = _waiting.remove(id);
    if (waiting == null) return;
    waiting.timer.cancel();
    state = ControlsState(pending: {...state.pending}..remove(waiting.entityId), notice: state.notice);
    if (notice != null) _show(notice);
  }

  void _show(String notice) {
    _noticeTimer?.cancel();
    _noticeTimer = Timer(noticeDuration, () => state = ControlsState(pending: state.pending));
    state = ControlsState(pending: state.pending, notice: notice);
  }
}

/// What the screen says for each error code of the protocol.
String errorText(String code) => switch (code) {
      'unavailable' => 'Home Assistant nu răspunde.',
      'not_allowed' => 'Acțiunea nu e permisă de aici.',
      'unknown_entity' => 'Dispozitiv necunoscut.',
      _ => 'Nu a mers.',
    };

final controlsProvider = NotifierProvider<Controls, ControlsState>(Controls.new);
