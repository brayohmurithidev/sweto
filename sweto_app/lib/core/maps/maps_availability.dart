import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

const _channel = MethodChannel('sweto/maps');

/// Whether this build has a Google Maps key. Without one, iOS aborts the app
/// as soon as a map is drawn, so screens show their non-map fallback instead.
/// Anything unexpected (no native handler, tests, other platforms) counts as
/// "no map": a missing map is better than a crash.
final mapsAvailableProvider = FutureProvider<bool>((ref) async {
  try {
    return await _channel.invokeMethod<bool>('isConfigured') ?? false;
  } on MissingPluginException {
    return false;
  } on PlatformException {
    return false;
  }
});
