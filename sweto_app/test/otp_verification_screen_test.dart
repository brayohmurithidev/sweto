import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/core/network/api_exception.dart';
import 'package:sweto_app/features/auth/domain/repositories/auth_repository.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/auth/presentation/otp_verification_screen.dart';

import 'support/fake_otp_delivery_repository.dart';

void main() {
  Future<FakeOtpDeliveryRepository> pumpWhatsAppOtp(
    WidgetTester tester,
    OtpDeliveryStatus status,
  ) async {
    final delivery = FakeOtpDeliveryRepository(status: status);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authRepositoryProvider.overrideWithValue(_AuthFake()),
          otpDeliveryRepositoryProvider.overrideWithValue(delivery),
        ],
        child: MaterialApp(
          home: OtpVerificationScreen(
            challenge: OtpChallenge(
              challengeId: 'whatsapp-challenge',
              phoneNumber: '+256701234567',
              expiresAt: DateTime.now().add(const Duration(minutes: 5)),
              resendAvailableAt: DateTime.now().add(const Duration(minutes: 1)),
              deliveryChannel: OtpDeliveryChannel.whatsapp,
            ),
          ),
        ),
      ),
    );
    return delivery;
  }

  testWidgets('a failed WhatsApp delivery is explained and resend opens', (
    tester,
  ) async {
    final delivery = await pumpWhatsAppOtp(tester, OtpDeliveryStatus.failed);
    expect(find.byKey(const Key('otp-delivery-failed')), findsNothing);
    expect(find.text('Resend code'), findsNothing);

    await tester.pump(const Duration(seconds: 4));
    await tester.pump();

    expect(delivery.checkedChallengeIds, ['whatsapp-challenge']);
    expect(find.byKey(const Key('otp-delivery-failed')), findsOneWidget);
    expect(find.text('Resend code'), findsOneWidget);

    // A final answer stops the checks.
    await tester.pump(const Duration(seconds: 8));
    expect(delivery.checkedChallengeIds, hasLength(1));
  });

  testWidgets('a delivered WhatsApp code shows no warning', (tester) async {
    final delivery = await pumpWhatsAppOtp(
      tester,
      OtpDeliveryStatus.delivered,
    );

    await tester.pump(const Duration(seconds: 4));
    await tester.pump();

    expect(delivery.checkedChallengeIds, hasLength(1));
    expect(find.byKey(const Key('otp-delivery-failed')), findsNothing);
    expect(find.text('Resend code'), findsNothing);
  });

  testWidgets('SMS codes are not checked for delivery', (tester) async {
    final delivery = FakeOtpDeliveryRepository();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authRepositoryProvider.overrideWithValue(_AuthFake()),
          otpDeliveryRepositoryProvider.overrideWithValue(delivery),
        ],
        child: MaterialApp(
          home: OtpVerificationScreen(
            challenge: OtpChallenge(
              challengeId: 'sms-challenge',
              phoneNumber: '+254712345678',
              expiresAt: DateTime.now().add(const Duration(minutes: 5)),
              resendAvailableAt: DateTime.now().add(const Duration(minutes: 1)),
            ),
          ),
        ),
      ),
    );

    await tester.pump(const Duration(seconds: 8));

    expect(delivery.checkedChallengeIds, isEmpty);
  });

  for (final (channel, title) in [
    (OtpDeliveryChannel.sms, 'Check your SMS'),
    (OtpDeliveryChannel.whatsapp, 'Check WhatsApp'),
  ]) {
    testWidgets('tells the user where to find a ${channel.name} code', (
      tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authRepositoryProvider.overrideWithValue(_AuthFake()),
            otpDeliveryRepositoryProvider.overrideWithValue(
              FakeOtpDeliveryRepository(),
            ),
          ],
          child: MaterialApp(
            home: OtpVerificationScreen(
              challenge: OtpChallenge(
                challengeId: 'challenge',
                phoneNumber: '+256701234567',
                expiresAt: DateTime.now().add(const Duration(minutes: 5)),
                resendAvailableAt: DateTime.now().add(
                  const Duration(minutes: 1),
                ),
                deliveryChannel: channel,
              ),
            ),
          ),
        ),
      );

      expect(find.text(title), findsOneWidget);
      expect(find.text('+256701234567'), findsOneWidget);
    });
  }

  testWidgets('renders six responsive OTP boxes without overflow', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(800, 600));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authRepositoryProvider.overrideWithValue(_AuthFake())],
        child: MaterialApp(
          home: OtpVerificationScreen(
            challenge: OtpChallenge(
              challengeId: 'challenge',
              phoneNumber: '+254712345678',
              expiresAt: DateTime.now().add(const Duration(minutes: 5)),
              resendAvailableAt: DateTime.now().subtract(
                const Duration(seconds: 1),
              ),
            ),
          ),
        ),
      ),
    );

    for (var index = 0; index < 6; index++) {
      expect(find.byKey(Key('otp-digit-box-$index')), findsOneWidget);
    }
    expect(find.text('Resend code'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('resend updates the mounted challenge and verification uses it', (
    tester,
  ) async {
    final auth = _AuthFake();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authRepositoryProvider.overrideWithValue(auth)],
        child: MaterialApp(
          home: OtpVerificationScreen(
            challenge: OtpChallenge(
              challengeId: 'old-challenge',
              phoneNumber: '+254112345678',
              expiresAt: DateTime.now().add(const Duration(minutes: 5)),
              resendAvailableAt: DateTime.now().subtract(
                const Duration(seconds: 1),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.enterText(find.byKey(const Key('otp-hidden-input')), '123');
    await tester.tap(find.byKey(const Key('resend-otp-button')));
    await tester.pump();

    expect(auth.requestedPhone, '+254112345678');
    expect(find.byType(OtpVerificationScreen), findsOneWidget);
    expect(find.text('1'), findsNothing);
    expect(find.textContaining('Resend code in 00:'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('otp-hidden-input')), '654321');
    await tester.pump();

    expect(auth.verifiedChallengeId, 'new-challenge');
  });

  testWidgets(
    'invalid OTP shakes, shows red boxes, then clears and refocuses',
    (tester) async {
      final auth = _AuthFake()..throwInvalidOtp = true;
      await tester.binding.setSurfaceSize(const Size(800, 600));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        ProviderScope(
          overrides: [authRepositoryProvider.overrideWithValue(auth)],
          child: MaterialApp(
            home: OtpVerificationScreen(
              challenge: OtpChallenge(
                challengeId: 'challenge',
                phoneNumber: '+254712345678',
                expiresAt: DateTime.now().add(const Duration(minutes: 5)),
                resendAvailableAt: DateTime.now().add(
                  const Duration(minutes: 1),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.enterText(
        find.byKey(const Key('otp-hidden-input')),
        '123456',
      );
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('The verification code is incorrect.'), findsOneWidget);
      final box = tester.widget<Container>(
        find.byKey(const Key('otp-digit-box-0')),
      );
      final decoration = box.decoration! as BoxDecoration;
      expect((decoration.border! as Border).top.color, Colors.redAccent);
      expect(find.byType(Transform), findsWidgets);

      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 1));
      final field = tester.widget<TextField>(
        find.byKey(const Key('otp-hidden-input')),
      );
      expect(field.controller!.text, isEmpty);
      expect(field.focusNode!.hasFocus, isTrue);

      await tester.enterText(find.byKey(const Key('otp-hidden-input')), '1');
      await tester.pump();
      final updatedBox = tester.widget<Container>(
        find.byKey(const Key('otp-digit-box-0')),
      );
      final updatedDecoration = updatedBox.decoration! as BoxDecoration;
      expect(
        (updatedDecoration.border! as Border).top.color,
        isNot(Colors.redAccent),
      );
      expect(tester.takeException(), isNull);
    },
  );
}

class _AuthFake implements AuthRepository {
  String? requestedPhone;
  String? verifiedChallengeId;
  bool throwInvalidOtp = false;
  @override
  Future<void> clearTokens() async {}
  @override
  Future<AccountOnboarding> getOnboarding() async => const AccountOnboarding(
    roles: [AccountRole.gymOwner],
    defaultRole: AccountRole.gymOwner,
    status: AccountOnboardingStatus.completed,
    completed: true,
    nextStep: 'dashboard',
  );
  @override
  Future<AuthUser> getMe() async =>
      const AuthUser(id: 'user', mustChangePassword: false);
  @override
  Future<String?> readRefreshToken() async => null;
  @override
  Future<AccountOnboarding> selectGymOwnerRole() => throw UnimplementedError();
  @override
  Future<AuthTokens> refresh(String refreshToken) => throw UnimplementedError();
  @override
  Future<void> logout(String refreshToken) async {}
  @override
  Future<OtpChallenge> requestOtp(String phoneNumber) async {
    requestedPhone = phoneNumber;
    return OtpChallenge(
      challengeId: 'new-challenge',
      phoneNumber: phoneNumber,
      expiresAt: DateTime.now().add(const Duration(minutes: 5)),
      resendAvailableAt: DateTime.now().add(const Duration(seconds: 60)),
    );
  }

  @override
  Future<void> saveTokens(AuthTokens tokens) async {}
  @override
  Future<AuthTokens> verifyOtp({
    required String challengeId,
    required String code,
  }) async {
    verifiedChallengeId = challengeId;
    if (throwInvalidOtp) {
      throw DioException(
        requestOptions: RequestOptions(path: '/api/v1/auth/verify-otp'),
        error: const ApiException(
          message: 'The verification code is incorrect.',
          statusCode: 422,
          code: 'INVALID_OTP',
        ),
      );
    }
    return Completer<AuthTokens>().future;
  }
}
