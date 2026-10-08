import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sweto_app/core/phone/phone_country.dart';
import 'package:sweto_app/core/phone/phone_number.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';

/// Phone input shown as `[flag] [+dial code] | [subscriber number]`.
///
/// The dial code lives only in the country selector; the text field holds
/// the grouped subscriber number. Use [PhoneNumbers.toE164] with [country]
/// to get the value to send.
class PhoneNumberField extends StatelessWidget {
  const PhoneNumberField({
    required this.country,
    required this.onCountryChanged,
    required this.controller,
    required this.focusNode,
    required this.onChanged,
    this.countries = supportedPhoneCountries,
    this.errorText,
    this.enabled = true,
    this.fieldKey,
    this.compact = false,
    super.key,
  });

  final PhoneCountry country;
  final ValueChanged<PhoneCountry> onCountryChanged;
  final TextEditingController controller;
  final FocusNode focusNode;
  final ValueChanged<String> onChanged;
  final List<PhoneCountry> countries;
  final String? errorText;
  final bool enabled;
  final Key? fieldKey;
  final bool compact;

  Future<void> _chooseCountry(BuildContext context) async {
    final selected = await showModalBottomSheet<PhoneCountry>(
      context: context,
      backgroundColor: AppColors.surfaceElevated,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) =>
          _CountrySheet(selected: country, countries: countries),
    );
    if (selected == null || selected == country) return;
    // Re-read what was typed for the new country, so the field never keeps
    // digits (or a dial code) that belong to the previous one.
    final text = PhoneNumbers.format(selected, controller.text);
    controller.value = TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: text.length),
    );
    onCountryChanged(selected);
    onChanged(text);
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      key: fieldKey ?? const Key('phone-number-field'),
      controller: controller,
      focusNode: focusNode,
      enabled: enabled,
      keyboardType: TextInputType.phone,
      textInputAction: TextInputAction.done,
      autofillHints: const [AutofillHints.telephoneNumberNational],
      inputFormatters: <TextInputFormatter>[SubscriberNumberFormatter(country)],
      onChanged: onChanged,
      style: AppTextStyles.bodyLarge.copyWith(
        color: AppColors.white,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.3,
      ),
      decoration: InputDecoration(
        hintText: country.example,
        errorText: errorText,
        counterText: '',
        filled: true,
        fillColor: AppColors.surface,
        prefixIconConstraints: const BoxConstraints(minWidth: 104),
        prefixIcon: _CountryButton(
          country: country,
          onPressed: enabled ? () => _chooseCountry(context) : null,
        ),
        contentPadding: EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: compact ? 11 : 18,
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

class _CountryButton extends StatelessWidget {
  const _CountryButton({required this.country, required this.onPressed});

  final PhoneCountry country;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      enabled: onPressed != null,
      onTap: onPressed,
      label: 'Country: ${country.name}, ${country.displayDialCode}. '
          'Change country',
      excludeSemantics: true,
      child: InkWell(
        key: const Key('phone-country-button'),
        onTap: onPressed,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        child: Padding(
          padding: const EdgeInsets.only(
            left: AppSpacing.md,
            right: AppSpacing.sm,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(country.flag, style: const TextStyle(fontSize: 22)),
              const SizedBox(width: AppSpacing.xs),
              Text(
                country.displayDialCode,
                key: const Key('phone-dial-code'),
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Icon(
                Icons.arrow_drop_down_rounded,
                color: AppColors.textSecondary,
                size: 20,
              ),
              const SizedBox(width: AppSpacing.xs),
              Container(width: 1, height: 24, color: AppColors.border),
            ],
          ),
        ),
      ),
    );
  }
}

class _CountrySheet extends StatelessWidget {
  const _CountrySheet({required this.selected, required this.countries});

  final PhoneCountry selected;
  final List<PhoneCountry> countries;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.7,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.all(18),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'Select country',
                  style: AppTextStyles.headingMedium,
                ),
              ),
            ),
            Flexible(
              child: ListView(
                shrinkWrap: true,
                children: [
                  for (final country in countries)
                    ListTile(
                      key: Key('phone-country-${country.isoCode}'),
                      leading: Text(
                        country.flag,
                        style: const TextStyle(fontSize: 24),
                      ),
                      title: Text(country.name),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            country.displayDialCode,
                            style: AppTextStyles.bodyMedium.copyWith(
                              color: AppColors.textSecondary,
                            ),
                          ),
                          if (country == selected) ...[
                            const SizedBox(width: AppSpacing.sm),
                            const Icon(Icons.check, color: AppColors.secondary),
                          ],
                        ],
                      ),
                      selected: country == selected,
                      onTap: () => Navigator.pop(context, country),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}
