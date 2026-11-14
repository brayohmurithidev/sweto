import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';

const _months = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

/// "13 Dec 2026"
String formatDay(DateTime day) =>
    '${day.day} ${_months[day.month - 1]} ${day.year}';

/// "KES 5,000"
String formatMoney(num amount, String currency) {
  final whole = amount.round().toString();
  final grouped = whole.replaceAllMapped(
    RegExp(r'\B(?=(\d{3})+(?!\d))'),
    (_) => ',',
  );
  return '$currency $grouped';
}

/// [compact] drops "Paid" so the list badge never needs to truncate.
String standingLabel(GymMember member, {bool compact = false}) {
  final until = member.paidUntil;
  return switch (member.standing) {
    MemberStanding.active =>
      '${compact ? 'Until' : 'Paid until'} ${formatDay(until!)}',
    MemberStanding.expiring => 'Ends ${formatDay(until!)}',
    MemberStanding.expired => 'Expired ${formatDay(until!)}',
    MemberStanding.noMembership => 'Never paid',
  };
}

Color standingColor(MemberStanding standing) => switch (standing) {
  MemberStanding.active => AppColors.secondary,
  MemberStanding.expiring => AppColors.warning,
  MemberStanding.expired => AppColors.error,
  MemberStanding.noMembership => AppColors.textMuted,
};

class StandingBadge extends StatelessWidget {
  const StandingBadge({required this.member, this.compact = false, super.key});

  final GymMember member;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final color = standingColor(member.standing);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .12),
        borderRadius: BorderRadius.circular(AppRadius.pill),
        border: Border.all(color: color.withValues(alpha: .5)),
      ),
      child: Text(
        standingLabel(member, compact: compact),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: AppTextStyles.caption.copyWith(color: color),
      ),
    );
  }
}
