import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';

/// Sign-in code delivery: which countries can sign in now, and whether a
/// code reached the user (WhatsApp reports this after sending).
abstract interface class OtpDeliveryRepository {
  /// Countries whose sign-in channel is switched on, Kenya first.
  Future<List<SignInCountry>> getSignInCountries();

  Future<OtpDeliveryStatus> getDeliveryStatus(String challengeId);
}
