import 'dart:io';

import 'package:crypto/crypto.dart';

/// SHA-256 of a certificate, lowercase hex: the same value the hub logs.
String certificateFingerprint(X509Certificate certificate) => sha256.convert(certificate.der).toString();

/// Whether to trust the hub's certificate. With nothing pinned yet (only while
/// pairing) any certificate is accepted and becomes the one to pin.
bool trustHub({required String? pinned, required String presented}) => pinned == null || pinned == presented;

/// An HttpClient that trusts no certificate authority, only the hub's own
/// certificate, by fingerprint. [onPresented] gets every fingerprint the hub shows.
HttpClient pinnedHttpClient({required String? pinned, required void Function(String) onPresented}) {
  final client = HttpClient(context: SecurityContext(withTrustedRoots: false));
  client.badCertificateCallback = (certificate, host, port) {
    final presented = certificateFingerprint(certificate);
    onPresented(presented);
    return trustHub(pinned: pinned, presented: presented);
  };
  return client;
}
