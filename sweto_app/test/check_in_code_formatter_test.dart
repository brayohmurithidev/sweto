import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/features/members/presentation/check_in_screen.dart';

/// Types [text] one character at a time, like a keyboard.
String _type(String text) {
  const formatter = CheckInCodeInputFormatter();
  var value = TextEditingValue.empty;
  for (final char in text.split('')) {
    final next = TextEditingValue(text: value.text + char);
    value = formatter.formatEditUpdate(value, next);
  }
  return value.text;
}

TextEditingValue _edit(String before, String after) =>
    const CheckInCodeInputFormatter().formatEditUpdate(
      TextEditingValue(text: before),
      TextEditingValue(text: after),
    );

void main() {
  test('capitals and the dash appear while typing', () {
    expect(_type('tav'), 'TAV');
    expect(_type('tavm'), 'TAVM-');
    expect(_type('tavmpfuz'), 'TAVM-PFUZ');
  });

  test('a typed dash or space is not doubled, extras are dropped', () {
    expect(_type('tavm-pfuz'), 'TAVM-PFUZ');
    expect(_type('tavm pfuz'), 'TAVM-PFUZ');
    expect(_type('tavmpfuzxx'), 'TAVM-PFUZ');
  });

  test('characters codes never use are ignored (0, O, 1, I, L)', () {
    expect(_type('t0aOv1mIpLfuz'), 'TAVM-PFUZ');
  });

  test('backspacing over the dash removes it', () {
    expect(_edit('TAVM-', 'TAVM').text, 'TAVM');
    expect(_edit('TAVM-P', 'TAVM-').text, 'TAVM');
  });

  test('a pasted QR payload keeps only the code', () {
    expect(_edit('', 'sweto:checkin:TAVMPFUZ').text, 'TAVM-PFUZ');
  });

  test('the cursor stays at the end', () {
    final value = _edit('TAV', 'TAVM');
    expect(value.selection.baseOffset, value.text.length);
  });
}
