import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/shared/widgets/orange_particles.dart';
import 'package:sweto_app/shared/widgets/sweto_loading_bar.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';
import 'package:sweto_app/shared/widgets/sweto_logo.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';
import 'package:sweto_app/features/onboarding/data/onboarding_storage.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';
import 'package:sweto_app/features/gym_owner/presentation/gym_owner_screens.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _progressController;

  Timer? _navigationTimer;
  bool _connectionFailed = false;

  @override
  void initState() {
    super.initState();

    _progressController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2400),
    )..forward();

    // A signed-in user arriving here (after verifying an OTP, or redirected
    // away from a sign-in screen) is routed straight away. A cold start shows
    // the full splash while the stored session is checked.
    final alreadySignedIn = ref
        .read(sessionControllerProvider)
        .isAuthenticated;
    _navigationTimer = Timer(
      alreadySignedIn ? Duration.zero : const Duration(milliseconds: 2600),
      _bootstrap,
    );
  }

  /// Decides where the app starts. The session controller owns the session;
  /// this screen only turns its state into a first destination.
  Future<void> _bootstrap() async {
    if (!mounted) return;
    if (_connectionFailed) setState(() => _connectionFailed = false);

    final session = ref.read(sessionControllerProvider.notifier);
    try {
      var status = ref.read(sessionControllerProvider).status;
      if (status == SessionStatus.unknown) {
        status = await session.restore();
      }
      if (!mounted) return;

      if (status == SessionStatus.authenticated) {
        final destination = await ref
            .read(onboardingCoordinatorProvider)
            .resolve();
        if (!mounted) return;
        goToDestination(context, destination);
        return;
      }

      await _goToSignedOutStart();
    } on SessionRestoreException {
      _showConnectionFailure();
    } catch (_) {
      // Network or server failure while resolving where to go next.
      if (!mounted) return;
      // The session may have expired while resolving the destination; the
      // controller has already been updated in that case.
      if (!ref.read(sessionControllerProvider).isAuthenticated) {
        await _goToSignedOutStart();
        return;
      }
      _showConnectionFailure();
    }
  }

  Future<void> _goToSignedOutStart() async {
    final expired =
        ref.read(sessionControllerProvider).endReason ==
        SessionEndReason.expired;
    final introSeen = expired || await OnboardingStorage().isCompleted();
    if (!mounted) return;
    context.goNamed(
      introSeen ? AppRoutes.phoneLoginName : AppRoutes.onboardingName,
    );
  }

  void _showConnectionFailure() {
    if (!mounted) return;
    setState(() => _connectionFailed = true);
  }

  @override
  void dispose() {
    _navigationTimer?.cancel();
    _progressController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        fit: StackFit.expand,
        children: [
          const ColoredBox(color: AppColors.background),
          const OrangeParticles(),
          const _SplashVignette(),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.xl,
                vertical: AppSpacing.lg,
              ),
              child: Column(
                children: [
                  const Spacer(flex: 5),
                  const SwetoLogo(width: 250),
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    'Karibu!',
                    style: AppTextStyles.headingMedium.copyWith(
                      color: AppColors.secondary,
                      fontStyle: FontStyle.italic,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const Spacer(flex: 4),
                  if (_connectionFailed) ...[
                    Text(
                      'We couldn’t reach SWETO. Check your connection and '
                      'try again.',
                      key: const Key('splash-connection-error'),
                      textAlign: TextAlign.center,
                      style: AppTextStyles.bodyMedium.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    AppPrimaryButton(
                      key: const Key('splash-retry'),
                      label: 'Try again',
                      onPressed: _bootstrap,
                    ),
                  ] else
                    AnimatedBuilder(
                      animation: _progressController,
                      builder: (context, child) {
                        return SwetoLoadingBar(
                          progress: Curves.easeInOut.transform(
                            _progressController.value,
                          ),
                        );
                      },
                    ),
                  const SizedBox(height: AppSpacing.xl),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SplashVignette extends StatelessWidget {
  const _SplashVignette();

  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(
        gradient: RadialGradient(
          center: Alignment.center,
          radius: 0.95,
          colors: [Colors.transparent, Color(0x99000000)],
          stops: [0.45, 1],
        ),
      ),
    );
  }
}
