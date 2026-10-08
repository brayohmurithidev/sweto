import 'package:flutter/services.dart';

class KenyaPhoneFormatter extends TextInputFormatter {
  const KenyaPhoneFormatter();

  static const int maximumDigits = 9;

  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    var digits = newValue.text.replaceAll(RegExp(r'\D'), '');

    // Users may paste 07XXXXXXXX, 01XXXXXXXX, +254XXXXXXXXX or 254XXXXXXXXX.
    if (digits.startsWith('254')) {
      digits = digits.substring(3);
    }

    if (digits.startsWith('0')) {
      digits = digits.substring(1);
    }

    if (digits.length > maximumDigits) {
      digits = digits.substring(0, maximumDigits);
    }

    final formatted = _formatDigits(digits);

    return TextEditingValue(
      text: formatted,
      selection: TextSelection.collapsed(offset: formatted.length),
    );
  }

  static String _formatDigits(String digits) {
    if (digits.isEmpty) {
      return '';
    }

    if (digits.length <= 3) {
      return digits;
    }

    if (digits.length <= 6) {
      return '${digits.substring(0, 3)} ${digits.substring(3)}';
    }

    return '${digits.substring(0, 3)} '
        '${digits.substring(3, 6)} '
        '${digits.substring(6)}';
  }

  /// Formats a stored number (for example E.164 `+254712345678`) for a
  /// [KenyaPhoneField], which already shows the +254 prefix: `712 345 678`.
  ///
  /// Text assigned to a controller in code skips input formatters, so values
  /// that pre-fill the field must go through this instead.
  static String formatForField(String value) {
    return const KenyaPhoneFormatter()
        .formatEditUpdate(TextEditingValue.empty, TextEditingValue(text: value))
        .text;
  }

  static String digitsOnly(String value) {
    return value.replaceAll(RegExp(r'\D'), '');
  }

  static bool isValid(String value) {
    final digits = _normalizedDigits(value);

    if (digits.length != maximumDigits) {
      return false;
    }

    // Kenyan mobile numbers start with either 7 or 1 after +254.
    return digits.startsWith('7') || digits.startsWith('1');
  }

  static String toInternational(String value) {
    final digits = _normalizedDigits(value);

    if (!isValid(digits)) {
      throw const FormatException('Invalid Kenyan phone number.');
    }

    return '+254$digits';
  }

  static String _normalizedDigits(String value) {
    var digits = digitsOnly(value);
    if (digits.startsWith('254')) {
      digits = digits.substring(3);
    }
    if (digits.startsWith('0')) {
      digits = digits.substring(1);
    }
    return digits;
  }
}
