import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/auth/presentation/phone_login_screen.dart';

import 'support/fake_auth_repository.dart';

void main() {
  late FakeAuthRepository auth;
  OtpChallenge? openedChallenge;

  Future<void> pumpLogin(WidgetTester tester) async {
    auth = FakeAuthRepository();
    openedChallenge = null;
    final router = GoRouter(
      routes: [
        GoRoute(path: '/', builder: (_, _) => const PhoneLoginScreen()),
        GoRoute(
          path: AppRoutes.otpPath,
          name: AppRoutes.otpName,
          builder: (_, state) {
            openedChallenge = state.extra as OtpChallenge?;
            return const Text('otp screen');
          },
        ),
      ],
    );
    addTearDown(router.dispose);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authRepositoryProvider.overrideWithValue(auth)],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pump();
  }

  Future<void> chooseCountry(WidgetTester tester, String isoCode) async {
    await tester.tap(find.byKey(const Key('phone-country-button')));
    await tester.pumpAndSettle();
    final option = find.byKey(Key('phone-country-$isoCode'));
    await tester.ensureVisible(option);
    await tester.pumpAndSettle();
    await tester.tap(option);
    await tester.pumpAndSettle();
  }

  Text dialCode(WidgetTester tester) =>
      tester.widget<Text>(find.byKey(const Key('phone-dial-code')));

  TextField phoneField(WidgetTester tester) =>
      tester.widget<TextField>(find.byKey(const Key('phone-number-field')));

  testWidgets('Kenya is the default and its code goes by SMS', (tester) async {
    await pumpLogin(tester);

    expect(dialCode(tester).data, '+254');
    expect(find.text('Code will be sent by SMS'), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('phone-number-field')),
      '0712345678',
    );
    await tester.pump();
    expect(phoneField(tester).controller!.text, '712 345 678');
    expect(find.textContaining('+254'), findsOneWidget);

    await tester.tap(find.byKey(const Key('send-code-button')));
    await tester.pumpAndSettle();

    expect(auth.requestedPhoneNumbers, ['+254712345678']);
    expect(openedChallenge?.deliveryChannel, OtpDeliveryChannel.sms);
  });

  testWidgets('choosing Uganda changes the dial code and channel', (
    tester,
  ) async {
    await pumpLogin(tester);

    await chooseCountry(tester, 'UG');

    expect(dialCode(tester).data, '+256');
    expect(find.text('Code will be sent via WhatsApp'), findsOneWidget);

    // A pasted international number keeps only the subscriber part, so the
    // dial code is never shown twice.
    await tester.enterText(
      find.byKey(const Key('phone-number-field')),
      '+256701234567',
    );
    await tester.pump();
    expect(phoneField(tester).controller!.text, '701 234 567');
    expect(find.textContaining('+256'), findsOneWidget);

    await tester.tap(find.byKey(const Key('send-code-button')));
    await tester.pumpAndSettle();

    expect(auth.requestedPhoneNumbers, ['+256701234567']);
    expect(openedChallenge?.deliveryChannel, OtpDeliveryChannel.whatsapp);
  });

  testWidgets('Tanzania numbers are sent as E.164', (tester) async {
    await pumpLogin(tester);
    await chooseCountry(tester, 'TZ');

    await tester.enterText(
      find.byKey(const Key('phone-number-field')),
      '0712345678',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('send-code-button')));
    await tester.pumpAndSettle();

    expect(auth.requestedPhoneNumbers, ['+255712345678']);
  });

  testWidgets('a number invalid for the selected country is rejected', (
    tester,
  ) async {
    await pumpLogin(tester);
    await chooseCountry(tester, 'RW');

    // Valid in Kenya, but not a Rwandan mobile number.
    await tester.enterText(
      find.byKey(const Key('phone-number-field')),
      '0712345678',
    );
    await tester.pump();

    expect(
      find.text('Enter a valid mobile number for Rwanda.'),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const Key('send-code-button')));
    await tester.pump();
    expect(auth.requestedPhoneNumbers, isEmpty);
  });

  testWidgets('switching country re-reads the typed digits', (tester) async {
    await pumpLogin(tester);
    await tester.enterText(
      find.byKey(const Key('phone-number-field')),
      '0701234567',
    );
    await tester.pump();

    await chooseCountry(tester, 'UG');

    expect(phoneField(tester).controller!.text, '701 234 567');
    expect(find.text('Enter a valid mobile number for Uganda.'), findsNothing);
  });
}
