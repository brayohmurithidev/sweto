import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/auth/utils/kenya_phone_formatter.dart';

class KenyaPhoneField extends StatelessWidget {
  const KenyaPhoneField({
    required this.controller,
    required this.focusNode,
    required this.onChanged,
    this.errorText,
    this.enabled = true,
    super.key,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final ValueChanged<String> onChanged;
  final String? errorText;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return TextField(
      key: const Key('phone-number-field'),
      controller: controller,
      focusNode: focusNode,
      enabled: enabled,
      keyboardType: TextInputType.phone,
      textInputAction: TextInputAction.done,
      autofillHints: const [AutofillHints.telephoneNumber],
      inputFormatters: const <TextInputFormatter>[KenyaPhoneFormatter()],
      onChanged: onChanged,
      style: AppTextStyles.bodyLarge.copyWith(
        color: AppColors.white,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.3,
      ),
      decoration: InputDecoration(
        hintText: '712 345 678',
        errorText: errorText,
        counterText: '',
        filled: true,
        fillColor: AppColors.surface,
        prefixIconConstraints: const BoxConstraints(minWidth: 104),
        prefixIcon: const _KenyaCountryPrefix(),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: 18,
        ),
        hintStyle: AppTextStyles.bodyLarge.copyWith(
          color: AppColors.textMuted,
          fontWeight: FontWeight.w500,
        ),
        errorStyle: AppTextStyles.bodySmall.copyWith(color: Colors.redAccent),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        disabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          borderSide: const BorderSide(color: Colors.redAccent),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          borderSide: const BorderSide(color: Colors.redAccent, width: 1.5),
        ),
      ),
    );
  }
}

class _KenyaCountryPrefix extends StatelessWidget {
  const _KenyaCountryPrefix();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: AppSpacing.md, right: AppSpacing.sm),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('🇰🇪', style: TextStyle(fontSize: 22)),
          const SizedBox(width: AppSpacing.xs),
          Text(
            '+254',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Container(width: 1, height: 24, color: AppColors.border),
        ],
      ),
    );
  }
}
