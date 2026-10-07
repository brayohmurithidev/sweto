import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';
import 'package:sweto_app/shared/widgets/sweto_snackbar.dart';

class GymOwnerDashboardScreen extends ConsumerStatefulWidget {
  const GymOwnerDashboardScreen({super.key});
  @override
  ConsumerState<GymOwnerDashboardScreen> createState() => _DashboardState();
}

class _DashboardState extends ConsumerState<GymOwnerDashboardScreen> {
  Gym? _gym;
  GymOnboarding? _onboarding;
  GymVerificationData? _verification;
  bool _loading = true;
  bool _refreshing = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool refresh = false}) async {
    if (_refreshing) return;
    setState(() {
      _refreshing = refresh;
      if (!refresh) _loading = true;
    });
    try {
      final repo = ref.read(gymOwnerRepositoryProvider);
      final gym = await repo.getCurrentGym();
      final onboarding = await repo.getGymOnboarding(gym.id);
      final verification = await repo.getGymVerification(gym.id);
      if (!mounted) return;
      setState(() {
        _gym = gym;
        _onboarding = onboarding;
        _verification = verification;
        _loading = false;
        _refreshing = false;
        _error = null;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _refreshing = false;
        _error = 'We couldn’t load your dashboard.';
      });
      showSwetoSnackBar(
        context,
        message: 'Dashboard refresh failed.',
        type: SwetoSnackBarType.error,
      );
    }
  }

  void _openVerification() => context.goNamed(AppRoutes.gymVerificationName);

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: AppColors.background,
        body: Center(
          child: CircularProgressIndicator(color: AppColors.primary),
        ),
      );
    }
    if (_gym == null || _error != null) {
      return Scaffold(
        backgroundColor: AppColors.background,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error ?? 'No gym is associated with this account.'),
              const SizedBox(height: 12),
              OutlinedButton(onPressed: _load, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }
    final status = _verification?.status ?? 'not_submitted';
    final limited = status != 'approved';
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.primary,
          onRefresh: () => _load(refresh: true),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
            children: [
              Text('Hello, there 👋', style: AppTextStyles.bodyMedium),
              const SizedBox(height: 6),
              Text('Welcome to SWETO!', style: AppTextStyles.headingLarge),
              const SizedBox(height: 6),
              Text(
                limited
                    ? 'You’re almost there. Complete verification to unlock all features.'
                    : 'Manage your gym, members and bookings from one place.',
                style: AppTextStyles.bodyMedium,
              ),
              const SizedBox(height: 22),
              _statusCard(status),
              if (limited) ...[const SizedBox(height: 14), _limitedBanner()],
              const SizedBox(height: 24),
              Text('Overview', style: AppTextStyles.titleLarge),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _stat(
                      'Bookings Today',
                      '—',
                      Icons.calendar_today_outlined,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _stat('Check-ins Today', '—', Icons.groups_outlined),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _stat(
                      'Revenue',
                      '—',
                      Icons.account_balance_wallet_outlined,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _stat('Active Members', '—', Icons.people_outline),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Text('Tasks to Complete', style: AppTextStyles.titleLarge),
              const SizedBox(height: 10),
              _task(
                'Gym Details',
                _onboarding?.nextStep != GymOnboardingStep.basicInformation,
              ),
              _task('Gym Photos', true),
              _task(
                'Business Documents',
                status == 'approved' || status == 'pending',
                onTap: _openVerification,
              ),
              const SizedBox(height: 24),
              if (status != 'approved')
                FilledButton.icon(
                  onPressed: _openVerification,
                  icon: const Icon(Icons.shield_outlined),
                  label: Text(
                    status == 'rejected'
                        ? 'Review and Resubmit'
                        : 'Continue Verification',
                  ),
                ),
              if (_refreshing)
                const Padding(
                  padding: EdgeInsets.only(top: 16),
                  child: LinearProgressIndicator(),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _statusCard(String status) {
    final pending = status == 'pending';
    final approved = status == 'approved';
    final rejected = status == 'rejected';
    final title = approved
        ? 'Gym Verified'
        : rejected
        ? 'Verification Needs Attention'
        : pending
        ? 'Verification Pending'
        : 'Verification Incomplete';
    final message = approved
        ? 'Your gym is approved and ready to use.'
        : rejected
        ? (_verification?.rejectionReason ??
              'Review and resubmit your documents.')
        : pending
        ? 'Your documents are currently under review.'
        : 'Upload the required documents and submit your gym for review.';
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            approved ? Icons.verified_outlined : Icons.shield_outlined,
            color: approved ? AppColors.secondary : AppColors.primary,
            size: 30,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: AppTextStyles.labelMedium),
                const SizedBox(height: 6),
                Text(message, style: AppTextStyles.bodySmall),
                if (!approved && !pending)
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: _openVerification,
                      child: const Text('Continue Verification'),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _limitedBanner() => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadius.md),
    ),
    child: const Text('Some features will unlock after your gym is verified.'),
  );

  Widget _stat(String label, String value, IconData icon) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadius.md),
      border: Border.all(color: AppColors.border),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: AppColors.primary),
        const SizedBox(height: 10),
        Text(value, style: AppTextStyles.headingMedium),
        Text(label, style: AppTextStyles.caption),
      ],
    ),
  );

  Widget _task(String label, bool complete, {VoidCallback? onTap}) => ListTile(
    contentPadding: const EdgeInsets.symmetric(horizontal: 4),
    leading: Icon(
      complete ? Icons.check_circle : Icons.radio_button_unchecked,
      color: complete ? AppColors.secondary : AppColors.primary,
    ),
    title: Text(label),
    trailing: onTap == null
        ? null
        : const Icon(Icons.arrow_forward_ios, size: 16),
    onTap: onTap,
  );
}
