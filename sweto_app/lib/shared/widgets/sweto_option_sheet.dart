import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';

/// One choice in a [showSwetoOptionSheet].
class SwetoOption<T> {
  const SwetoOption({
    required this.value,
    required this.label,
    this.detail,
    this.trailing,
    this.icon,
    this.enabled = true,
    this.key,
  });

  final T value;
  final String label;

  /// A second line under the label, such as "Required".
  final String? detail;

  /// Short text on the right, such as a price.
  final String? trailing;
  final IconData? icon;
  final bool enabled;
  final Key? key;
}

/// SWETO's picker: a rounded bottom sheet with a title and one row per
/// option, the selected one outlined and ticked. Returns the chosen value,
/// or null when dismissed.
Future<T?> showSwetoOptionSheet<T>(
  BuildContext context, {
  required String title,
  required List<SwetoOption<T>> options,
  T? selected,
  String? subtitle,
}) => showModalBottomSheet<T>(
  context: context,
  backgroundColor: AppColors.surfaceElevated,
  isScrollControlled: true,
  showDragHandle: true,
  shape: const RoundedRectangleBorder(
    borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
  ),
  builder: (context) => _OptionSheet<T>(
    title: title,
    subtitle: subtitle,
    options: options,
    selected: selected,
  ),
);

class _OptionSheet<T> extends StatelessWidget {
  const _OptionSheet({
    required this.title,
    required this.options,
    required this.selected,
    this.subtitle,
  });

  final String title;
  final String? subtitle;
  final List<SwetoOption<T>> options;
  final T? selected;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.75,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, AppSpacing.sm),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: AppTextStyles.headingMedium),
                  if (subtitle != null) ...[
                    const SizedBox(height: AppSpacing.xxs),
                    Text(subtitle!, style: AppTextStyles.bodySmall),
                  ],
                ],
              ),
            ),
            Flexible(
              child: ListView.separated(
                shrinkWrap: true,
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                itemCount: options.length,
                separatorBuilder: (_, _) => const SizedBox(height: 8),
                itemBuilder: (context, index) => _OptionRow<T>(
                  option: options[index],
                  selected: options[index].value == selected,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OptionRow<T> extends StatelessWidget {
  const _OptionRow({required this.option, required this.selected});

  final SwetoOption<T> option;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final enabled = option.enabled;
    final labelColor = enabled ? AppColors.textPrimary : AppColors.textMuted;
    return Material(
      color: selected
          ? AppColors.primary.withValues(alpha: 0.10)
          : AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        side: BorderSide(
          color: selected ? AppColors.primary : AppColors.border,
          width: selected ? 1.5 : 1,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        key: option.key,
        onTap: enabled ? () => Navigator.pop(context, option.value) : null,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              if (option.icon != null) ...[
                Icon(
                  option.icon,
                  color: enabled ? AppColors.primary : AppColors.textMuted,
                ),
                const SizedBox(width: AppSpacing.sm),
              ],
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      option.label,
                      style: AppTextStyles.bodyLarge.copyWith(
                        color: labelColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (option.detail != null) ...[
                      const SizedBox(height: 2),
                      Text(option.detail!, style: AppTextStyles.bodySmall),
                    ],
                  ],
                ),
              ),
              if (option.trailing != null) ...[
                const SizedBox(width: AppSpacing.sm),
                Text(
                  option.trailing!,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: enabled
                        ? AppColors.textSecondary
                        : AppColors.textMuted,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
              const SizedBox(width: AppSpacing.sm),
              Icon(
                selected
                    ? Icons.check_circle_rounded
                    : Icons.radio_button_unchecked_rounded,
                size: 22,
                color: selected ? AppColors.primary : AppColors.border,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A form field that opens a picker instead of a keyboard. It wears the same
/// decoration as the text fields around it, with a chevron.
class SwetoSelectField extends StatelessWidget {
  const SwetoSelectField({
    required this.label,
    required this.value,
    required this.onTap,
    this.hint,
    this.decoration,
    super.key,
  });

  final String label;

  /// The chosen value as shown, or null for none yet.
  final String? value;
  final String? hint;
  final VoidCallback? onTap;

  /// Matches a screen's own field style when given; the label is added.
  final InputDecoration? decoration;

  @override
  Widget build(BuildContext context) {
    final base = decoration ?? const InputDecoration();
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: InputDecorator(
        isEmpty: value == null,
        decoration: base.copyWith(
          labelText: label,
          hintText: hint,
          suffixIcon: const Icon(
            Icons.keyboard_arrow_down_rounded,
            color: AppColors.textSecondary,
          ),
        ),
        child: Text(
          value ?? '',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppTextStyles.bodyLarge.copyWith(color: AppColors.textPrimary),
        ),
      ),
    );
  }
}
