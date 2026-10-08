import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/repositories/otp_delivery_repository.dart';

/// In-memory [OtpDeliveryRepository]: which countries can sign in and what
/// the delivery status of a code is.
class FakeOtpDeliveryRepository implements OtpDeliveryRepository {
  FakeOtpDeliveryRepository({
    this.countries = kenyaOnly,
    this.status = OtpDeliveryStatus.accepted,
  });

  /// What the API lists while WhatsApp is switched off.
  static const kenyaOnly = [
    SignInCountry(isoCode: 'KE', channel: OtpDeliveryChannel.sms),
  ];

  /// What the API lists once WhatsApp is on.
  static const withWhatsApp = [
    SignInCountry(isoCode: 'KE', channel: OtpDeliveryChannel.sms),
    SignInCountry(isoCode: 'BI', channel: OtpDeliveryChannel.whatsapp),
    SignInCountry(isoCode: 'CD', channel: OtpDeliveryChannel.whatsapp),
    SignInCountry(isoCode: 'RW', channel: OtpDeliveryChannel.whatsapp),
    SignInCountry(isoCode: 'SO', channel: OtpDeliveryChannel.whatsapp),
    SignInCountry(isoCode: 'SS', channel: OtpDeliveryChannel.whatsapp),
    SignInCountry(isoCode: 'TZ', channel: OtpDeliveryChannel.whatsapp),
    SignInCountry(isoCode: 'UG', channel: OtpDeliveryChannel.whatsapp),
  ];

  List<SignInCountry> countries;
  OtpDeliveryStatus status;

  /// When set, [getSignInCountries] throws this (API unreachable).
  Object? countriesError;

  final List<String> checkedChallengeIds = [];

  @override
  Future<List<SignInCountry>> getSignInCountries() async {
    final error = countriesError;
    if (error != null) throw error;
    return countries;
  }

  @override
  Future<OtpDeliveryStatus> getDeliveryStatus(String challengeId) async {
    checkedChallengeIds.add(challengeId);
    return status;
  }
}
