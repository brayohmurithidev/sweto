import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sweto_app/app/app.dart';
import 'package:sweto_app/core/config/app_config.dart';
import 'package:sweto_app/core/config/app_environment.dart';
import 'package:sweto_app/core/config/config_providers.dart';
import 'package:sweto_app/core/router/app_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/auth/presentation/otp_verification_screen.dart';
import 'package:sweto_app/features/auth/presentation/phone_login_screen.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_repository.dart';
import 'package:sweto_app/features/gym_owner/presentation/gym_owner_dashboard.dart';
import 'package:sweto_app/features/gym_owner/presentation/gym_owner_screens.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';

import 'support/fake_auth_repository.dart';
import 'support/fake_otp_delivery_repository.dart';

/// End-to-end session lifecycle through the real router, splash, sign-in
/// screens and session controller, with the network replaced by fakes.
void main() {
  late ProviderContainer container;

  setUp(() {
    // The intro has been seen, so signed-out users land on phone sign-in.
    SharedPreferences.setMockInitialValues({'onboarding_completed': true});
  });

  Future<void> pumpApp(WidgetTester tester, FakeAuthRepository auth) async {
    container = ProviderContainer(
      overrides: [
        appConfigProvider.overrideWithValue(
          const AppConfig(
            environment: AppEnvironment.local,
            apiBaseUrl: 'http://localhost:8000',
          ),
        ),
        authRepositoryProvider.overrideWithValue(auth),
        otpDeliveryRepositoryProvider.overrideWithValue(
          FakeOtpDeliveryRepository(),
        ),
        gymOwnerRepositoryProvider.overrideWithValue(_DashboardGyms()),
      ],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(container: container, child: const SwetoApp()),
    );
    // Splash animation, then session restore and routing.
    await tester.pump(const Duration(milliseconds: 2700));
    await _settle(tester);
  }

  Future<void> go(WidgetTester tester, String path) async {
    container.read(appRouterProvider).go(path);
    await _settle(tester);
  }

  SessionState session() => container.read(sessionControllerProvider);

  group('signed out', () {
    testWidgets('fresh launch lands on phone sign-in', (tester) async {
      await pumpApp(tester, FakeAuthRepository());

      expect(find.byType(PhoneLoginScreen), findsOneWidget);
      expect(session().status, SessionStatus.unauthenticated);
      expect(find.byKey(const Key('session-expired-message')), findsNothing);
    });

    testWidgets('authenticated routes redirect to sign-in', (tester) async {
      await pumpApp(tester, FakeAuthRepository());

      for (final path in [
        AppRoutes.homePath,
        AppRoutes.accountTypePath,
        AppRoutes.verificationPendingPath,
      ]) {
        await go(tester, path);
        expect(find.byType(PhoneLoginScreen), findsOneWidget, reason: path);
        expect(find.byType(GymOwnerDashboardScreen), findsNothing);
      }
    });

    testWidgets('sign-in completes and enters the app', (tester) async {
      final auth = FakeAuthRepository();
      await pumpApp(tester, auth);

      await _signInThroughOtp(tester);

      expect(session().status, SessionStatus.authenticated);
      expect(auth.accessToken, FakeAuthRepository.issuedTokens.accessToken);
      expect(find.byType(AccountTypeScreen), findsOneWidget);
    });
  });

  group('signed in', () {
    testWidgets('restart with a valid session skips sign-in', (tester) async {
      final auth = FakeAuthRepository(refreshToken: 'stored-refresh');
      await pumpApp(tester, auth);

      expect(session().status, SessionStatus.authenticated);
      expect(auth.refreshCount, 1);
      expect(find.byType(AccountTypeScreen), findsOneWidget);
    });

    testWidgets('authenticated routes are reachable', (tester) async {
      await pumpApp(tester, FakeAuthRepository(refreshToken: 'stored-refresh'));

      await go(tester, AppRoutes.homePath);

      expect(find.byType(GymOwnerDashboardScreen), findsOneWidget);
    });

    testWidgets('sign-in screens are skipped', (tester) async {
      await pumpApp(tester, FakeAuthRepository(refreshToken: 'stored-refresh'));

      for (final path in [
        AppRoutes.phoneLoginPath,
        AppRoutes.onboardingPath,
      ]) {
        await go(tester, path);
        expect(find.byType(PhoneLoginScreen), findsNothing, reason: path);
        expect(find.byType(AccountTypeScreen), findsOneWidget, reason: path);
      }
    });
  });

  group('expired session', () {
    testWidgets('a session rejected at startup shows the expiry message', (
      tester,
    ) async {
      final auth = FakeAuthRepository(refreshToken: 'revoked-refresh')
        ..refreshError = rejectedRefresh();
      await pumpApp(tester, auth);

      expect(find.byType(PhoneLoginScreen), findsOneWidget);
      expect(find.text(sessionExpiredMessage), findsOneWidget);
      expect(auth.refreshToken, isNull);
    });

    testWidgets(
      'expiry during use clears the session, returns to sign-in and allows '
      'signing in again',
      (tester) async {
        final auth = FakeAuthRepository(refreshToken: 'stored-refresh');
        await pumpApp(tester, auth);
        await go(tester, AppRoutes.homePath);
        expect(find.byType(GymOwnerDashboardScreen), findsOneWidget);

        // What the token refresh interceptor does when the server rejects
        // the refresh token.
        await container.read(sessionControllerProvider.notifier).expire();
        await _settle(tester);

        expect(session().status, SessionStatus.unauthenticated);
        expect(auth.refreshToken, isNull);
        expect(find.byType(GymOwnerDashboardScreen), findsNothing);
        expect(find.byType(PhoneLoginScreen), findsOneWidget);
        expect(find.text(sessionExpiredMessage), findsOneWidget);

        await go(tester, AppRoutes.homePath);
        expect(find.byType(PhoneLoginScreen), findsOneWidget);

        await _signInThroughOtp(tester);

        expect(session().status, SessionStatus.authenticated);
        expect(session().endReason, isNull);
        expect(find.byType(AccountTypeScreen), findsOneWidget);
      },
    );
  });

  group('logout', () {
    testWidgets('dashboard logout revokes, clears and returns to sign-in', (
      tester,
    ) async {
      final auth = FakeAuthRepository(refreshToken: 'stored-refresh');
      await pumpApp(tester, auth);
      await go(tester, AppRoutes.homePath);

      await tester.tap(find.byKey(const Key('dashboard-logout')));
      await _settle(tester);
      await tester.tap(find.widgetWithText(FilledButton, 'Log out'));
      await _settle(tester);

      expect(auth.revokedRefreshTokens, [
        FakeAuthRepository.issuedTokens.refreshToken,
      ]);
      expect(auth.refreshToken, isNull);
      expect(session().endReason, SessionEndReason.loggedOut);
      expect(find.byType(PhoneLoginScreen), findsOneWidget);
      expect(find.text(sessionExpiredMessage), findsNothing);

      await go(tester, AppRoutes.homePath);
      expect(find.byType(PhoneLoginScreen), findsOneWidget);
      expect(find.byType(GymOwnerDashboardScreen), findsNothing);
    });

    testWidgets('a failed server logout still signs the user out', (
      tester,
    ) async {
      final auth = FakeAuthRepository(refreshToken: 'stored-refresh')
        ..logoutError = unreachableRefresh();
      await pumpApp(tester, auth);
      await go(tester, AppRoutes.verificationPendingPath);

      await tester.tap(find.byKey(const Key('verification-pending-logout')));
      await _settle(tester);

      expect(auth.revokedRefreshTokens, hasLength(1));
      expect(auth.refreshToken, isNull);
      expect(session().status, SessionStatus.unauthenticated);
      expect(find.byType(PhoneLoginScreen), findsOneWidget);

      await go(tester, AppRoutes.verificationPendingPath);
      expect(find.byType(PhoneLoginScreen), findsOneWidget);
    });
  });
}

/// Pumps frames without waiting for endless animations (splash particles,
/// progress indicators) to stop.
Future<void> _settle(WidgetTester tester) async {
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

Future<void> _signInThroughOtp(WidgetTester tester) async {
  await tester.enterText(
    find.byKey(const Key('phone-number-field')),
    '712345678',
  );
  await tester.pump();
  await tester.tap(find.byKey(const Key('send-code-button')));
  await _settle(tester);
  expect(find.byType(OtpVerificationScreen), findsOneWidget);

  await tester.enterText(find.byKey(const Key('otp-hidden-input')), '123456');
  await _settle(tester);
}

/// Only what the dashboard reads is implemented; anything else throws.
class _DashboardGyms extends Fake implements GymOwnerRepository {
  @override
  Future<Gym> getCurrentGym() async => const Gym(id: 'gym-id', name: 'FlexFit');

  @override
  Future<GymOnboarding> getGymOnboarding(String gymId) async => GymOnboarding(
    gymId: gymId,
    nextStep: GymOnboardingStep.waitingForVerification,
    completed: false,
    verificationStatus: GymVerificationStatus.pending,
  );

  @override
  Future<GymVerificationData> getGymVerification(String gymId) async =>
      const GymVerificationData(
        status: 'pending',
        requiredTypes: [],
        missingTypes: [],
        documents: [],
      );
}
