import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/member_formatting.dart';

/// One line of the gym's activity: who, what, by whom and when.
class ActivityRow extends StatelessWidget {
  const ActivityRow({
    required this.item,
    required this.now,
    this.onTap,
    this.showBy = true,
    super.key,
  });

  final ActivityItem item;
  final DateTime now;
  final VoidCallback? onTap;

  /// Off in a list that already shows one person's activity.
  final bool showBy;

  @override
  Widget build(BuildContext context) {
    final (icon, color) = switch (item.kind) {
      'check_in' when item.ok => (Icons.check_circle, AppColors.secondary),
      'check_in' => (Icons.block, AppColors.error),
      'payment' => (Icons.payments_outlined, AppColors.primary),
      _ => (Icons.person_add_alt_1, AppColors.textSecondary),
    };
    final by = showBy ? item.byName : null;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, color: color),
      title: Text(
        item.memberName ?? 'Unknown code',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        by == null ? item.detail : '${item.detail} · by ${firstName(by)}',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: AppTextStyles.bodySmall,
      ),
      trailing: Text(ago(item.at, now), style: AppTextStyles.caption),
      onTap: onTap,
    );
  }
}

/// "Wanjiku" from "Wanjiku Kamau".
String firstName(String fullName) {
  final parts = fullName.trim().split(RegExp(r'\s+'));
  return parts.isEmpty || parts.first.isEmpty ? fullName : parts.first;
}

/// "just now", "5 min ago", "3 h ago", else the day.
String ago(DateTime at, DateTime now) {
  final minutes = now.difference(at).inMinutes;
  if (minutes < 1) return 'just now';
  if (minutes < 60) return '$minutes min ago';
  final hours = minutes ~/ 60;
  if (hours < 24) return '$hours h ago';
  return formatDay(at);
}
