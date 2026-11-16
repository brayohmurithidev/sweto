import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/features/members/presentation/mpesa_till_screen.dart';

import 'members_screens_test.dart' show FakeMembers, fakeApiError;

const _passkey =
    'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919';

Future<void> _pump(WidgetTester tester, FakeMembers repo) async {
  tester.view.physicalSize = const Size(1170, 4200);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [membersRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: MpesaTillScreen(gymId: 'gym-1')),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _enter(WidgetTester tester, String key, String text) async {
  await tester.ensureVisible(find.byKey(Key(key)));
  await tester.enterText(find.byKey(Key(key)), text);
}

Future<void> _tapSave(WidgetTester tester) async {
  await tester.ensureVisible(find.byKey(const Key('till-save')));
  await tester.tap(find.byKey(const Key('till-save')));
}

void main() {
  testWidgets('a new till needs every number and the passkey', (tester) async {
    final repo = FakeMembers();
    await _pump(tester, repo);
    expect(find.byKey(const Key('till-test-mode')), findsOneWidget);

    await _tapSave(tester);
    await tester.pump();
    expect(find.text('Enter the 5 to 7 digit number.'), findsOneWidget);
    expect(find.text('Enter the 5 to 7 digit till number.'), findsOneWidget);
    expect(find.text('Enter the passkey from Safaricom.'), findsOneWidget);

    await _enter(tester, 'till-passkey', 'short');
    await _tapSave(tester);
    await tester.pump();
    expect(find.text('That passkey looks too short.'), findsOneWidget);
    expect(repo.tillSaves, isEmpty);
  });

  testWidgets('saves a till and keeps the passkey out of sight', (
    tester,
  ) async {
    final repo = FakeMembers();
    await _pump(tester, repo);

    await _enter(tester, 'till-shortcode', '7654321');
    await _enter(tester, 'till-number', '5123456');
    await _enter(tester, 'till-passkey', _passkey);
    expect(
      tester
          .widget<TextField>(find.byKey(const Key('till-passkey')))
          .obscureText,
      isTrue,
    );
    await _tapSave(tester);
    await tester.pump();

    expect(repo.tillSaves.single, {
      'isTill': true,
      'shortcode': '7654321',
      'tillNumber': '5123456',
      'passkey': _passkey,
      'consumerKey': null,
      'consumerSecret': null,
    });
    expect(find.text('M-Pesa till saved.'), findsOneWidget);
    expect(
      tester
          .widget<TextField>(find.byKey(const Key('till-passkey')))
          .controller!
          .text,
      isEmpty,
    );
    expect(find.text('Passkey (saved)'), findsOneWidget);
  });

  testWidgets('a saved pay bill opens filled in and keeps its passkey', (
    tester,
  ) async {
    final repo = FakeMembers()
      ..till = const MpesaTill(
        configured: true,
        mode: 'production',
        shortcode: '888880',
        passkeySaved: true,
        appKeysSaved: true,
      );
    await _pump(tester, repo);

    expect(find.byKey(const Key('till-test-mode')), findsNothing);
    expect(find.byKey(const Key('till-number')), findsNothing);
    expect(find.text('Pay Bill number'), findsOneWidget);
    expect(find.text('888880'), findsOneWidget);

    await _tapSave(tester);
    await tester.pump();
    expect(repo.tillSaves.single['passkey'], isNull);
    expect(repo.tillSaves.single['consumerKey'], isNull);
    expect(repo.tillSaves.single['isTill'], isFalse);
    expect(find.text('Consumer secret (saved)'), findsOneWidget);
  });

  testWidgets('live M-Pesa needs the gym\'s own Daraja app keys', (
    tester,
  ) async {
    final repo = FakeMembers()
      ..till = const MpesaTill(configured: false, mode: 'production');
    await _pump(tester, repo);

    await _enter(tester, 'till-shortcode', '7654321');
    await _enter(tester, 'till-number', '5123456');
    await _enter(tester, 'till-passkey', _passkey);
    await _tapSave(tester);
    await tester.pump();
    expect(
      find.text('Enter the consumer key and secret from your Daraja app.'),
      findsOneWidget,
    );

    await _enter(tester, 'till-consumer-key', 'fake-key-xxxxxxxxxx');
    await _tapSave(tester);
    await tester.pump();
    expect(
      find.text('Enter both the consumer key and the consumer secret.'),
      findsOneWidget,
    );
    expect(repo.tillSaves, isEmpty);

    await _enter(tester, 'till-consumer-secret', 'fake-secret-xxxxxxxxxx');
    expect(
      tester
          .widget<TextField>(find.byKey(const Key('till-consumer-secret')))
          .obscureText,
      isTrue,
    );
    await _tapSave(tester);
    await tester.pump();

    expect(repo.tillSaves.single['consumerKey'], 'fake-key-xxxxxxxxxx');
    expect(repo.tillSaves.single['consumerSecret'], 'fake-secret-xxxxxxxxxx');
    expect(find.text('Consumer key (saved)'), findsOneWidget);
  });

  testWidgets('the go-live steps follow the account type', (tester) async {
    await _pump(tester, FakeMembers());
    await tester.tap(find.text('How to get these'));
    await tester.pumpAndSettle();
    expect(find.textContaining('primary till operator'), findsOneWidget);

    await tester.tap(find.text('Pay Bill'));
    await tester.pumpAndSettle();
    expect(find.textContaining('administrator or manager'), findsOneWidget);
  });

  testWidgets('a manager is told only the owner can change it', (tester) async {
    final repo = FakeMembers()
      ..tillError = fakeApiError(
        'Only the gym\'s owner can change where M-Pesa payments go.',
      );
    await _pump(tester, repo);

    await _enter(tester, 'till-shortcode', '7654321');
    await _enter(tester, 'till-number', '5123456');
    await _enter(tester, 'till-passkey', _passkey);
    await _tapSave(tester);
    await tester.pump();

    expect(
      find.text('Only the gym\'s owner can change where M-Pesa payments go.'),
      findsOneWidget,
    );
  });
}
