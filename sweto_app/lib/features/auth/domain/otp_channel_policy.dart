import 'package:sweto_app/core/phone/phone_country.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';

/// Countries whose sign-in codes go by SMS. Mirrors the API's
/// OTP_SMS_REGIONS (decision D-011); every other supported country uses
/// WhatsApp.
///
/// The app only uses this for the hint before a code is requested. After
/// the request, the channel in the API response is what the app shows.
const smsOtpCountryCodes = {'KE'};

OtpDeliveryChannel expectedOtpChannel(PhoneCountry country) =>
    smsOtpCountryCodes.contains(country.isoCode)
    ? OtpDeliveryChannel.sms
    : OtpDeliveryChannel.whatsapp;
