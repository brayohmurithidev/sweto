import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/config/config_providers.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/router/session_redirect.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';
import 'package:sweto_app/features/auth/presentation/phone_login_screen.dart';
import 'package:sweto_app/features/auth/presentation/otp_verification_screen.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/health/presentation/health_check_screen.dart';
import 'package:sweto_app/features/onboarding/presentation/onboarding_screen.dart';
import 'package:sweto_app/features/splash/presentation/splash_screen.dart';
import 'package:sweto_app/features/gym_owner/presentation/gym_owner_screens.dart';
import 'package:sweto_app/features/gym_owner/presentation/gym_owner_dashboard.dart';

CustomTransitionPage<void> _onboardingPage(GoRouterState state, Widget child) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionDuration: const Duration(milliseconds: 240),
      reverseTransitionDuration: const Duration(milliseconds: 220),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        final offset = Tween<Offset>(
          begin: const Offset(0.08, 0),
          end: Offset.zero,
        ).chain(CurveTween(curve: Curves.easeOutCubic)).animate(animation);
        return FadeTransition(
          opacity: animation,
          child: SlideTransition(position: offset, child: child),
        );
      },
    );

final appRouterProvider = Provider<GoRouter>((ref) {
  // Mirrors the session status so GoRouter re-runs [sessionRedirect] whenever
  // the user signs in, logs out or their session expires.
  final sessionStatus = ValueNotifier<SessionStatus>(
    ref.read(sessionControllerProvider).status,
  );
  ref.listen<SessionState>(
    sessionControllerProvider,
    (_, next) => sessionStatus.value = next.status,
  );

  final isProduction = ref.read(appConfigProvider).isProduction;

  final router = GoRouter(
    initialLocation: AppRoutes.splashPath,
    refreshListenable: sessionStatus,
    redirect: (context, state) =>
        sessionRedirect(sessionStatus.value, state.uri.path),
    routes: [
      GoRoute(
        path: AppRoutes.accountTypePath,
        name: AppRoutes.accountTypeName,
        pageBuilder: (context, state) =>
            _onboardingPage(state, const AccountTypeScreen()),
      ),
      GoRoute(
        path: AppRoutes.gymRegistrationPath,
        name: AppRoutes.gymRegistrationName,
        pageBuilder: (context, state) =>
            _onboardingPage(state, const GymRegistrationScreen()),
      ),
      GoRoute(
        path: AppRoutes.gymLocationPath,
        name: AppRoutes.gymLocationName,
        pageBuilder: (context, state) =>
            _onboardingPage(state, const GymLocationScreen()),
      ),
      GoRoute(
        path: AppRoutes.gymBusinessDetailsPath,
        name: AppRoutes.gymBusinessDetailsName,
        pageBuilder: (context, state) =>
            _onboardingPage(state, const GymBusinessDetailsScreen()),
      ),
      GoRoute(
        path: AppRoutes.gymAmenitiesPath,
        name: AppRoutes.gymAmenitiesName,
        pageBuilder: (context, state) =>
            _onboardingPage(state, const GymAmenitiesScreen()),
      ),
      GoRoute(
        path: AppRoutes.gymOperatingHoursPath,
        name: AppRoutes.gymOperatingHoursName,
        pageBuilder: (context, state) =>
            _onboardingPage(state, const GymOperatingHoursScreen()),
      ),
      GoRoute(
        path: AppRoutes.gymPricingPath,
        name: AppRoutes.gymPricingName,
        pageBuilder: (context, state) =>
            _onboardingPage(state, const GymPricingScreen()),
      ),
      GoRoute(
        path: AppRoutes.memberComingSoonPath,
        name: AppRoutes.memberComingSoonName,
        builder: (context, state) => SimpleOnboardingPlaceholder(
          key: const Key('member-coming-soon-screen'),
          title: 'Coming soon',
          message: 'Member onboarding is not available in this MVP.',
          actionLabel: 'Choose account type',
          action: () => context.goNamed(AppRoutes.accountTypeName),
        ),
      ),
      GoRoute(
        path: AppRoutes.verificationPendingPath,
        name: AppRoutes.verificationPendingName,
        builder: (context, state) => const VerificationPendingScreen(),
      ),
      GoRoute(
        path: AppRoutes.gymVerificationPath,
        name: AppRoutes.gymVerificationName,
        pageBuilder: (context, state) =>
            _onboardingPage(state, const GymVerificationSetupScreen()),
      ),
      GoRoute(
        path: AppRoutes.unsupportedOnboardingPath,
        name: AppRoutes.unsupportedOnboardingName,
        builder: (context, state) => const UnsupportedOnboardingScreen(),
      ),
      GoRoute(
        path: AppRoutes.splashPath,
        name: AppRoutes.splashName,
        builder: (context, state) {
          return const SplashScreen();
        },
      ),
      GoRoute(
        path: AppRoutes.otpPath,
        name: AppRoutes.otpName,
        builder: (context, state) {
          final challenge = state.extra;
          if (challenge is! OtpChallenge) return const PhoneLoginScreen();
          return OtpVerificationScreen(challenge: challenge);
        },
      ),
      GoRoute(
        path: AppRoutes.homePath,
        name: AppRoutes.homeName,
        pageBuilder: (context, state) =>
            _onboardingPage(state, const GymOwnerDashboardScreen()),
      ),
      GoRoute(
        path: AppRoutes.profileCompletionPath,
        name: AppRoutes.profileCompletionName,
        builder: (context, state) =>
            const _AuthenticatedPlaceholder(title: 'Complete your profile'),
      ),
      GoRoute(
        path: AppRoutes.onboardingPath,
        name: AppRoutes.onboardingName,
        builder: (context, state) {
          return const OnboardingScreen();
        },
      ),
      GoRoute(
        path: AppRoutes.phoneLoginPath,
        name: AppRoutes.phoneLoginName,
        builder: (context, state) {
          return const PhoneLoginScreen();
        },
      ),
      // Developer diagnostics; not shipped in production builds.
      if (!isProduction)
        GoRoute(
          path: AppRoutes.healthPath,
          name: AppRoutes.healthName,
          builder: (context, state) {
            return const HealthCheckScreen();
          },
        ),
    ],
  );

  ref.onDispose(() {
    router.dispose();
    sessionStatus.dispose();
  });

  return router;
});

class _AuthenticatedPlaceholder extends StatelessWidget {
  const _AuthenticatedPlaceholder({required this.title});
  final String title;
  @override
  Widget build(BuildContext context) =>
      Scaffold(body: Center(child: Text(title)));
}
