import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/onboarding/data/onboarding_pages.dart';
import 'package:sweto_app/features/onboarding/domain/onboarding_page_data.dart';
import 'package:sweto_app/shared/widgets/onboarding_icon.dart';
import 'package:sweto_app/shared/widgets/onboarding_page_indicator.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  late final PageController _pageController;

  int _currentPage = 0;

  bool get _isLastPage {
    return _currentPage == onboardingPages.length - 1;
  }

  @override
  void initState() {
    super.initState();

    _pageController = PageController();
  }

  void _handlePageChanged(int page) {
    setState(() {
      _currentPage = page;
    });
  }

  Future<void> _handlePrimaryAction() async {
    if (_isLastPage) {
      _openPhoneLogin();
      return;
    }

    await _pageController.nextPage(
      duration: const Duration(milliseconds: 350),
      curve: Curves.easeOutCubic,
    );
  }

  void _openPhoneLogin() {
    context.goNamed(AppRoutes.phoneLoginName);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        fit: StackFit.expand,
        children: [
          PageView.builder(
            controller: _pageController,
            itemCount: onboardingPages.length,
            onPageChanged: _handlePageChanged,
            itemBuilder: (context, index) {
              return _OnboardingPage(data: onboardingPages[index]);
            },
          ),
          SafeArea(
            child: Align(
              alignment: Alignment.topRight,
              child: Padding(
                padding: const EdgeInsets.only(
                  top: AppSpacing.sm,
                  right: AppSpacing.md,
                ),
                child: TextButton(
                  onPressed: _openPhoneLogin,
                  style: TextButton.styleFrom(
                    foregroundColor: AppColors.white,
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                      vertical: AppSpacing.xs,
                    ),
                  ),
                  child: const Text('Skip'),
                ),
              ),
            ),
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: _OnboardingBottomPanel(
              currentPage: _currentPage,
              isLastPage: _isLastPage,
              onPrimaryPressed: _handlePrimaryAction,
              onLoginPressed: _openPhoneLogin,
            ),
          ),
        ],
      ),
    );
  }
}

class _OnboardingPage extends StatelessWidget {
  const _OnboardingPage({required this.data});

  final OnboardingPageData data;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        Image.asset(
          data.imagePath,
          fit: BoxFit.cover,
          alignment: Alignment.topCenter,
          errorBuilder: (context, error, stackTrace) {
            return const ColoredBox(
              color: AppColors.surface,
              child: Center(
                child: Icon(
                  Icons.image_not_supported_outlined,
                  color: AppColors.textMuted,
                  size: 48,
                ),
              ),
            );
          },
        ),
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Color(0x22000000),
                Color(0x00000000),
                Color(0x66000000),
                Color(0xFF080808),
              ],
              stops: [0, 0.38, 0.63, 1],
            ),
          ),
        ),
      ],
    );
  }
}

class _OnboardingBottomPanel extends StatelessWidget {
  const _OnboardingBottomPanel({
    required this.currentPage,
    required this.isLastPage,
    required this.onPrimaryPressed,
    required this.onLoginPressed,
  });

  final int currentPage;
  final bool isLastPage;
  final VoidCallback onPrimaryPressed;
  final VoidCallback onLoginPressed;

  @override
  Widget build(BuildContext context) {
    final currentData = onboardingPages[currentPage];

    return SafeArea(
      top: false,
      child: Container(
        width: double.infinity,
        constraints: const BoxConstraints(minHeight: 285, maxHeight: 330),
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.md,
          0,
          AppSpacing.md,
          AppSpacing.sm,
        ),
        decoration: const BoxDecoration(
          color: Color(0xF5141414),
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(AppRadius.xl),
            topRight: Radius.circular(AppRadius.xl),
          ),
          border: Border(top: BorderSide(color: AppColors.border)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Transform.translate(
              offset: const Offset(0, -27),
              child: OnboardingIcon(icon: currentData.icon),
            ),
            Transform.translate(
              offset: const Offset(0, -17),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 250),
                    child: Text(
                      currentData.title,
                      key: ValueKey(currentData.title),
                      textAlign: TextAlign.center,
                      style: AppTextStyles.headingMedium.copyWith(
                        fontWeight: FontWeight.w800,
                        height: 1.15,
                      ),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 250),
                    child: Text(
                      currentData.description,
                      key: ValueKey(currentData.description),
                      textAlign: TextAlign.center,
                      style: AppTextStyles.bodyMedium.copyWith(
                        color: AppColors.textSecondary,
                        height: 1.45,
                      ),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  OnboardingPageIndicator(
                    pageCount: onboardingPages.length,
                    currentPage: currentPage,
                  ),
                  const SizedBox(height: AppSpacing.md),
                  FilledButton(
                    onPressed: onPrimaryPressed,
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(54),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.sm),
                      ),
                    ),
                    child: Text(isLastPage ? 'Get Started' : 'Next'),
                  ),
                  if (isLastPage) ...[
                    const SizedBox(height: AppSpacing.xs),
                    TextButton(
                      onPressed: onLoginPressed,
                      style: TextButton.styleFrom(
                        minimumSize: const Size.fromHeight(32),
                        padding: EdgeInsets.zero,
                      ),
                      child: const Text('I already have an account'),
                    ),
                  ] else
                    const SizedBox(height: 32),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
