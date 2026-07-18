import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/app/app.dart';

void main() {
  testWidgets('SWETO app starts successfully', (tester) async {
    await tester.pumpWidget(const SwetoApp());

    expect(find.text('SWETO'), findsOneWidget);
  });
}
