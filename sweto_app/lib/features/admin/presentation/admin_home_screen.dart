import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/admin/domain/admin_entities.dart';
import 'package:sweto_app/features/admin/presentation/admin_providers.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';
import 'package:sweto_app/features/members/presentation/member_formatting.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';

/// SWETO staff: gyms waiting for review, and those already decided.
class AdminHomeScreen extends ConsumerStatefulWidget {
  const AdminHomeScreen({super.key});

  @override
  ConsumerState<AdminHomeScreen> createState() => _AdminHomeScreenState();
}

class _AdminHomeScreenState extends ConsumerState<AdminHomeScreen> {
  static const _tabs = [
    (VerificationStatus.pending, 'Waiting'),
    (VerificationStatus.rejected, 'Rejected'),
    (VerificationStatus.approved, 'Approved'),
  ];

  VerificationStatus _status = VerificationStatus.pending;
  VerificationQueuePage? _page;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final page = await ref
          .read(adminRepositoryProvider)
          .listVerifications(_status);
      if (mounted) setState(() => _page = page);
    } catch (error) {
      if (mounted) setState(() => _error = memberErrorMessage(error));
    }
  }

  void _show(VerificationStatus status) {
    if (status == _status) return;
    setState(() {
      _status = status;
      _page = null;
    });
    _load();
  }

  Future<void> _open(VerificationSummary gym) async {
    final changed = await context.pushNamed<bool>(
      AppRoutes.adminGymReviewName,
      pathParameters: {'gymId': gym.gymId},
    );
    if (changed == true && mounted) _load();
  }

  @override
  Widget build(BuildContext context) {
    final page = _page;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        title: const Text('Gym reviews'),
        actions: [
          IconButton(
            key: const Key('admin-logout'),
            tooltip: 'Log out',
            icon: const Icon(Icons.logout_rounded),
            onPressed: () =>
                ref.read(sessionControllerProvider.notifier).logout(),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 8),
              child: SegmentedButton<VerificationStatus>(
                key: const Key('admin-status-tabs'),
                showSelectedIcon: false,
                segments: [
                  for (final (status, label) in _tabs)
                    ButtonSegment(value: status, label: Text(label)),
                ],
                selected: {_status},
                onSelectionChanged: (s) => _show(s.first),
              ),
            ),
            Expanded(
              child: RefreshIndicator(
                color: AppColors.primary,
                onRefresh: _load,
                child: _body(page),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _body(VerificationQueuePage? page) {
    if (_error != null && page == null) {
      return ListView(
        children: [
          const SizedBox(height: 80),
          Center(child: Text(_error!, key: const Key('admin-queue-error'))),
          Center(
            child: TextButton(onPressed: _load, child: const Text('Retry')),
          ),
        ],
      );
    }
    if (page == null) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.primary),
      );
    }
    if (page.gyms.isEmpty) {
      return ListView(
        children: [
          const SizedBox(height: 80),
          Center(
            child: Text(
              _status == VerificationStatus.pending
                  ? 'No gyms waiting for review.'
                  : 'Nothing here yet.',
              key: const Key('admin-queue-empty'),
              style: AppTextStyles.bodyMedium,
            ),
          ),
        ],
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 32),
      itemCount: page.gyms.length,
      separatorBuilder: (_, _) => const SizedBox(height: AppSpacing.xs),
      itemBuilder: (_, i) => _row(page.gyms[i]),
    );
  }

  Widget _row(VerificationSummary gym) {
    final when = _status == VerificationStatus.pending
        ? gym.submittedAt
        : gym.reviewedAt;
    final missing = gym.missingDocuments.length;
    return Material(
      color: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        side: const BorderSide(color: AppColors.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: ListTile(
        key: Key('admin-gym-${gym.gymId}'),
        title: Text(gym.gymName, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: Text(
          [
            if (when != null)
              '${_status == VerificationStatus.pending ? 'Submitted' : 'Reviewed'} '
                  '${formatDayTime(when)}',
            if (missing > 0)
              '$missing ${missing == 1 ? 'document' : 'documents'} missing',
          ].join(' · '),
          style: AppTextStyles.bodySmall.copyWith(
            color: missing > 0 ? AppColors.warning : null,
          ),
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => _open(gym),
      ),
    );
  }
}
