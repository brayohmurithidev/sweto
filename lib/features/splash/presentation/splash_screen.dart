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
import 'package:sweto_app/shared/widgets/sweto_logo.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
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

  @override
  void initState() {
    super.initState();

    _progressController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2400),
    )..forward();

    _navigationTimer = Timer(const Duration(milliseconds: 2600), _bootstrap);
  }

  Future<void> _bootstrap() async {
    if (!mounted) {
      return;
    }
    final onboarding = await ref.read(authBootstrapProvider.future);
    if (!mounted) return;
    if (onboarding != null) {
      final destination = await ref
          .read(onboardingCoordinatorProvider)
          .resolveAccount(onboarding);
      if (!mounted) return;
      goToDestination(context, destination);
      return;
    }
    final completed = await OnboardingStorage().isCompleted();
    if (!mounted) return;
    context.goNamed(
      completed ? AppRoutes.phoneLoginName : AppRoutes.onboardingName,
    );
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
