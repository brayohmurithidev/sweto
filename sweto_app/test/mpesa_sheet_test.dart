import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/features/members/presentation/mpesa_payment_sheet.dart';

import 'members_screens_test.dart'
    show FakeMembers, FakePricing, fakeApiError, fakeMember;

const _pending = MpesaPayment(
  paymentId: 'pay-1',
  state: PaymentState.pending,
  message: 'Waiting for the member to enter their M-Pesa PIN.',
);

Future<List<MpesaPayment?>> _open(WidgetTester tester, FakeMembers repo) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final results = <MpesaPayment?>[];
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        membersRepositoryProvider.overrideWithValue(repo),
        gymOwnerRepositoryProvider.overrideWithValue(FakePricing()),
      ],
      child: MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: TextButton(
              onPressed: () async => results.add(
                await showMpesaPaymentSheet(
                  context,
                  gymId: 'gym-1',
                  member: fakeMember('1', 'Achieng Otieno'),
                  pollEvery: const Duration(seconds: 1),
                  giveUpAfter: const Duration(seconds: 3),
                ),
              ),
              child: const Text('open'),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.tap(find.text('open'));
  await tester.pumpAndSettle();
  return results;
}

void main() {
  testWidgets('sends the prompt, waits, and closes when paid', (tester) async {
    final repo = FakeMembers()
      ..paymentUpdates.addAll([
        _pending,
        MpesaPayment(
          paymentId: 'pay-1',
          state: PaymentState.completed,
          message: 'Paid.',
          receipt: 'TKE1ABC2DE',
          paidUntil: DateTime(2026, 12, 13),
        ),
      ]);
    final results = await _open(tester, repo);

    await tester.tap(find.byKey(const Key('mpesa-send')));
    await tester.pump();
    expect(repo.mpesaRequests, [('1', 'plan-monthly', 5000)]);
    expect(
      find.text('Waiting for Achieng Otieno to enter their M-Pesa PIN…'),
      findsOneWidget,
    );

    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('mpesa-send')), findsNothing);
    expect(results.single?.receipt, 'TKE1ABC2DE');
    expect(
      mpesaPaidMessage(results.single!),
      'M-Pesa payment received. Paid until 13 Dec 2026. Receipt TKE1ABC2DE.',
    );
  });

  testWidgets('a cancelled prompt says why and can be sent again', (
    tester,
  ) async {
    final repo = FakeMembers()
      ..paymentUpdates.add(
        const MpesaPayment(
          paymentId: 'pay-1',
          state: PaymentState.failed,
          message: 'The member cancelled the M-Pesa prompt.',
        ),
      );
    await _open(tester, repo);

    await tester.tap(find.byKey(const Key('mpesa-send')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    await tester.pump();

    expect(find.byKey(const Key('mpesa-state-failed')), findsOneWidget);
    expect(
      find.text('The member cancelled the M-Pesa prompt.'),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const Key('mpesa-try-again')));
    await tester.pump();
    expect(find.byKey(const Key('mpesa-send')), findsOneWidget);
  });

  testWidgets('M-Pesa switched off is explained, not a raw error', (
    tester,
  ) async {
    final repo = FakeMembers()
      ..mpesaError = fakeApiError(
        "M-Pesa payments aren't switched on yet. Record cash for now.",
      );
    await _open(tester, repo);

    await tester.tap(find.byKey(const Key('mpesa-send')));
    await tester.pump();

    expect(
      find.text("M-Pesa payments aren't switched on yet. Record cash for now."),
      findsOneWidget,
    );
  });

  testWidgets('after a while without an answer it can be left to finish', (
    tester,
  ) async {
    final repo = FakeMembers()..paymentUpdates.add(_pending);
    final results = await _open(tester, repo);

    await tester.tap(find.byKey(const Key('mpesa-send')));
    await tester.pump();
    for (var i = 0; i < 4; i++) {
      await tester.pump(const Duration(seconds: 1));
    }

    expect(find.textContaining('Still waiting for M-Pesa.'), findsOneWidget);
    await tester.tap(find.byKey(const Key('mpesa-close')));
    await tester.pumpAndSettle();
    expect(results, [null]);
  });
}
