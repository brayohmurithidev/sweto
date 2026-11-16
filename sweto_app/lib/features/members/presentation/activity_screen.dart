import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/activity_row.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';

/// Everything that happened at the gym, with who did it; or one staff
/// member's share of it when [byUserId] is set. Owner and manager.
class ActivityScreen extends ConsumerStatefulWidget {
  const ActivityScreen({
    required this.gymId,
    this.byUserId,
    this.byName,
    this.now,
    super.key,
  });

  final String gymId;
  final String? byUserId;
  final String? byName;
  final DateTime Function()? now;

  @override
  ConsumerState<ActivityScreen> createState() => _ActivityScreenState();
}

class _ActivityScreenState extends ConsumerState<ActivityScreen> {
  static const _page = 30;
  final _items = <ActivityItem>[];
  bool _hasMore = false;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load(reset: true);
  }

  Future<void> _load({bool reset = false}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await ref
          .read(membersRepositoryProvider)
          .getActivity(
            widget.gymId,
            byUserId: widget.byUserId,
            limit: _page,
            offset: reset ? 0 : _items.length,
          );
      if (!mounted) return;
      setState(() {
        if (reset) _items.clear();
        _items.addAll(page.items);
        _hasMore = page.hasMore;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = memberErrorMessage(error);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final now = (widget.now ?? DateTime.now)();
    final title = widget.byName == null
        ? 'Activity'
        : '${firstName(widget.byName!)}\'s activity';
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(backgroundColor: AppColors.background, title: Text(title)),
      body: RefreshIndicator(
        color: AppColors.primary,
        onRefresh: () => _load(reset: true),
        child: ListView(
          key: const Key('activity-list'),
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
          children: [
            if (widget.byUserId != null)
              Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                child: Text(
                  'Members they added, payments they took and the check-ins '
                  'they let in.',
                  style: AppTextStyles.bodySmall,
                ),
              ),
            for (final item in _items)
              ActivityRow(
                item: item,
                now: now,
                showBy: widget.byUserId == null,
                onTap: item.memberId == null
                    ? null
                    : () => context.pushNamed(
                        AppRoutes.memberDetailName,
                        pathParameters: {
                          'gymId': widget.gymId,
                          'memberId': item.memberId!,
                        },
                      ),
              ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
                child: Column(
                  children: [
                    Text(_error!, key: const Key('activity-error')),
                    TextButton(
                      onPressed: () => _load(reset: _items.isEmpty),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              )
            else if (_loading)
              const Padding(
                padding: EdgeInsets.all(AppSpacing.lg),
                child: Center(
                  child: CircularProgressIndicator(color: AppColors.primary),
                ),
              )
            else if (_items.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.xl),
                child: Text(
                  'Nothing yet.',
                  key: const Key('activity-empty'),
                  textAlign: TextAlign.center,
                  style: AppTextStyles.bodySmall,
                ),
              )
            else if (_hasMore)
              TextButton(
                key: const Key('activity-load-more'),
                onPressed: _load,
                child: const Text('Show more'),
              ),
          ],
        ),
      ),
    );
  }
}
