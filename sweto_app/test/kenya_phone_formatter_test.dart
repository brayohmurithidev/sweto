import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/features/auth/utils/kenya_phone_formatter.dart';

void main() {
  test('accepts Kenyan 7-series and 1-series mobile numbers', () {
    for (final entry in <String, String>{
      '0712345678': '+254712345678',
      '0112345678': '+254112345678',
      '712345678': '+254712345678',
      '112345678': '+254112345678',
      '+254712345678': '+254712345678',
      '+254112345678': '+254112345678',
    }.entries) {
      expect(KenyaPhoneFormatter.isValid(entry.key), isTrue);
      expect(KenyaPhoneFormatter.toInternational(entry.key), entry.value);
    }
  });

  test('formats stored numbers for the field without repeating +254', () {
    for (final entry in <String, String>{
      '+254712345678': '712 345 678',
      '254712345678': '712 345 678',
      '0712345678': '712 345 678',
      '+254112345678': '112 345 678',
      '': '',
    }.entries) {
      expect(KenyaPhoneFormatter.formatForField(entry.key), entry.value);
    }
  });
}
