import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/shared/widgets/sweto_option_sheet.dart';

void main() {
  Future<List<String?>> pumpPicker(WidgetTester tester) async {
    final picked = <String?>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: SwetoSelectField(
              key: const Key('field'),
              label: 'Business type',
              value: 'Partnership',
              onTap: () async => picked.add(
                await showSwetoOptionSheet<String>(
                  context,
                  title: 'Business type',
                  selected: 'partnership',
                  options: const [
                    SwetoOption(value: 'sole', label: 'Sole Proprietorship'),
                    SwetoOption(value: 'partnership', label: 'Partnership'),
                    SwetoOption(
                      value: 'limited',
                      label: 'Limited Company',
                      detail: 'Added',
                      enabled: false,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.byKey(const Key('field')));
    await tester.pumpAndSettle();
    return picked;
  }

  testWidgets('the sheet ticks the current choice and returns a new one', (
    tester,
  ) async {
    final picked = await pumpPicker(tester);

    expect(find.text('Business type'), findsNWidgets(2)); // label + title
    expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);

    await tester.tap(find.text('Sole Proprietorship'));
    await tester.pumpAndSettle();

    expect(picked, ['sole']);
    expect(find.text('Sole Proprietorship'), findsNothing);
  });

  testWidgets('a disabled option cannot be picked', (tester) async {
    final picked = await pumpPicker(tester);

    await tester.tap(find.text('Limited Company'));
    await tester.pumpAndSettle();

    expect(picked, isEmpty);
    expect(find.text('Added'), findsOneWidget);
  });
}
