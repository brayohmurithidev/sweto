/// A country users can pick for their phone number.
///
/// Mobile number rules come from libphonenumber's metadata (version 9.0.34,
/// the same library the API validates with), so a number the app accepts is
/// one the server accepts. The server is still authoritative.
class PhoneCountry {
  const PhoneCountry({
    required this.isoCode,
    required this.name,
    required this.dialCode,
    required this.mobileLengths,
    required this.mobilePattern,
    required this.groups,
    required this.example,
    this.nationalPrefix,
  });

  /// ISO 3166-1 alpha-2 code, for example `KE`.
  final String isoCode;
  final String name;

  /// Country calling code without `+`, for example `254`.
  final String dialCode;

  /// Trunk prefix dialled inside the country (`0` in `0712…`), if any.
  final String? nationalPrefix;

  /// Valid lengths of the subscriber (national significant) number.
  final Set<int> mobileLengths;

  /// libphonenumber's mobile pattern for the subscriber number.
  final String mobilePattern;

  /// Digit groups used to display the subscriber number, e.g. `[3, 3, 3]`.
  final List<int> groups;

  /// Example subscriber number, already grouped, used as the field hint.
  final String example;

  int get maxLength => mobileLengths.reduce((a, b) => a > b ? a : b);

  String get displayDialCode => '+$dialCode';

  /// Flag emoji built from the ISO code's regional indicator symbols.
  String get flag => String.fromCharCodes(
    isoCode.codeUnits.map((unit) => 0x1F1E6 + unit - 0x41),
  );

  @override
  bool operator ==(Object other) =>
      other is PhoneCountry && other.isoCode == isoCode;

  @override
  int get hashCode => isoCode.hashCode;
}

const kenya = PhoneCountry(
  isoCode: 'KE',
  name: 'Kenya',
  dialCode: '254',
  nationalPrefix: '0',
  mobileLengths: {9},
  mobilePattern: r'(?:1(?:0[0-8]|1\d|2[014]|30|4[0-5])|7\d\d)\d{6}',
  groups: [3, 3, 3],
  example: '712 345 678',
);

/// Countries whose numbers can sign in. Must match the API's
/// OTP_SUPPORTED_REGIONS (decision D-011). Kenya first, then by name.
const supportedPhoneCountries = <PhoneCountry>[
  kenya,
  PhoneCountry(
    isoCode: 'BI',
    name: 'Burundi',
    dialCode: '257',
    mobileLengths: {8},
    mobilePattern: r'(?:29|6[1-9]|7[125-9])\d{6}',
    groups: [2, 2, 2, 2],
    example: '79 56 12 34',
  ),
  PhoneCountry(
    isoCode: 'CD',
    name: 'DR Congo',
    dialCode: '243',
    nationalPrefix: '0',
    mobileLengths: {7, 9},
    mobilePattern: r'88\d{5}|(?:8[0-69]|9[016-9])\d{7}',
    groups: [3, 3, 3],
    example: '991 234 567',
  ),
  PhoneCountry(
    isoCode: 'RW',
    name: 'Rwanda',
    dialCode: '250',
    nationalPrefix: '0',
    mobileLengths: {9},
    mobilePattern: r'7[237-9]\d{7}',
    groups: [3, 3, 3],
    example: '720 123 456',
  ),
  PhoneCountry(
    isoCode: 'SO',
    name: 'Somalia',
    dialCode: '252',
    nationalPrefix: '0',
    mobileLengths: {7, 8, 9},
    mobilePattern:
        r'(?:(?:15|(?:3[59]|4[89]|6\d|7[0-35-9]|8[08])\d|9(?:0\d|[2-9]))\d'
        r'|2(?:4\d|8))\d{5}|(?:[67]\d\d|904)\d{5}',
    groups: [3, 3, 3],
    example: '711 234 56',
  ),
  PhoneCountry(
    isoCode: 'SS',
    name: 'South Sudan',
    dialCode: '211',
    nationalPrefix: '0',
    mobileLengths: {9},
    mobilePattern: r'(?:12|9[1257-9])\d{7}',
    groups: [3, 3, 3],
    example: '977 123 456',
  ),
  PhoneCountry(
    isoCode: 'TZ',
    name: 'Tanzania',
    dialCode: '255',
    nationalPrefix: '0',
    mobileLengths: {9},
    mobilePattern: r'(?:6[1-35-9]|7\d)\d{7}',
    groups: [3, 3, 3],
    example: '621 234 567',
  ),
  PhoneCountry(
    isoCode: 'UG',
    name: 'Uganda',
    dialCode: '256',
    nationalPrefix: '0',
    mobileLengths: {9},
    mobilePattern: r'7280\d{5}|7(?:[014-8]\d|2[01467]|3[016]|9[0-589])\d{6}',
    groups: [3, 3, 3],
    example: '712 345 678',
  ),
];
