import 'dart:math' as math;

import 'package:flutter/services.dart';
import 'package:sweto_app/core/phone/phone_country.dart';

/// A phone number split into its country and grouped subscriber digits, as
/// shown in a phone field (the dial code is shown by the country selector).
class PhoneNumberParts {
  const PhoneNumberParts({required this.country, required this.subscriber});

  final PhoneCountry country;

  /// Grouped subscriber number without dial code or trunk prefix.
  final String subscriber;
}

/// Normalisation, validation and formatting rules for phone numbers.
///
/// Every phone field uses these rules, so sign-in and onboarding accept and
/// send numbers the same way: the user types the subscriber number for the
/// selected country, and the app sends E.164 (`+256701234567`).
class PhoneNumbers {
  const PhoneNumbers._();

  static final Map<String, RegExp> _patterns = {};

  static String digitsOnly(String value) => value.replaceAll(RegExp(r'\D'), '');

  /// Returns the subscriber digits of [input] for [country].
  ///
  /// Accepts what people type or paste: `0712345678`, `712 345 678`,
  /// `+254712345678` or `254712345678`. The dial code is removed when the
  /// input starts with `+` or is too long to be a subscriber number; the
  /// trunk prefix (`0`) is removed when present.
  static String subscriberDigits(PhoneCountry country, String input) {
    var digits = digitsOnly(input);
    final international = input.trimLeft().startsWith('+');
    if (digits.startsWith(country.dialCode) &&
        (international || digits.length > country.maxLength)) {
      digits = digits.substring(country.dialCode.length);
    }
    final prefix = country.nationalPrefix;
    if (prefix != null && digits.startsWith(prefix)) {
      digits = digits.substring(prefix.length);
    }
    if (digits.length > country.maxLength) {
      digits = digits.substring(0, country.maxLength);
    }
    return digits;
  }

  /// Groups subscriber digits for display, e.g. `712 345 678`.
  static String group(PhoneCountry country, String digits) {
    final parts = <String>[];
    var start = 0;
    for (var i = 0; i < country.groups.length && start < digits.length; i++) {
      final last = i == country.groups.length - 1;
      final end = last
          ? digits.length
          : math.min(start + country.groups[i], digits.length);
      parts.add(digits.substring(start, end));
      start = end;
    }
    return parts.join(' ');
  }

  /// Formats [input] as the field shows it for [country].
  static String format(PhoneCountry country, String input) =>
      group(country, subscriberDigits(country, input));

  /// Whether [input] is a valid mobile number for [country].
  static bool isValid(PhoneCountry country, String input) {
    final digits = subscriberDigits(country, input);
    if (!country.mobileLengths.contains(digits.length)) return false;
    final pattern = _patterns.putIfAbsent(
      country.isoCode,
      () => RegExp('^(?:${country.mobilePattern})\$'),
    );
    return pattern.hasMatch(digits);
  }

  /// Returns [input] as E.164, for example `+256701234567`.
  ///
  /// Throws a [FormatException] when the number is not valid for [country].
  static String toE164(PhoneCountry country, String input) {
    if (!isValid(country, input)) {
      throw FormatException('Enter a valid mobile number for ${country.name}.');
    }
    return '+${country.dialCode}${subscriberDigits(country, input)}';
  }

  /// Splits a stored E.164 number into its country and subscriber number.
  ///
  /// Returns null for an empty value or a country not in [countries].
  static PhoneNumberParts? parse(
    String? e164, {
    List<PhoneCountry> countries = supportedPhoneCountries,
  }) {
    if (e164 == null) return null;
    final digits = digitsOnly(e164);
    if (digits.isEmpty) return null;
    for (final country in countries) {
      if (digits.startsWith(country.dialCode)) {
        return PhoneNumberParts(
          country: country,
          subscriber: format(country, '+$digits'),
        );
      }
    }
    return null;
  }
}

/// Keeps a phone field's text as the grouped subscriber number for [country].
class SubscriberNumberFormatter extends TextInputFormatter {
  const SubscriberNumberFormatter(this.country);

  final PhoneCountry country;

  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final formatted = PhoneNumbers.format(country, newValue.text);
    return TextEditingValue(
      text: formatted,
      selection: TextSelection.collapsed(offset: formatted.length),
    );
  }
}
