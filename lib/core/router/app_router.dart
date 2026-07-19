import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/auth/presentation/phone_login_screen.dart';
import 'package:sweto_app/features/health/presentation/health_check_screen.dart';
import 'package:sweto_app/features/onboarding/presentation/onboarding_screen.dart';
import 'package:sweto_app/features/splash/presentation/splash_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: AppRoutes.splashPath,
    routes: [
      GoRoute(
        path: AppRoutes.splashPath,
        name: AppRoutes.splashName,
        builder: (context, state) {
          return const SplashScreen();
        },
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
      GoRoute(
        path: AppRoutes.healthPath,
        name: AppRoutes.healthName,
        builder: (context, state) {
          return const HealthCheckScreen();
        },
      ),
    ],
  );
});
