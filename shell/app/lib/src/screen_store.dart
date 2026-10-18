import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:path_provider/path_provider.dart';

/// Who this screen is to the hub: its id, and once paired, its token and the hub's
/// certificate fingerprint.
class ScreenIdentity {
  const ScreenIdentity({required this.screenId, this.token, this.hubFingerprint});

  /// A new screen: a random id, not paired.
  factory ScreenIdentity.fresh([Random? random]) {
    final r = random ?? Random.secure();
    return ScreenIdentity(screenId: List.generate(12, (_) => r.nextInt(16).toRadixString(16)).join());
  }

  factory ScreenIdentity.fromJson(Map<String, Object?> json) => ScreenIdentity(
        screenId: json['screenId']! as String,
        token: json['token'] as String?,
        hubFingerprint: json['hubFingerprint'] as String?,
      );

  final String screenId;
  final String? token;

  /// SHA-256 of the hub's certificate, lowercase hex, pinned when the screen paired.
  final String? hubFingerprint;

  bool get paired => token != null;

  /// Back to unpaired, keeping the id.
  ScreenIdentity unpaired() => ScreenIdentity(screenId: screenId);

  ScreenIdentity withToken(String token, String? hubFingerprint) =>
      ScreenIdentity(screenId: screenId, token: token, hubFingerprint: hubFingerprint);

  Map<String, Object?> toJson() => {
        'screenId': screenId,
        if (token != null) 'token': token,
        if (hubFingerprint != null) 'hubFingerprint': hubFingerprint,
      };

  @override
  String toString() => 'ScreenIdentity($screenId, paired: $paired)';
}

/// Where the identity is kept between starts.
abstract interface class ScreenStore {
  Future<ScreenIdentity> load();
  Future<void> save(ScreenIdentity identity);
}

/// A JSON file in the app's private support directory.
class FileScreenStore implements ScreenStore {
  FileScreenStore({Future<Directory> Function()? directory})
      : _directory = directory ?? getApplicationSupportDirectory;

  final Future<Directory> Function() _directory;

  Future<File> get _file async => File('${(await _directory()).path}/screen.json');

  @override
  Future<ScreenIdentity> load() async {
    final file = await _file;
    if (await file.exists()) {
      return ScreenIdentity.fromJson((jsonDecode(await file.readAsString()) as Map).cast<String, Object?>());
    }
    final fresh = ScreenIdentity.fresh();
    await save(fresh);
    return fresh;
  }

  @override
  Future<void> save(ScreenIdentity identity) async {
    final file = await _file;
    await file.parent.create(recursive: true);
    final tmp = File('${file.path}.tmp');
    await tmp.writeAsString(jsonEncode(identity.toJson()), flush: true);
    await tmp.rename(file.path);
  }
}

/// For tests, and for nothing else.
class MemoryScreenStore implements ScreenStore {
  MemoryScreenStore([ScreenIdentity? identity]) : identity = identity ?? ScreenIdentity.fresh();

  ScreenIdentity identity;

  @override
  Future<ScreenIdentity> load() async => identity;

  @override
  Future<void> save(ScreenIdentity identity) async => this.identity = identity;
}
