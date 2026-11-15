import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/presentation/member_formatting.dart';

/// How far back a payment can start, for a member who paid before being
/// recorded (matches the API).
const backdateLimitDays = 90;

/// How far ahead a payment can start: pay Friday, start Monday (matches the
/// API).
const futureStartLimitDays = 30;

/// "Starts today" by default; tap to pick a day within the limits.
class StartDateTile extends StatelessWidget {
  const StartDateTile({
    required this.today,
    required this.value,
    required this.onChanged,
    super.key,
  });

  /// The gym's local today, at midnight.
  final DateTime today;

  /// The chosen start, or null for today.
  final DateTime? value;
  final ValueChanged<DateTime> onChanged;

  Future<void> _pick(BuildContext context) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: value ?? today,
      firstDate: today.subtract(const Duration(days: backdateLimitDays)),
      lastDate: today.add(const Duration(days: futureStartLimitDays)),
      helpText: 'When does this membership start?',
    );
    if (picked != null) onChanged(picked);
  }

  @override
  Widget build(BuildContext context) {
    final day = value;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: const Icon(Icons.event, color: AppColors.primary),
      title: Text(
        day == null || day == today
            ? 'Starts today'
            : day.isAfter(today)
            ? 'Starts ${formatDay(day)}'
            : 'Started ${formatDay(day)}',
      ),
      subtitle: Text(
        'Paid earlier, or starting later? Pick the start date (up to '
        '$backdateLimitDays days back or $futureStartLimitDays days ahead).',
        style: AppTextStyles.bodySmall,
      ),
      onTap: () => _pick(context),
    );
  }
}
