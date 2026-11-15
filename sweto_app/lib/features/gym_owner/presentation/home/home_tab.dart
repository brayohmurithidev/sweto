import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/revenue_sparkline.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/member_formatting.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';

/// The verified gym's Home tab: today's numbers, revenue, quick actions and
/// what happened recently.
class HomeTab extends ConsumerStatefulWidget {
  const HomeTab({
    required this.gymId,
    required this.onLogout,
    this.now,
    super.key,
  });

  final String gymId;
  final VoidCallback onLogout;

  /// Overrides the clock in tests (greeting and "x mins ago").
  final DateTime Function()? now;

  @override
  ConsumerState<HomeTab> createState() => HomeTabState();
}

class HomeTabState extends ConsumerState<HomeTab> {
  DashboardSummary? _summary;
  String? _error;

  DateTime _now() => (widget.now ?? DateTime.now)();

  @override
  void initState() {
    super.initState();
    reload();
  }

  /// Fetches fresh numbers; the shell calls this when Home is shown again.
  Future<void> reload() async {
    try {
      final summary = await ref
          .read(membersRepositoryProvider)
          .getDashboard(widget.gymId);
      if (mounted) {
        setState(() {
          _summary = summary;
          _error = null;
        });
      }
    } catch (error) {
      if (mounted) setState(() => _error = memberErrorMessage(error));
    }
  }

  Future<void> _go(String routeName, {Map<String, String>? extra}) async {
    await context.pushNamed(
      routeName,
      pathParameters: {'gymId': widget.gymId, ...?extra},
    );
    if (mounted) reload();
  }

  @override
  Widget build(BuildContext context) {
    final summary = _summary;
    if (summary == null) {
      return Center(
        child: _error == null
            ? const CircularProgressIndicator(color: AppColors.primary)
            : Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(_error!, key: const Key('home-error')),
                  const SizedBox(height: AppSpacing.sm),
                  OutlinedButton(onPressed: reload, child: const Text('Retry')),
                ],
              ),
      );
    }
    return RefreshIndicator(
      color: AppColors.primary,
      onRefresh: reload,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
        children: [
          _header(summary),
          const SizedBox(height: AppSpacing.lg),
          Row(
            children: [
              Expanded(
                child: _Stat(
                  key: const Key('home-active-members'),
                  icon: Icons.people_outline,
                  value: summary.activeMembers,
                  label: 'Active members',
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _Stat(
                  key: const Key('home-expiring-members'),
                  icon: Icons.hourglass_bottom,
                  value: summary.expiringMembers,
                  label: 'Expiring in 7 days',
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _Stat(
                  key: const Key('home-check-ins'),
                  icon: Icons.qr_code_scanner,
                  value: summary.checkInsToday,
                  label: 'Check-ins today',
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          _revenueCard(summary),
          const SizedBox(height: AppSpacing.lg),
          Text('Quick actions', style: AppTextStyles.titleLarge),
          const SizedBox(height: AppSpacing.xs),
          Row(
            children: [
              Expanded(
                child: _Action(
                  key: const Key('home-scan'),
                  icon: Icons.qr_code_scanner,
                  label: 'Scan QR',
                  onTap: () => _go(AppRoutes.checkInName),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _Action(
                  key: const Key('home-add-member'),
                  icon: Icons.person_add_alt_1,
                  label: 'Add member',
                  onTap: () => _go(AppRoutes.addMemberName),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          Text('Recent activity', style: AppTextStyles.titleLarge),
          const SizedBox(height: AppSpacing.xs),
          if (summary.recentActivity.isEmpty)
            Text(
              'Nothing yet. Add a member or check someone in to get started.',
              style: AppTextStyles.bodySmall,
            )
          else
            for (final item in summary.recentActivity) _activityRow(item),
        ],
      ),
    );
  }

  Widget _header(DashboardSummary summary) {
    final hour = _now().hour;
    final part = hour < 12
        ? 'Good morning'
        : hour < 17
        ? 'Good afternoon'
        : 'Good evening';
    final name = summary.ownerFirstName;
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                name == null ? '$part 👋' : '$part, $name 👋',
                key: const Key('home-greeting'),
                style: AppTextStyles.headingMedium,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 2),
              Text(
                summary.gymName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTextStyles.bodyMedium,
              ),
            ],
          ),
        ),
        IconButton(
          key: const Key('home-logout'),
          tooltip: 'Log out',
          onPressed: widget.onLogout,
          icon: const Icon(
            Icons.logout_rounded,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _revenueCard(DashboardSummary summary) {
    final change = summary.revenueChangePercent;
    final up = change != null && change >= 0;
    return Container(
      key: const Key('home-revenue'),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Revenue this month', style: AppTextStyles.bodySmall),
                const SizedBox(height: 4),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Text(
                    formatMoney(summary.revenueThisMonth, summary.currency),
                    style: AppTextStyles.headingLarge,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  change == null
                      ? 'Nothing last month to compare with'
                      : '${up ? '↑' : '↓'} '
                            '${change.abs().toStringAsFixed(1)}% vs last month',
                  key: const Key('home-revenue-change'),
                  style: AppTextStyles.caption.copyWith(
                    color: change == null
                        ? AppColors.textMuted
                        : up
                        ? AppColors.secondary
                        : AppColors.error,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          SizedBox(
            width: 120,
            child: RevenueSparkline(daily: summary.dailyRevenue),
          ),
        ],
      ),
    );
  }

  Widget _activityRow(ActivityItem item) {
    final (icon, color) = switch (item.kind) {
      'check_in' when item.ok => (Icons.check_circle, AppColors.secondary),
      'check_in' => (Icons.block, AppColors.error),
      'payment' => (Icons.payments_outlined, AppColors.primary),
      _ => (Icons.person_add_alt_1, AppColors.textSecondary),
    };
    final memberId = item.memberId;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, color: color),
      title: Text(
        item.memberName ?? 'Unknown code',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        item.detail,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: AppTextStyles.bodySmall,
      ),
      trailing: Text(_ago(item.at), style: AppTextStyles.caption),
      onTap: memberId == null
          ? null
          : () =>
                _go(AppRoutes.memberDetailName, extra: {'memberId': memberId}),
    );
  }

  String _ago(DateTime at) {
    final minutes = _now().difference(at).inMinutes;
    if (minutes < 1) return 'just now';
    if (minutes < 60) return '$minutes min ago';
    final hours = minutes ~/ 60;
    if (hours < 24) return '$hours h ago';
    return formatDay(at);
  }
}

class _Stat extends StatelessWidget {
  const _Stat({
    required this.icon,
    required this.value,
    required this.label,
    super.key,
  });

  final IconData icon;
  final int value;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadius.md),
      border: Border.all(color: AppColors.border),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: AppColors.primary, size: 22),
        const SizedBox(height: 8),
        Text('$value', style: AppTextStyles.headingMedium),
        Text(
          label,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: AppTextStyles.caption,
        ),
      ],
    ),
  );
}

class _Action extends StatelessWidget {
  const _Action({
    required this.icon,
    required this.label,
    required this.onTap,
    super.key,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: AppColors.surface,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(AppRadius.md),
      side: const BorderSide(color: AppColors.border),
    ),
    clipBehavior: Clip.antiAlias,
    child: InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 14),
        child: Column(
          children: [
            Icon(icon, color: AppColors.primary),
            const SizedBox(height: 6),
            Text(label, style: AppTextStyles.labelMedium),
          ],
        ),
      ),
    ),
  );
}
