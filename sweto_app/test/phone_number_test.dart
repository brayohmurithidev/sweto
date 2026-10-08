import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/core/phone/phone_country.dart';
import 'package:sweto_app/core/phone/phone_number.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/otp_channel_policy.dart';

PhoneCountry country(String isoCode) =>
    supportedPhoneCountries.firstWhere((c) => c.isoCode == isoCode);

void main() {
  group('Kenya (existing behaviour)', () {
    test('accepts 7-series and 1-series mobiles in every typed form', () {
      for (final entry in <String, String>{
        '0712345678': '+254712345678',
        '0112345678': '+254112345678',
        '712345678': '+254712345678',
        '112345678': '+254112345678',
        '712 345 678': '+254712345678',
        '+254712345678': '+254712345678',
        '+254 112 345 678': '+254112345678',
        '254712345678': '+254712345678',
      }.entries) {
        expect(
          PhoneNumbers.isValid(kenya, entry.key),
          isTrue,
          reason: entry.key,
        );
        expect(PhoneNumbers.toE164(kenya, entry.key), entry.value);
      }
    });

    test('formats as 712 345 678 without the +254 prefix', () {
      expect(PhoneNumbers.format(kenya, '+254712345678'), '712 345 678');
      expect(PhoneNumbers.format(kenya, '0712345678'), '712 345 678');
      expect(PhoneNumbers.format(kenya, '7123'), '712 3');
    });

    test('rejects short, long and non-mobile numbers', () {
      for (final input in ['71234567', '0201234567', '812345678', '']) {
        expect(PhoneNumbers.isValid(kenya, input), isFalse, reason: input);
      }
      expect(
        () => PhoneNumbers.toE164(kenya, '0201234567'),
        throwsA(isA<FormatException>()),
      );
    });
  });

  group('other countries', () {
    test('local numbers normalise to E.164 for the selected country', () {
      for (final (code, input, e164) in [
        ('UG', '0701234567', '+256701234567'),
        ('UG', '701 234 567', '+256701234567'),
        ('TZ', '0712345678', '+255712345678'),
        ('RW', '0781234567', '+250781234567'),
        ('BI', '79123456', '+25779123456'),
      ]) {
        expect(PhoneNumbers.toE164(country(code), input), e164);
      }
    });

    test('a pasted international number keeps only the subscriber part', () {
      expect(
        PhoneNumbers.format(country('UG'), '+256701234567'),
        '701 234 567',
      );
      expect(
        PhoneNumbers.format(country('BI'), '+257 79 12 34 56'),
        '79 12 34 56',
      );
    });

    test('numbers invalid for the selected country are rejected', () {
      expect(PhoneNumbers.isValid(country('UG'), '0201234567'), isFalse);
      expect(PhoneNumbers.isValid(country('TZ'), '0221234567'), isFalse);
      expect(PhoneNumbers.isValid(country('RW'), '0712345678'), isFalse);
      expect(PhoneNumbers.isValid(country('BI'), '59123456'), isFalse);
    });

    test('every country example is a valid mobile number', () {
      for (final c in supportedPhoneCountries) {
        expect(PhoneNumbers.isValid(c, c.example), isTrue, reason: c.isoCode);
      }
    });
  });

  group('stored numbers', () {
    test('parse picks the country and drops the dial code', () {
      final uganda = PhoneNumbers.parse('+256701234567')!;
      expect(uganda.country.isoCode, 'UG');
      expect(uganda.subscriber, '701 234 567');

      final kenyan = PhoneNumbers.parse('+254712345678')!;
      expect(kenyan.country, kenya);
      expect(kenyan.subscriber, '712 345 678');
    });

    test('parse returns null for empty or unsupported numbers', () {
      expect(PhoneNumbers.parse(null), isNull);
      expect(PhoneNumbers.parse(''), isNull);
      expect(PhoneNumbers.parse('+12025550123'), isNull);
    });
  });

  test('formatter keeps the field as the grouped subscriber number', () {
    const formatter = SubscriberNumberFormatter(kenya);
    final value = formatter.formatEditUpdate(
      TextEditingValue.empty,
      const TextEditingValue(text: '+254712345678'),
    );
    expect(value.text, '712 345 678');
    expect(value.selection.baseOffset, value.text.length);
  });

  test('countries show their flag and dial code', () {
    expect(kenya.flag, '🇰🇪');
    expect(kenya.displayDialCode, '+254');
    expect(country('UG').displayDialCode, '+256');
  });

  group('OTP channel', () {
    test('Kenya gets the code by SMS', () {
      expect(expectedOtpChannel(kenya), OtpDeliveryChannel.sms);
    });

    test('every other supported country gets it on WhatsApp', () {
      for (final code in ['UG', 'TZ', 'RW', 'BI', 'SS', 'CD', 'SO']) {
        expect(
          expectedOtpChannel(country(code)),
          OtpDeliveryChannel.whatsapp,
          reason: code,
        );
      }
    });

    test('the API channel is parsed, defaulting to SMS', () {
      expect(
        OtpDeliveryChannel.fromApi('whatsapp'),
        OtpDeliveryChannel.whatsapp,
      );
      expect(OtpDeliveryChannel.fromApi('sms'), OtpDeliveryChannel.sms);
      expect(OtpDeliveryChannel.fromApi(null), OtpDeliveryChannel.sms);
    });
  });
}
