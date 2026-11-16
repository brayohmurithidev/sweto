import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/export_share.dart';
import 'package:sweto_app/features/members/presentation/member_formatting.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/features/staff/domain/staff_entities.dart';
import 'package:sweto_app/features/staff/presentation/staff_providers.dart';
import 'package:sweto_app/shared/widgets/sweto_snackbar.dart';

/// Tabs on the member list, each a standing filter on the API.
enum MembersTab {
  active('Active', MemberStanding.active, 'No members with a current plan.'),
  expiring(
    'Expiring',
    MemberStanding.expiring,
    'Nobody\'s plan ends in the next 7 days.',
  ),
  expired('Expired', MemberStanding.expired, 'No expired members.'),
  neverPaid(
    'Never paid',
    MemberStanding.noMembership,
    'Everyone has paid at least once.',
  );

  const MembersTab(this.label, this.standing, this.emptyMessage);
  final String label;
  final MemberStanding standing;
  final String emptyMessage;
}

class MembersScreen extends ConsumerStatefulWidget {
  const MembersScreen({required this.gymId, super.key});

  final String gymId;

  @override
  ConsumerState<MembersScreen> createState() => _MembersScreenState();
}

class _MembersScreenState extends ConsumerState<MembersScreen> {
  static const _pageSize = 30;

  final _search = TextEditingController();
  final _scroll = ScrollController();
  Timer? _debounce;
  MembersTab _tab = MembersTab.active;
  List<GymMember> _members = const [];
  int _total = 0;
  bool _loading = true;
  bool _loadingMore = false;
  String? _error;
  int _request = 0;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_maybeLoadMore);
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final request = ++_request;
    setState(() {
      _loading = _members.isEmpty;
      _error = null;
    });
    try {
      final page = await ref
          .read(membersRepositoryProvider)
          .listMembers(
            widget.gymId,
            standing: _tab.standing,
            search: _search.text,
            limit: _pageSize,
          );
      if (!mounted || request != _request) return;
      setState(() {
        _members = page.members;
        _total = page.total;
        _loading = false;
      });
    } catch (error) {
      if (!mounted || request != _request) return;
      setState(() {
        _loading = false;
        _error = memberErrorMessage(error);
      });
    }
  }

  Future<void> _loadMore() async {
    if (_loadingMore || _members.length >= _total) return;
    final request = _request;
    setState(() => _loadingMore = true);
    try {
      final page = await ref
          .read(membersRepositoryProvider)
          .listMembers(
            widget.gymId,
            standing: _tab.standing,
            search: _search.text,
            limit: _pageSize,
            offset: _members.length,
          );
      if (!mounted || request != _request) return;
      setState(() {
        _members = [..._members, ...page.members];
        _total = page.total;
      });
    } catch (_) {
      // The list keeps what it has; scrolling again retries.
    } finally {
      if (mounted) setState(() => _loadingMore = false);
    }
  }

  void _maybeLoadMore() {
    if (_scroll.position.extentAfter < 400) _loadMore();
  }

  void _selectTab(MembersTab tab) {
    if (tab == _tab) return;
    setState(() {
      _tab = tab;
      _members = const [];
    });
    _load();
  }

  void _onSearchChanged(String _) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      setState(() => _members = const []);
      _load();
    });
  }

  /// Opens a member; the list refreshes when they come back.
  Future<void> _open(String memberId) async {
    await context.pushNamed(
      AppRoutes.memberDetailName,
      pathParameters: {'gymId': widget.gymId, 'memberId': memberId},
    );
    if (mounted) _load();
  }

  Future<void> _add() async {
    final memberId = await context.pushNamed<String>(
      AppRoutes.addMemberName,
      pathParameters: {'gymId': widget.gymId},
    );
    if (!mounted) return;
    _load();
    if (memberId != null) await _open(memberId);
  }

  bool _exporting = false;

  /// Shares every member (name, phone, standing, paid until) as a CSV.
  Future<void> _export(BuildContext buttonContext) async {
    if (_exporting) return;
    final box = buttonContext.findRenderObject() as RenderBox?;
    final origin = box == null
        ? null
        : box.localToGlobal(Offset.zero) & box.size;
    setState(() => _exporting = true);
    try {
      final file = await ref
          .read(membersRepositoryProvider)
          .exportMembers(widget.gymId);
      await ref.read(exportSharerProvider)(file, origin: origin);
    } catch (error) {
      if (mounted) {
        showSwetoSnackBar(
          context,
          message: memberErrorMessage(error),
          type: SwetoSnackBarType.error,
        );
      }
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        title: const Text('Members'),
        actions: [
          if (ref.watch(gymAccessProvider).can(GymPermission.exportMembers))
            Builder(
              builder: (buttonContext) => IconButton(
                key: const Key('members-export'),
                tooltip: 'Export member list',
                onPressed: _exporting ? null : () => _export(buttonContext),
                icon: _exporting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.ios_share),
              ),
            ),
        ],
      ),
      floatingActionButton:
          ref.watch(gymAccessProvider).can(GymPermission.editMembers)
          ? FloatingActionButton.extended(
              key: const Key('add-member-button'),
              onPressed: _add,
              backgroundColor: AppColors.primary,
              foregroundColor: AppColors.white,
              icon: const Icon(Icons.person_add_alt_1),
              label: const Text('Add member'),
            )
          : null,
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.md,
              AppSpacing.xs,
              AppSpacing.md,
              AppSpacing.xs,
            ),
            child: TextField(
              key: const Key('members-search'),
              controller: _search,
              onChanged: _onSearchChanged,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Search by name or phone',
                prefixIcon: const Icon(Icons.search),
                filled: true,
                fillColor: AppColors.surface,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
            child: Container(
              height: 44,
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              // All four tabs always visible, even on a narrow phone.
              child: Row(
                children: [
                  for (final tab in MembersTab.values)
                    Expanded(
                      child: _TabSegment(
                        key: Key('members-tab-${tab.name}'),
                        label: tab.label,
                        selected: tab == _tab,
                        onTap: () => _selectTab(tab),
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Expanded(child: _body()),
        ],
      ),
    );
  }

  Widget _body() {
    if (_loading) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.primary),
      );
    }
    if (_error != null && _members.isEmpty) {
      return _Message(
        key: const Key('members-error'),
        message: _error!,
        action: OutlinedButton(onPressed: _load, child: const Text('Retry')),
      );
    }
    return RefreshIndicator(
      color: AppColors.primary,
      onRefresh: _load,
      child: _members.isEmpty
          ? ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: [
                const SizedBox(height: 80),
                _Message(
                  key: const Key('members-empty'),
                  message: _search.text.trim().isEmpty
                      ? _tab.emptyMessage
                      : 'No members match "${_search.text.trim()}".',
                ),
              ],
            )
          : ListView.separated(
              key: const Key('members-list'),
              controller: _scroll,
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.md,
                AppSpacing.xs,
                AppSpacing.md,
                96,
              ),
              itemCount: _members.length + (_members.length < _total ? 1 : 0),
              separatorBuilder: (_, _) => const SizedBox(height: AppSpacing.xs),
              itemBuilder: (context, index) {
                if (index == _members.length) {
                  return const Padding(
                    padding: EdgeInsets.all(AppSpacing.md),
                    child: Center(
                      child: CircularProgressIndicator(
                        color: AppColors.primary,
                      ),
                    ),
                  );
                }
                final member = _members[index];
                return _MemberRow(
                  member: member,
                  onTap: () => _open(member.id),
                );
              },
            ),
    );
  }
}

class _TabSegment extends StatelessWidget {
  const _TabSegment({
    required this.label,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: selected,
      button: true,
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.sm),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? AppColors.primary : AppColors.transparent,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.caption.copyWith(
              color: selected ? AppColors.white : AppColors.textSecondary,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ),
      ),
    );
  }
}

class _MemberRow extends StatelessWidget {
  const _MemberRow({required this.member, required this.onTap});

  final GymMember member;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: InkWell(
        key: Key('member-row-${member.id}'),
        borderRadius: BorderRadius.circular(AppRadius.md),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              CircleAvatar(
                backgroundColor: AppColors.primarySoft,
                child: Text(
                  member.fullName.characters.first.toUpperCase(),
                  style: AppTextStyles.labelMedium,
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      member.fullName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.labelMedium,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      member.phoneNumber,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: AppSpacing.xs),
              StandingBadge(member: member, compact: true),
            ],
          ),
        ),
      ),
    );
  }
}

class _Message extends StatelessWidget {
  const _Message({required this.message, this.action, super.key});

  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message,
              textAlign: TextAlign.center,
              style: AppTextStyles.bodyMedium,
            ),
            if (action != null) ...[
              const SizedBox(height: AppSpacing.sm),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}
