import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';

/// Routes anyone can open, signed in or not.
const publicRoutePaths = {
  AppRoutes.splashPath,
  AppRoutes.onboardingPath,
  AppRoutes.phoneLoginPath,
  AppRoutes.otpPath,
  AppRoutes.healthPath,
};

/// Sign-in routes a signed-in user should skip.
const signInRoutePaths = {
  AppRoutes.onboardingPath,
  AppRoutes.phoneLoginPath,
  AppRoutes.otpPath,
};

/// The single access rule for every route, driven by the session state.
///
/// Returns the path to redirect to, or null to allow [path].
///
/// - Unknown (cold start): only public routes; anything else goes to the
///   splash screen, which restores the session and then routes onwards.
/// - Signed out: only public routes; anything else goes to phone sign-in.
/// - Signed in: sign-in routes go to the splash screen, which resolves the
///   right place from the server's onboarding state; all others are allowed.
String? sessionRedirect(SessionStatus status, String path) {
  final isPublic = publicRoutePaths.contains(path);
  return switch (status) {
    SessionStatus.unknown => isPublic ? null : AppRoutes.splashPath,
    SessionStatus.unauthenticated => isPublic ? null : AppRoutes.phoneLoginPath,
    SessionStatus.authenticated =>
      signInRoutePaths.contains(path) ? AppRoutes.splashPath : null,
  };
}
