import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/check_in_screen.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';

import 'members_screens_test.dart' show FakeMembers, fakeApiError;

CheckInOutcome _outcome(
  CheckInResult result, {
  bool repeat = false,
  String message = 'Welcome, Achieng Otieno.',
  String? name = 'Achieng Otieno',
}) => CheckInOutcome(
  result: result,
  alreadyCheckedInToday: repeat,
  message: message,
  memberName: name,
  paidUntil: name == null ? null : DateTime(2026, 12, 13),
  planName: name == null ? null : 'Monthly',
);

/// Stands in for the camera: a button that "scans" [value].
CheckInScannerBuilder _scanner(String value) =>
    (context, onCode) => Center(
      child: TextButton(
        key: const Key('fake-scan'),
        onPressed: () => onCode(value),
        child: const Text('scan'),
      ),
    );

Future<void> _pump(
  WidgetTester tester,
  FakeMembers repo, {
  CheckInScannerBuilder? scanner,
}) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [membersRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp(
        home: CheckInScreen(
          gymId: 'gym-1',
          scannerBuilder: scanner ?? _scanner('sweto:checkin:7KQ2M9XD'),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _type(WidgetTester tester, String code) async {
  await tester.enterText(find.byKey(const Key('check-in-code-field')), code);
  await tester.tap(find.byKey(const Key('check-in-submit')));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('a typed code must look like a check-in code', (tester) async {
    final repo = FakeMembers()
      ..checkInResult = (_) => _outcome(CheckInResult.allowed);
    await _pump(tester, repo);

    // Extra characters can't be typed at all: the field stops at 8.
    for (final bad in ['', '7KQ2', '0OIL-1234']) {
      await _type(tester, bad);
      expect(
        find.text('Enter the 8-character code, e.g. 7KQ2-M9XD.'),
        findsOneWidget,
        reason: bad,
      );
    }
    expect(repo.checkInCodes, isEmpty);

    await _type(tester, ' 7kq2 m9xd ');
    expect(repo.checkInCodes, ['7KQ2M9XD']);
  });

  testWidgets('allowed shows a green card, then back to the next member', (
    tester,
  ) async {
    final repo = FakeMembers()
      ..checkInResult = (_) => _outcome(CheckInResult.allowed);
    await _pump(tester, repo);

    await _type(tester, '7KQ2-M9XD');
    expect(find.byKey(const Key('check-in-result-allowed')), findsOneWidget);
    expect(find.text('Allowed in'), findsOneWidget);
    expect(find.text('Achieng Otieno'), findsOneWidget);
    expect(find.text('Monthly · paid until 13 Dec 2026'), findsOneWidget);

    await tester.tap(find.byKey(const Key('check-in-next')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('check-in-code-field')), findsOneWidget);
  });

  testWidgets('a repeat visit the same day shows "Already in today"', (
    tester,
  ) async {
    final repo = FakeMembers()
      ..checkInResult = (_) => _outcome(
        CheckInResult.allowed,
        repeat: true,
        message: 'Achieng Otieno already checked in today.',
      );
    await _pump(tester, repo);

    await _type(tester, '7KQ2-M9XD');
    expect(find.text('Already in today'), findsOneWidget);
    expect(
      find.text('Achieng Otieno already checked in today.'),
      findsOneWidget,
    );
  });

  const refusals = {
    CheckInResult.expired: 'Membership expired',
    CheckInResult.notStarted: 'Not started yet',
    CheckInResult.noMembership: 'No membership',
    CheckInResult.archived: 'Member archived',
    CheckInResult.visitLimitReached: 'Visits used up',
    CheckInResult.unknownCode: 'Code not recognised',
  };
  for (final MapEntry(key: result, value: title) in refusals.entries) {
    testWidgets('refused: ${result.apiValue} shows "$title" with the reason', (
      tester,
    ) async {
      final unknown = result == CheckInResult.unknownCode;
      final repo = FakeMembers()
        ..checkInResult = (_) => _outcome(
          result,
          message: 'Reason from the server.',
          name: unknown ? null : 'Achieng Otieno',
        );
      await _pump(tester, repo);

      await _type(tester, '7KQ2-M9XD');
      expect(
        find.byKey(Key('check-in-result-${result.apiValue}')),
        findsOneWidget,
      );
      expect(find.text(title), findsOneWidget);
      expect(find.text('Reason from the server.'), findsOneWidget);
      expect(
        find.byKey(const Key('check-in-member-name')),
        unknown ? findsNothing : findsOneWidget,
      );
    });
  }

  testWidgets('a scan checks in once even if the camera repeats it', (
    tester,
  ) async {
    final repo = FakeMembers()
      ..checkInResult = (_) => _outcome(CheckInResult.allowed);
    await _pump(tester, repo);

    await tester.tap(find.byKey(const Key('fake-scan')));
    await tester.pumpAndSettle();
    expect(repo.checkInCodes, ['sweto:checkin:7KQ2M9XD']);
    expect(find.text('Allowed in'), findsOneWidget);

    // Back to scanning straight away: the same QR still in view is ignored.
    await tester.tap(find.byKey(const Key('check-in-next')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('fake-scan')));
    await tester.pumpAndSettle();
    expect(repo.checkInCodes, hasLength(1));
  });

  testWidgets('a server error is shown without leaving the screen', (
    tester,
  ) async {
    final repo = FakeMembers()
      ..checkInError = fakeApiError(
        'Too many check-in attempts. Wait a moment and try again.',
      );
    await _pump(tester, repo);

    await _type(tester, '7KQ2-M9XD');
    expect(
      find.text('Too many check-in attempts. Wait a moment and try again.'),
      findsOneWidget,
    );
    expect(find.byKey(const Key('check-in-submit')), findsOneWidget);
  });

  testWidgets("today's counts and list are shown", (tester) async {
    final repo = FakeMembers()
      ..today = CheckInDay(
        visits: 1,
        refused: 1,
        entries: [
          CheckInEntry(
            id: '2',
            result: CheckInResult.unknownCode,
            alreadyCheckedInToday: false,
            checkedInAt: DateTime(2026, 11, 14, 9, 5),
          ),
          CheckInEntry(
            id: '1',
            result: CheckInResult.allowed,
            alreadyCheckedInToday: false,
            checkedInAt: DateTime(2026, 11, 14, 8, 30),
            memberName: 'Achieng Otieno',
          ),
        ],
      );
    await _pump(tester, repo);

    expect(find.text('1 in · 1 refused'), findsOneWidget);
    expect(find.text('Unknown code'), findsOneWidget);
    expect(find.text('08:30'), findsOneWidget);
  });
}
