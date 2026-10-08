import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/router/session_redirect.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';

void main() {
  const authenticatedPaths = [
    AppRoutes.homePath,
    AppRoutes.accountTypePath,
    AppRoutes.gymRegistrationPath,
    AppRoutes.gymLocationPath,
    AppRoutes.gymVerificationPath,
    AppRoutes.verificationPendingPath,
    AppRoutes.profileCompletionPath,
  ];

  group('signed out', () {
    test('authenticated routes redirect to phone sign-in', () {
      for (final path in authenticatedPaths) {
        expect(
          sessionRedirect(SessionStatus.unauthenticated, path),
          AppRoutes.phoneLoginPath,
          reason: path,
        );
      }
    });

    test('unknown routes are treated as authenticated routes', () {
      expect(
        sessionRedirect(SessionStatus.unauthenticated, '/anything-else'),
        AppRoutes.phoneLoginPath,
      );
    });

    test('splash, intro, phone sign-in and OTP stay reachable', () {
      for (final path in [
        AppRoutes.splashPath,
        AppRoutes.onboardingPath,
        AppRoutes.phoneLoginPath,
        AppRoutes.otpPath,
      ]) {
        expect(
          sessionRedirect(SessionStatus.unauthenticated, path),
          isNull,
          reason: path,
        );
      }
    });
  });

  group('signed in', () {
    test('authenticated routes are allowed', () {
      for (final path in authenticatedPaths) {
        expect(
          sessionRedirect(SessionStatus.authenticated, path),
          isNull,
          reason: path,
        );
      }
    });

    test('sign-in screens are skipped via the splash resolver', () {
      for (final path in [
        AppRoutes.onboardingPath,
        AppRoutes.phoneLoginPath,
        AppRoutes.otpPath,
      ]) {
        expect(
          sessionRedirect(SessionStatus.authenticated, path),
          AppRoutes.splashPath,
          reason: path,
        );
      }
    });

    test('splash stays reachable so it can resolve the destination', () {
      expect(
        sessionRedirect(SessionStatus.authenticated, AppRoutes.splashPath),
        isNull,
      );
    });
  });

  group('session not yet restored', () {
    test('authenticated routes wait on the splash screen', () {
      for (final path in authenticatedPaths) {
        expect(
          sessionRedirect(SessionStatus.unknown, path),
          AppRoutes.splashPath,
          reason: path,
        );
      }
    });

    test('public routes are allowed', () {
      expect(sessionRedirect(SessionStatus.unknown, AppRoutes.splashPath), isNull);
      expect(
        sessionRedirect(SessionStatus.unknown, AppRoutes.phoneLoginPath),
        isNull,
      );
    });
  });
}
