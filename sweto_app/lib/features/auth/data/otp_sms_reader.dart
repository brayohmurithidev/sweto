import 'package:smart_auth/smart_auth.dart';

/// Picks up a sign-in code from an incoming SMS so it need not be typed.
abstract class OtpSmsReader {
  /// Waits for the next SMS and returns its 6-digit code, or null when
  /// nothing usable arrived (declined, timed out, stopped, unsupported).
  Future<String?> waitForCode();

  /// Stops waiting. A pending [waitForCode] then returns null.
  Future<void> stop();
}

/// Android's SMS User Consent API: when an SMS with a code arrives, Android
/// asks the person whether SWETO may read that one message. No SMS
/// permission is needed and the SMS text does not change.
class UserConsentOtpSmsReader implements OtpSmsReader {
  UserConsentOtpSmsReader([SmartAuth? smartAuth])
    : _smartAuth = smartAuth ?? SmartAuth.instance;

  final SmartAuth _smartAuth;

  @override
  Future<String?> waitForCode() async {
    final result = await _smartAuth.getSmsWithUserConsentApi(
      matcher: r'\b\d{6}\b',
    );
    return result.data?.code;
  }

  @override
  Future<void> stop() async {
    await _smartAuth.removeUserConsentApiListener();
  }
}

/// For platforms that fill codes themselves (iOS offers the code above the
/// keyboard) or cannot read SMS at all.
class NoOtpSmsReader implements OtpSmsReader {
  const NoOtpSmsReader();

  @override
  Future<String?> waitForCode() async => null;

  @override
  Future<void> stop() async {}
}
