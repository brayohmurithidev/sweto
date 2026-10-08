import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/network/api_exception.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/core/phone/phone_country.dart';
import 'package:sweto_app/core/phone/phone_number.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/otp_channel_policy.dart';
import 'package:sweto_app/shared/widgets/phone_number_field.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';
import 'package:sweto_app/shared/widgets/sweto_logo.dart';

class PhoneLoginScreen extends ConsumerStatefulWidget {
  const PhoneLoginScreen({super.key});

  @override
  ConsumerState<PhoneLoginScreen> createState() => _PhoneLoginScreenState();
}

class _PhoneLoginScreenState extends ConsumerState<PhoneLoginScreen> {
  late final TextEditingController _phoneController;
  late final FocusNode _phoneFocusNode;

  PhoneCountry _country = kenya;
  bool _hasInteracted = false;
  bool _isSubmitting = false;
  String? _submissionError;

  bool get _isPhoneValid {
    return PhoneNumbers.isValid(_country, _phoneController.text);
  }

  String? get _phoneError {
    if (!_hasInteracted || _phoneController.text.isEmpty) {
      return null;
    }

    if (!_isPhoneValid) {
      return 'Enter a valid mobile number for ${_country.name}.';
    }

    return null;
  }

  @override
  void initState() {
    super.initState();

    _phoneController = TextEditingController();
    _phoneFocusNode = FocusNode();
  }

  void _onPhoneChanged(String value) {
    setState(() {
      _hasInteracted = true;
      _submissionError = null;
    });
  }

  void _onCountryChanged(PhoneCountry country) {
    setState(() {
      _country = country;
      _submissionError = null;
    });
  }

  Future<void> _sendCode() async {
    FocusScope.of(context).unfocus();

    setState(() {
      _hasInteracted = true;
    });

    if (!_isPhoneValid || _isSubmitting) {
      return;
    }

    final phoneNumber = PhoneNumbers.toE164(_country, _phoneController.text);

    setState(() {
      _isSubmitting = true;
    });

    try {
      final challenge = await ref
          .read(authRepositoryProvider)
          .requestOtp(phoneNumber);

      if (!mounted) {
        return;
      }

      ref.read(sessionControllerProvider.notifier).clearEndReason();
      context.pushNamed(AppRoutes.otpName, extra: challenge);
    } on DioException catch (error) {
      final apiError = error.error;
      if (mounted) {
        setState(
          () => _submissionError = apiError is ApiException
              ? apiError.message
              : 'Something went wrong. Please try again.',
        );
      }
    } on FormatException catch (error) {
      if (mounted) setState(() => _submissionError = error.message);
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  void _openTerms() {
    // Add the Terms route later.
  }

  void _openPrivacyPolicy() {
    // Add the Privacy Policy route later.
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _phoneFocusNode.dispose();

    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final sessionExpired =
        ref.watch(sessionControllerProvider).endReason ==
        SessionEndReason.expired;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () {
            FocusScope.of(context).unfocus();
          },
          child: LayoutBuilder(
            builder: (context, constraints) {
              return SingleChildScrollView(
                keyboardDismissBehavior:
                    ScrollViewKeyboardDismissBehavior.onDrag,
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: constraints.maxHeight),
                  child: IntrinsicHeight(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: AppSpacing.md),

                        const SizedBox(height: AppSpacing.xl),

                        const Center(child: SwetoLogo(width: 150)),

                        const SizedBox(height: AppSpacing.xl),

                        Text(
                          'Welcome to SWETO',
                          style: AppTextStyles.headingLarge.copyWith(
                            color: AppColors.white,
                            fontWeight: FontWeight.w800,
                            height: 1.12,
                          ),
                        ),

                        const SizedBox(height: AppSpacing.sm),

                        Text(
                          'Enter your phone number and we’ll send you '
                          'a verification code.',
                          style: AppTextStyles.bodyMedium.copyWith(
                            color: AppColors.textSecondary,
                            height: 1.5,
                          ),
                        ),

                        const SizedBox(height: AppSpacing.xl),

                        if (sessionExpired) ...[
                          const _SessionExpiredNotice(),
                          const SizedBox(height: AppSpacing.lg),
                        ],

                        Text(
                          'Phone number',
                          style: AppTextStyles.labelMedium.copyWith(
                            color: AppColors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),

                        const SizedBox(height: AppSpacing.xs),

                        PhoneNumberField(
                          country: _country,
                          onCountryChanged: _onCountryChanged,
                          controller: _phoneController,
                          focusNode: _phoneFocusNode,
                          errorText: _phoneError,
                          enabled: !_isSubmitting,
                          onChanged: _onPhoneChanged,
                        ),

                        const SizedBox(height: AppSpacing.xs),

                        _OtpChannelHint(channel: expectedOtpChannel(_country)),

                        if (_submissionError != null) ...[
                          const SizedBox(height: AppSpacing.sm),
                          Text(
                            _submissionError!,
                            key: const Key('phone-login-api-error'),
                            style: AppTextStyles.bodySmall.copyWith(
                              color: Colors.redAccent,
                            ),
                          ),
                        ],

                        const SizedBox(height: AppSpacing.md),

                        AppPrimaryButton(
                          key: const Key('send-code-button'),
                          label: _isSubmitting
                              ? 'Sending code...'
                              : 'Send Code',
                          onPressed: _isPhoneValid && !_isSubmitting
                              ? _sendCode
                              : null,
                        ),

                        const Spacer(),

                        Padding(
                          padding: const EdgeInsets.symmetric(
                            vertical: AppSpacing.lg,
                          ),
                          child: _TermsNotice(
                            onTermsPressed: _openTerms,
                            onPrivacyPressed: _openPrivacyPolicy,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

/// Tells the user where the code will arrive, which depends on the country.
class _OtpChannelHint extends StatelessWidget {
  const _OtpChannelHint({required this.channel});

  final OtpDeliveryChannel channel;

  @override
  Widget build(BuildContext context) {
    final whatsapp = channel == OtpDeliveryChannel.whatsapp;
    return Row(
      key: const Key('otp-channel-hint'),
      children: [
        Icon(
          whatsapp ? Icons.chat_outlined : Icons.sms_outlined,
          size: 16,
          color: AppColors.textMuted,
        ),
        const SizedBox(width: AppSpacing.xs),
        Flexible(
          child: Text(
            whatsapp
                ? 'Code will be sent via WhatsApp'
                : 'Code will be sent by SMS',
            style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted),
          ),
        ),
      ],
    );
  }
}

class _SessionExpiredNotice extends StatelessWidget {
  const _SessionExpiredNotice();

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Container(
        key: const Key('session-expired-message'),
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.sm),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          border: Border.all(color: AppColors.warning),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.lock_outline_rounded,
              color: AppColors.warning,
              size: 20,
            ),
            const SizedBox(width: AppSpacing.xs),
            Expanded(
              child: Text(
                sessionExpiredMessage,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TermsNotice extends StatelessWidget {
  const _TermsNotice({
    required this.onTermsPressed,
    required this.onPrivacyPressed,
  });

  final VoidCallback onTermsPressed;
  final VoidCallback onPrivacyPressed;

  @override
  Widget build(BuildContext context) {
    final normalStyle = AppTextStyles.bodySmall.copyWith(
      color: AppColors.textMuted,
      height: 1.5,
    );

    final linkStyle = normalStyle.copyWith(
      color: AppColors.white,
      fontWeight: FontWeight.w700,
      decoration: TextDecoration.underline,
      decorationColor: AppColors.white,
    );

    return Text.rich(
      TextSpan(
        style: normalStyle,
        children: [
          const TextSpan(text: 'By continuing, you agree to SWETO’s '),
          TextSpan(
            text: 'Terms of Service',
            style: linkStyle,
            recognizer: TapGestureRecognizer()..onTap = onTermsPressed,
          ),
          const TextSpan(text: ' and '),
          TextSpan(
            text: 'Privacy Policy',
            style: linkStyle,
            recognizer: TapGestureRecognizer()..onTap = onPrivacyPressed,
          ),
          const TextSpan(text: '.'),
        ],
      ),
      textAlign: TextAlign.center,
    );
  }
}
