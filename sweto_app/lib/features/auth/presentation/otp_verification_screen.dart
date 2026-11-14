import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/network/api_exception.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';
import 'package:sweto_app/shared/widgets/sweto_logo.dart';

class OtpVerificationScreen extends ConsumerStatefulWidget {
  const OtpVerificationScreen({required this.challenge, super.key});
  final OtpChallenge challenge;
  @override
  ConsumerState<OtpVerificationScreen> createState() =>
      _OtpVerificationScreenState();
}

class _OtpVerificationScreenState extends ConsumerState<OtpVerificationScreen>
    with SingleTickerProviderStateMixin {
  final _controller = TextEditingController();
  final _focus = FocusNode();
  bool _verifying = false;
  bool _resending = false;
  bool _hasOtpError = false;
  String? _error;
  late OtpChallenge _challenge;
  late DateTime _resendAt;
  Timer? _timer;
  Timer? _deliveryTimer;
  bool _checkingDelivery = false;
  OtpDeliveryStatus _delivery = OtpDeliveryStatus.accepted;
  late final AnimationController _shakeController;
  late final Animation<double> _shakeOffset;

  @override
  void initState() {
    super.initState();
    _challenge = widget.challenge;
    _resendAt = _challenge.resendAvailableAt.toLocal();
    _focus.addListener(_onFocusChanged);
    _shakeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _shakeOffset = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0, end: -8), weight: 1),
      TweenSequenceItem(tween: Tween(begin: -8, end: 8), weight: 2),
      TweenSequenceItem(tween: Tween(begin: 8, end: -6), weight: 2),
      TweenSequenceItem(tween: Tween(begin: -6, end: 6), weight: 2),
      TweenSequenceItem(tween: Tween(begin: 6, end: 0), weight: 1),
    ]).animate(CurvedAnimation(parent: _shakeController, curve: Curves.linear));
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
    _watchDelivery();
  }

  /// Waits between delivery checks: quick at first, when a failure is
  /// most likely, then backing off to 30 seconds.
  static const _deliveryCheckDelays = [
    Duration(seconds: 4),
    Duration(seconds: 4),
    Duration(seconds: 8),
    Duration(seconds: 15),
    Duration(seconds: 30),
  ];
  int _deliveryChecks = 0;

  /// WhatsApp tells the API later whether the code arrived. Check until a
  /// final answer, so a failed delivery is shown instead of a silent wait.
  void _watchDelivery() {
    _deliveryTimer?.cancel();
    _deliveryChecks = 0;
    _delivery = OtpDeliveryStatus.accepted;
    if (_challenge.deliveryChannel != OtpDeliveryChannel.whatsapp) return;
    _scheduleDeliveryCheck();
  }

  void _scheduleDeliveryCheck() {
    final delay = _deliveryCheckDelays[_deliveryChecks
        .clamp(0, _deliveryCheckDelays.length - 1)
        .toInt()];
    _deliveryTimer = Timer(delay, _checkDelivery);
  }

  Future<void> _checkDelivery() async {
    if (_checkingDelivery || !mounted) return;
    final challengeId = _challenge.challengeId;
    if (DateTime.now().isAfter(_challenge.expiresAt)) return;
    _checkingDelivery = true;
    _deliveryChecks++;
    var keepChecking = true;
    try {
      final status = await ref
          .read(otpDeliveryRepositoryProvider)
          .getDeliveryStatus(challengeId);
      if (!mounted || challengeId != _challenge.challengeId) return;
      keepChecking = !status.isFinal;
      setState(() {
        _delivery = status;
        // The code never arrived, so a new one can be requested at once.
        if (status == OtpDeliveryStatus.failed) _resendAt = DateTime.now();
      });
    } catch (_) {
      // A network hiccup; the next check tries again.
    } finally {
      _checkingDelivery = false;
      if (mounted && keepChecking && challengeId == _challenge.challengeId) {
        _scheduleDeliveryCheck();
      }
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _deliveryTimer?.cancel();
    _shakeController.dispose();
    _focus.removeListener(_onFocusChanged);
    _controller.dispose();
    _focus.dispose();
    super.dispose();
  }

  void _onFocusChanged() {
    if (mounted) setState(() {});
  }

  int get _seconds =>
      _resendAt.difference(DateTime.now()).inSeconds.clamp(0, 9999);
  String get _resendLabel {
    final minutes = _seconds ~/ 60;
    final seconds = _seconds % 60;
    return 'Resend code in ${minutes.toString().padLeft(2, '0')}:'
        '${seconds.toString().padLeft(2, '0')}';
  }

  void _changed(String value) {
    final digits = value.replaceAll(RegExp(r'\D'), '');
    if (digits != value) {
      _controller.value = TextEditingValue(
        text: digits,
        selection: TextSelection.collapsed(offset: digits.length),
      );
    }
    setState(() {
      _error = null;
      _hasOtpError = false;
    });
    if (digits.length == 6) _verify();
  }

  Future<void> _verify() async {
    if (_verifying || _controller.text.length != 6) return;
    FocusScope.of(context).unfocus();
    setState(() => _verifying = true);
    try {
      final tokens = await ref
          .read(authRepositoryProvider)
          .verifyOtp(challengeId: _challenge.challengeId, code: _controller.text);
      // Starting the session is all this screen does. The router then leaves
      // the sign-in flow and the splash screen resolves the destination.
      await ref.read(sessionControllerProvider.notifier).signIn(tokens);
    } on DioException catch (e) {
      final apiError = e.error;
      await _showVerificationError(
        message: apiError is ApiException
            ? apiError.message
            : 'Something went wrong. Please try again.',
        shouldShakeAndClear:
            apiError is ApiException && apiError.code == 'INVALID_OTP',
      );
    } on FormatException catch (e) {
      await _showVerificationError(
        message: e.message,
        shouldShakeAndClear: false,
      );
    } finally {
      if (mounted) setState(() => _verifying = false);
    }
  }

  Future<void> _showVerificationError({
    required String message,
    required bool shouldShakeAndClear,
  }) async {
    if (!mounted) return;
    setState(() {
      _error = message;
      _hasOtpError = true;
    });
    if (!shouldShakeAndClear) return;

    await _shakeController.forward(from: 0);
    if (!mounted) return;
    setState(_controller.clear);
    _focus.requestFocus();
  }

  Future<void> _resend() async {
    if (_seconds > 0 || _verifying || _resending) return;
    setState(() => _resending = true);
    try {
      final challenge = await ref
          .read(authRepositoryProvider)
          .requestOtp(_challenge.phoneNumber);
      if (!mounted) return;
      setState(() {
        _challenge = challenge;
        _resendAt = challenge.resendAvailableAt.toLocal();
        _controller.clear();
        _error = null;
        _hasOtpError = false;
        _delivery = OtpDeliveryStatus.accepted;
      });
      _watchDelivery();
    } on DioException catch (e) {
      final apiError = e.error;
      if (mounted) {
        final retryAfter = _retryAfterSeconds(apiError);
        setState(() {
          _error = apiError is ApiException
              ? apiError.message
              : 'Something went wrong. Please try again.';
          if (retryAfter != null) {
            _resendAt = DateTime.now().add(Duration(seconds: retryAfter));
          }
        });
      }
    } finally {
      if (mounted) setState(() => _resending = false);
    }
  }

  int? _retryAfterSeconds(Object? error) {
    if (error is! ApiException) {
      return null;
    }
    final details = error.details;
    if (details is! Map<Object?, Object?>) {
      return null;
    }
    final value = details['retry_after_seconds'];
    return value is int ? value : int.tryParse('$value');
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: AppColors.background,
    body: SafeArea(
      child: LayoutBuilder(
        builder: (context, constraints) => SingleChildScrollView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: EdgeInsets.fromLTRB(
            AppSpacing.md,
            AppSpacing.sm,
            AppSpacing.md,
            MediaQuery.viewInsetsOf(context).bottom + AppSpacing.lg,
          ),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Column(
              children: [
                Stack(
                  alignment: Alignment.center,
                  children: [
                    Align(
                      alignment: Alignment.centerLeft,
                      child: IconButton(
                        key: const Key('otp-change-phone'),
                        onPressed: () =>
                            context.goNamed(AppRoutes.phoneLoginName),
                        icon: const Icon(Icons.arrow_back_rounded),
                        color: AppColors.white,
                        iconSize: 20,
                      ),
                    ),
                    const SwetoLogo(width: 112),
                  ],
                ),
                const SizedBox(height: AppSpacing.xl),
                Text(
                  _challenge.deliveryChannel == OtpDeliveryChannel.whatsapp
                      ? 'Check WhatsApp'
                      : 'Check your SMS',
                  textAlign: TextAlign.center,
                  style: AppTextStyles.headingLarge.copyWith(
                    color: AppColors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  'We sent a 6-digit code to',
                  textAlign: TextAlign.center,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _challenge.phoneNumber,
                  textAlign: TextAlign.center,
                  style: AppTextStyles.bodyLarge.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: AppSpacing.xl),
                AnimatedBuilder(
                  animation: _shakeOffset,
                  builder: (context, child) => Transform.translate(
                    offset: Offset(_shakeOffset.value, 0),
                    child: child,
                  ),
                  child: _OtpDigitBoxes(
                    value: _controller.text,
                    focused: _focus.hasFocus,
                    hasError: _hasOtpError,
                    onTap: _focus.requestFocus,
                  ),
                ),
                Opacity(
                  opacity: 0,
                  child: SizedBox(
                    height: 1,
                    width: 1,
                    child: TextField(
                      key: const Key('otp-hidden-input'),
                      controller: _controller,
                      focusNode: _focus,
                      autofocus: true,
                      keyboardType: TextInputType.number,
                      autofillHints: const [AutofillHints.oneTimeCode],
                      inputFormatters: [
                        FilteringTextInputFormatter.digitsOnly,
                        LengthLimitingTextInputFormatter(6),
                      ],
                      onChanged: _changed,
                    ),
                  ),
                ),
                if (_delivery == OtpDeliveryStatus.failed) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Semantics(
                    liveRegion: true,
                    child: Text(
                      'We couldn’t deliver your code on WhatsApp. Check that '
                      'this number uses WhatsApp, then send a new code or '
                      'go back and use a different number.',
                      key: const Key('otp-delivery-failed'),
                      textAlign: TextAlign.center,
                      style: AppTextStyles.bodySmall.copyWith(
                        color: Colors.redAccent,
                      ),
                    ),
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    _error!,
                    key: const Key('otp-verification-error'),
                    textAlign: TextAlign.center,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: Colors.redAccent,
                    ),
                  ),
                ],
                const SizedBox(height: AppSpacing.md),
                TextButton(
                  key: const Key('resend-otp-button'),
                  onPressed: _seconds == 0 && !_verifying && !_resending
                      ? _resend
                      : null,
                  child: Text(
                    _resending
                        ? 'Sending code...'
                        : _seconds == 0
                        ? 'Resend code'
                        : _resendLabel,
                    style: AppTextStyles.bodyMedium.copyWith(
                      color: _seconds == 0
                          ? AppColors.primary
                          : AppColors.textMuted,
                      fontWeight: _seconds == 0
                          ? FontWeight.w700
                          : FontWeight.w500,
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
                AppPrimaryButton(
                  key: const Key('verify-otp-button'),
                  label: _verifying ? 'Verifying...' : 'Verify',
                  onPressed: _controller.text.length == 6 && !_verifying
                      ? _verify
                      : null,
                ),
                const SizedBox(height: AppSpacing.md),
                Text(
                  'We’ll verify automatically\nonce code is entered',
                  textAlign: TextAlign.center,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textMuted,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

class _OtpDigitBoxes extends StatelessWidget {
  const _OtpDigitBoxes({
    required this.value,
    required this.focused,
    required this.hasError,
    required this.onTap,
  });

  final String value;
  final bool focused;
  final bool hasError;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      const gap = 8.0;
      final boxSize = ((constraints.maxWidth - (gap * 5)) / 6)
          .clamp(40.0, 54.0)
          .toDouble();
      final activeIndex = value.length.clamp(0, 5);
      return GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(6, (index) {
            final active = focused && index == activeIndex;
            final digit = index < value.length ? value[index] : '';
            return Padding(
              padding: EdgeInsets.only(right: index == 5 ? 0 : gap),
              child: Container(
                key: Key('otp-digit-box-$index'),
                width: boxSize,
                height: boxSize,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: hasError
                        ? Colors.redAccent
                        : active
                        ? AppColors.primary
                        : AppColors.border,
                    width: hasError || active ? 2 : 1,
                  ),
                ),
                child: Text(
                  digit,
                  style: AppTextStyles.headingMedium.copyWith(
                    color: AppColors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            );
          }),
        ),
      );
    },
  );
}
