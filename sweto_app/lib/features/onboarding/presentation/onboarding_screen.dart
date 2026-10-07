import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/onboarding/data/onboarding_pages.dart';
import 'package:sweto_app/features/onboarding/domain/onboarding_page_data.dart';
import 'package:sweto_app/shared/widgets/app_bottom_panel.dart';
import 'package:sweto_app/shared/widgets/app_page_indicator.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';
import 'package:sweto_app/shared/widgets/onboarding_feature_icon.dart';
import 'package:sweto_app/features/onboarding/data/onboarding_storage.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  late final PageController _pageController;

  int _currentIndex = 0;
  bool _isChangingPage = false;
  bool _imagesPrecached = false;

  OnboardingPageData get _currentPage {
    return onboardingPages[_currentIndex];
  }

  bool get _isLastPage {
    return _currentIndex == onboardingPages.length - 1;
  }

  @override
  void initState() {
    super.initState();

    _pageController = PageController();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();

    if (_imagesPrecached) {
      return;
    }

    _imagesPrecached = true;

    for (final page in onboardingPages) {
      precacheImage(AssetImage(page.imagePath), context);
    }
  }

  void _onPageChanged(int index) {
    if (index == _currentIndex) {
      return;
    }

    setState(() {
      _currentIndex = index;
    });
  }

  Future<void> _handlePrimaryAction() async {
    if (_isChangingPage) {
      return;
    }

    if (_isLastPage) {
      _openPhoneLogin();
      return;
    }

    setState(() {
      _isChangingPage = true;
    });

    try {
      await _pageController.nextPage(
        duration: const Duration(milliseconds: 420),
        curve: Curves.easeInOutCubic,
      );
    } finally {
      if (mounted) {
        setState(() {
          _isChangingPage = false;
        });
      }
    }
  }

  Future<void> _openPhoneLogin() async {
    await OnboardingStorage().markCompleted();
    if (!mounted) return;
    context.goNamed(AppRoutes.phoneLoginName);
  }

  @override
  void dispose() {
    _pageController.dispose();

    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final mediaQuery = MediaQuery.of(context);
    final screenHeight = mediaQuery.size.height;
    final bottomInset = mediaQuery.padding.bottom;

    final isCompact = screenHeight < 720;

    final panelHeight = (screenHeight * (isCompact ? 0.46 : 0.42))
        .clamp(isCompact ? 310.0 : 350.0, 410.0)
        .toDouble();

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        fit: StackFit.expand,
        children: [
          _ImageCarousel(
            controller: _pageController,
            onPageChanged: _onPageChanged,
            panelHeight: panelHeight,
          ),

          _ImageGradient(panelHeight: panelHeight),

          _SkipButton(onPressed: _openPhoneLogin),

          Align(
            alignment: Alignment.bottomCenter,
            child: SizedBox(
              height: panelHeight,
              width: double.infinity,
              child: AppBottomPanel(
                child: _BottomSheetContent(
                  page: _currentPage,
                  currentIndex: _currentIndex,
                  isLastPage: _isLastPage,
                  isCompact: isCompact,
                  bottomInset: bottomInset,
                  isChangingPage: _isChangingPage,
                  onPrimaryPressed: _handlePrimaryAction,
                  onLoginPressed: _openPhoneLogin,
                ),
              ),
            ),
          ),

          Positioned(
            left: 0,
            right: 0,
            bottom: panelHeight - 35,
            child: IgnorePointer(
              child: _AnimatedFeatureIcon(page: _currentPage),
            ),
          ),
        ],
      ),
    );
  }
}

class _ImageCarousel extends StatelessWidget {
  const _ImageCarousel({
    required this.controller,
    required this.onPageChanged,
    required this.panelHeight,
  });

  final PageController controller;
  final ValueChanged<int> onPageChanged;
  final double panelHeight;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: panelHeight - 70),
      child: PageView.builder(
        key: const Key('onboarding-page-view'),
        controller: controller,
        itemCount: onboardingPages.length,
        physics: const ClampingScrollPhysics(),
        onPageChanged: onPageChanged,
        itemBuilder: (context, index) {
          final page = onboardingPages[index];

          return _CarouselImage(imagePath: page.imagePath);
        },
      ),
    );
  }
}

class _CarouselImage extends StatelessWidget {
  const _CarouselImage({required this.imagePath});

  final String imagePath;

  @override
  Widget build(BuildContext context) {
    return Hero(
      tag: imagePath,
      child: Image.asset(
        imagePath,
        fit: BoxFit.cover,
        alignment: Alignment.topCenter,
        filterQuality: FilterQuality.high,
        errorBuilder: (context, error, stackTrace) {
          return const ColoredBox(
            color: AppColors.surface,
            child: Center(
              child: Icon(
                Icons.broken_image_outlined,
                size: 52,
                color: AppColors.textMuted,
              ),
            ),
          );
        },
      ),
    );
  }
}

class _ImageGradient extends StatelessWidget {
  const _ImageGradient({required this.panelHeight});

  final double panelHeight;

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      bottom: panelHeight - 70,
      child: const IgnorePointer(
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Color(0x33000000),
                Color(0x00000000),
                Color(0x11000000),
                Color(0xB3050505),
              ],
              stops: [0, 0.35, 0.68, 1],
            ),
          ),
        ),
      ),
    );
  }
}

class _BottomSheetContent extends StatelessWidget {
  const _BottomSheetContent({
    required this.page,
    required this.currentIndex,
    required this.isLastPage,
    required this.isCompact,
    required this.bottomInset,
    required this.isChangingPage,
    required this.onPrimaryPressed,
    required this.onLoginPressed,
  });

  final OnboardingPageData page;
  final int currentIndex;
  final bool isLastPage;
  final bool isCompact;
  final double bottomInset;
  final bool isChangingPage;
  final VoidCallback onPrimaryPressed;
  final VoidCallback onLoginPressed;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        AppSpacing.md,
        isCompact ? 48 : 58,
        AppSpacing.md,
        bottomInset > 0 ? bottomInset + 8 : 16,
      ),
      child: Column(
        children: [
          SizedBox(
            height: isCompact ? 58 : 66,
            child: ClipRect(
              child: _FadeSlideContent(
                contentKey: page.title,
                child: Text(
                  page.title,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: AppTextStyles.headingMedium.copyWith(
                    color: AppColors.white,
                    fontWeight: FontWeight.w800,
                    height: 1.12,
                  ),
                ),
              ),
            ),
          ),

          SizedBox(height: isCompact ? 4 : AppSpacing.xs),

          SizedBox(
            height: isCompact ? 60 : 68,
            child: ClipRect(
              child: _FadeSlideContent(
                contentKey: page.description,
                verticalOffset: 0.04,
                child: Text(
                  page.description,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                    height: 1.4,
                  ),
                ),
              ),
            ),
          ),

          const Spacer(),

          AppPageIndicator(
            count: onboardingPages.length,
            currentIndex: currentIndex,
          ),

          SizedBox(height: isCompact ? 12 : AppSpacing.md),

          AppPrimaryButton(
            key: const Key('onboarding-primary-button'),
            label: page.buttonLabel,
            onPressed: isChangingPage ? null : onPrimaryPressed,
          ),

          SizedBox(height: isCompact ? 6 : AppSpacing.xs),

          SizedBox(
            height: 30,
            child: AnimatedOpacity(
              duration: const Duration(milliseconds: 180),
              opacity: isLastPage ? 1 : 0,
              child: IgnorePointer(
                ignoring: !isLastPage,
                child: TextButton(
                  key: const Key('onboarding-login-button'),
                  onPressed: onLoginPressed,
                  style: TextButton.styleFrom(
                    padding: EdgeInsets.zero,
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    foregroundColor: AppColors.white,
                  ),
                  child: Text(
                    'I already have an account',
                    style: AppTextStyles.caption.copyWith(
                      color: AppColors.white,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FadeSlideContent extends StatelessWidget {
  const _FadeSlideContent({
    required this.contentKey,
    required this.child,
    this.verticalOffset = 0.08,
  });

  final Object contentKey;
  final Widget child;
  final double verticalOffset;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 240),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      layoutBuilder: (Widget? currentChild, List<Widget> previousChildren) {
        return Stack(
          alignment: Alignment.center,
          children: [...previousChildren, ?currentChild],
        );
      },
      transitionBuilder: (child, animation) {
        final fade = CurvedAnimation(parent: animation, curve: Curves.easeOut);

        final slide =
            Tween<Offset>(
              begin: Offset(0, verticalOffset),
              end: Offset.zero,
            ).animate(
              CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
            );

        return FadeTransition(
          opacity: fade,
          child: SlideTransition(position: slide, child: child),
        );
      },
      child: KeyedSubtree(key: ValueKey<Object>(contentKey), child: child),
    );
  }
}

class _AnimatedFeatureIcon extends StatelessWidget {
  const _AnimatedFeatureIcon({required this.page});

  final OnboardingPageData page;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 220),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      transitionBuilder: (child, animation) {
        return FadeTransition(
          opacity: animation,
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.92, end: 1).animate(animation),
            child: child,
          ),
        );
      },
      child: OnboardingFeatureIcon(
        key: ValueKey<IconData>(page.icon),
        icon: page.icon,
      ),
    );
  }
}

class _SkipButton extends StatelessWidget {
  const _SkipButton({required this.onPressed});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Align(
        alignment: Alignment.topRight,
        child: Padding(
          padding: const EdgeInsets.only(
            top: AppSpacing.xs,
            right: AppSpacing.sm,
          ),
          child: TextButton(
            key: const Key('onboarding-skip'),
            onPressed: onPressed,
            style: TextButton.styleFrom(
              foregroundColor: AppColors.white,
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm,
                vertical: AppSpacing.xs,
              ),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Skip'),
                SizedBox(width: 4),
                Icon(Icons.arrow_forward_rounded, size: 17),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
