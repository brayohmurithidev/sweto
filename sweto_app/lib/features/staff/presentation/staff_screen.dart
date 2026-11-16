import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/presentation/member_formatting.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/features/staff/domain/staff_entities.dart';
import 'package:sweto_app/features/staff/presentation/staff_providers.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';
import 'package:sweto_app/shared/widgets/sweto_dialog.dart';
import 'package:sweto_app/shared/widgets/sweto_snackbar.dart';

/// The owner's team: who works here, in which role, and adding or removing
/// people. Staff sign in with their own phone number.
class StaffScreen extends ConsumerStatefulWidget {
  const StaffScreen({required this.gymId, super.key});
  final String gymId;

  @override
  ConsumerState<StaffScreen> createState() => _StaffScreenState();
}

class _StaffScreenState extends ConsumerState<StaffScreen> {
  List<StaffMember>? _staff;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final staff = await ref
          .read(staffRepositoryProvider)
          .listStaff(widget.gymId);
      if (!mounted) return;
      setState(() {
        _staff = staff;
        _error = null;
      });
    } catch (error) {
      if (mounted) setState(() => _error = memberErrorMessage(error));
    }
  }

  Future<void> _add() async {
    final added = await showModalBottomSheet<AddedStaff>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      backgroundColor: AppColors.surfaceElevated,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => _AddStaffSheet(gymId: widget.gymId),
    );
    if (added == null || !mounted) return;
    final name = added.staff.displayName;
    showSwetoSnackBar(
      context,
      message: added.inviteSent
          ? 'Added $name. We texted them how to sign in.'
          : 'Added $name, but the invite SMS failed. Ask them to get SWETO '
                'and sign in with their number.',
      type: added.inviteSent
          ? SwetoSnackBarType.success
          : SwetoSnackBarType.warning,
    );
    await _load();
  }

  Future<void> _manage(StaffMember member) async {
    final changed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      backgroundColor: AppColors.surfaceElevated,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => _ManageStaffSheet(gymId: widget.gymId, member: member),
    );
    if (changed == true && mounted) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final staff = _staff;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        title: const Text('Staff'),
      ),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('add-staff-button'),
        onPressed: _add,
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.white,
        icon: const Icon(Icons.person_add_alt_1),
        label: const Text('Add staff'),
      ),
      body: staff == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator(color: AppColors.primary)
                  : Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_error!, key: const Key('staff-error')),
                        const SizedBox(height: AppSpacing.sm),
                        OutlinedButton(
                          onPressed: _load,
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
            )
          : RefreshIndicator(
              color: AppColors.primary,
              onRefresh: _load,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                children: [
                  Text(
                    'Add the people who run your front desk or train members. '
                    'Each one signs in with their own phone number and sees '
                    'only what their role allows.',
                    style: AppTextStyles.bodySmall,
                  ),
                  const SizedBox(height: AppSpacing.md),
                  for (final member in staff) ...[
                    _StaffTile(
                      member: member,
                      onTap: member.isPrimaryOwner
                          ? null
                          : () => _manage(member),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                  ],
                  if (staff.length == 1)
                    Padding(
                      padding: const EdgeInsets.only(top: AppSpacing.sm),
                      child: Text(
                        'No staff yet. Tap Add staff to add your first.',
                        key: const Key('staff-empty'),
                        textAlign: TextAlign.center,
                        style: AppTextStyles.bodySmall,
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}

class _StaffTile extends StatelessWidget {
  const _StaffTile({required this.member, required this.onTap});
  final StaffMember member;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final badges = [
      if (member.isPrimaryOwner) ('You', AppColors.secondary),
      if (!member.isPrimaryOwner && !member.hasSignedIn)
        ('Invited', AppColors.warning),
      if (member.isSuspended) ('Paused', AppColors.error),
    ];
    return Material(
      color: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        side: const BorderSide(color: AppColors.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        key: Key('staff-${member.id}'),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              CircleAvatar(
                radius: 20,
                backgroundColor: AppColors.primary.withValues(alpha: 0.15),
                child: (member.fullName?.trim().isNotEmpty ?? false)
                    ? Text(
                        member.fullName!.trim()[0].toUpperCase(),
                        style: AppTextStyles.labelMedium.copyWith(
                          color: AppColors.primary,
                        ),
                      )
                    : const Icon(
                        Icons.person_outline,
                        size: 20,
                        color: AppColors.primary,
                      ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      member.displayName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.bodyLarge.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      [
                        member.role.label,
                        if (member.phoneNumber != null &&
                            member.displayName != member.phoneNumber)
                          member.phoneNumber!,
                      ].join(' · '),
                      style: AppTextStyles.bodySmall,
                    ),
                    if (_showsToday(member))
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          _todayLine(member.today!),
                          key: Key('staff-today-${member.id}'),
                          style: AppTextStyles.caption.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              for (final (label, color) in badges)
                Container(
                  margin: const EdgeInsets.only(left: 6),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    label,
                    style: AppTextStyles.caption.copyWith(color: color),
                  ),
                ),
              if (onTap != null)
                const Padding(
                  padding: EdgeInsets.only(left: 4),
                  child: Icon(
                    Icons.chevron_right,
                    color: AppColors.textSecondary,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Role cards: name and what the role can do, the chosen one outlined.
class _RolePicker extends StatelessWidget {
  const _RolePicker({required this.selected, required this.onChanged});
  final StaffRole? selected;
  final ValueChanged<StaffRole>? onChanged;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      for (final role in StaffRole.assignable) ...[
        Material(
          color: role == selected
              ? AppColors.primary.withValues(alpha: 0.10)
              : AppColors.surface,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
            side: BorderSide(
              color: role == selected ? AppColors.primary : AppColors.border,
              width: role == selected ? 1.5 : 1,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            key: Key('staff-role-${role.apiValue}'),
            onTap: onChanged == null ? null : () => onChanged!(role),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          role.label,
                          style: AppTextStyles.bodyLarge.copyWith(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(role.summary, style: AppTextStyles.bodySmall),
                      ],
                    ),
                  ),
                  Icon(
                    role == selected
                        ? Icons.check_circle_rounded
                        : Icons.radio_button_unchecked_rounded,
                    color: role == selected
                        ? AppColors.primary
                        : AppColors.border,
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
      ],
    ],
  );
}

class _AddStaffSheet extends ConsumerStatefulWidget {
  const _AddStaffSheet({required this.gymId});
  final String gymId;

  @override
  ConsumerState<_AddStaffSheet> createState() => _AddStaffSheetState();
}

class _AddStaffSheetState extends ConsumerState<_AddStaffSheet> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  StaffRole? _role = StaffRole.receptionist;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final name = _name.text.trim();
    final phone = _phone.text.trim();
    if (name.length < 2) {
      setState(() => _error = 'Enter their name.');
      return;
    }
    if (phone.replaceAll(RegExp(r'\D'), '').length < 9) {
      setState(() => _error = 'Enter their mobile number.');
      return;
    }
    if (_role == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final added = await ref
          .read(staffRepositoryProvider)
          .addStaff(
            widget.gymId,
            fullName: name,
            phoneNumber: phone,
            role: _role!,
          );
      if (mounted) Navigator.pop(context, added);
    } catch (error) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = memberErrorMessage(error);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
    child: SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Add staff', style: AppTextStyles.headingMedium),
            const SizedBox(height: AppSpacing.xxs),
            Text(
              'We\'ll text them an invite. They sign in with this number.',
              style: AppTextStyles.bodySmall,
            ),
            const SizedBox(height: AppSpacing.md),
            TextField(
              key: const Key('staff-name-field'),
              controller: _name,
              textCapitalization: TextCapitalization.words,
              // Names like Wanjiku must not be "corrected".
              autocorrect: false,
              decoration: const InputDecoration(labelText: 'Full name'),
            ),
            const SizedBox(height: AppSpacing.sm),
            TextField(
              key: const Key('staff-phone-field'),
              controller: _phone,
              keyboardType: TextInputType.phone,
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[0-9+ ]')),
              ],
              decoration: const InputDecoration(
                labelText: 'Mobile number',
                hintText: '0712 345 678',
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            Text('Role', style: AppTextStyles.labelMedium),
            const SizedBox(height: AppSpacing.xs),
            _RolePicker(
              selected: _role,
              onChanged: _busy ? null : (role) => setState(() => _role = role),
            ),
            if (_error != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                _error!,
                key: const Key('add-staff-error'),
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
              ),
            ],
            const SizedBox(height: AppSpacing.md),
            AppPrimaryButton(
              key: const Key('add-staff-submit'),
              label: _busy ? 'Adding…' : 'Add and send invite',
              onPressed: _busy ? null : _save,
            ),
          ],
        ),
      ),
    ),
  );
}

class _ManageStaffSheet extends ConsumerStatefulWidget {
  const _ManageStaffSheet({required this.gymId, required this.member});
  final String gymId;
  final StaffMember member;

  @override
  ConsumerState<_ManageStaffSheet> createState() => _ManageStaffSheetState();
}

class _ManageStaffSheetState extends ConsumerState<_ManageStaffSheet> {
  late StaffRole _role = widget.member.role;
  bool _busy = false;
  String? _error;

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = memberErrorMessage(error);
        });
      }
    }
  }

  Future<void> _saveRole() => _run(
    () => ref
        .read(staffRepositoryProvider)
        .updateStaff(widget.gymId, widget.member.id, role: _role),
  );

  Future<void> _togglePause() async {
    final member = widget.member;
    if (!member.isSuspended) {
      final ok = await showSwetoConfirmationDialog(
        context,
        title: 'Pause ${member.displayName}?',
        message:
            'They are signed out now and cannot use SWETO for this gym until '
            'you turn their access back on.',
        confirmLabel: 'Pause access',
        type: SwetoDialogType.destructive,
      );
      if (!ok || !mounted) return;
    }
    await _run(
      () => ref
          .read(staffRepositoryProvider)
          .updateStaff(widget.gymId, member.id, suspended: !member.isSuspended),
    );
  }

  Future<void> _remove() async {
    final member = widget.member;
    final ok = await showSwetoConfirmationDialog(
      context,
      title: 'Remove ${member.displayName}?',
      message:
          'They are signed out now and lose access to this gym. You can add '
          'them again later.',
      confirmLabel: 'Remove',
      type: SwetoDialogType.destructive,
    );
    if (!ok || !mounted) return;
    await _run(
      () => ref
          .read(staffRepositoryProvider)
          .removeStaff(widget.gymId, member.id),
    );
  }

  @override
  Widget build(BuildContext context) {
    final member = widget.member;
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(member.displayName, style: AppTextStyles.headingMedium),
            if (member.phoneNumber != null)
              Text(member.phoneNumber!, style: AppTextStyles.bodySmall),
            const SizedBox(height: AppSpacing.md),
            Text('Role', style: AppTextStyles.labelMedium),
            const SizedBox(height: AppSpacing.xs),
            _RolePicker(
              selected: _role,
              onChanged: _busy ? null : (role) => setState(() => _role = role),
            ),
            if (_error != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                _error!,
                key: const Key('manage-staff-error'),
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
              ),
            ],
            const SizedBox(height: AppSpacing.sm),
            AppPrimaryButton(
              key: const Key('save-staff-role'),
              label: 'Save role',
              onPressed: _busy || _role == member.role ? null : _saveRole,
            ),
            const SizedBox(height: AppSpacing.xs),
            OutlinedButton.icon(
              key: const Key('pause-staff'),
              onPressed: _busy ? null : _togglePause,
              icon: Icon(
                member.isSuspended
                    ? Icons.play_circle_outline
                    : Icons.pause_circle_outline,
              ),
              label: Text(
                member.isSuspended ? 'Turn access back on' : 'Pause access',
              ),
            ),
            if (member.userId != null)
              OutlinedButton.icon(
                key: const Key('staff-activity'),
                onPressed: _busy
                    ? null
                    : () {
                        Navigator.pop(context);
                        context.pushNamed(
                          AppRoutes.activityName,
                          pathParameters: {'gymId': widget.gymId},
                          queryParameters: {
                            'by': member.userId!,
                            'name': member.displayName,
                          },
                        );
                      },
                icon: const Icon(Icons.history),
                label: const Text('See their activity'),
              ),
            TextButton.icon(
              key: const Key('remove-staff'),
              onPressed: _busy ? null : _remove,
              style: TextButton.styleFrom(foregroundColor: AppColors.error),
              icon: const Icon(Icons.person_remove_outlined),
              label: const Text('Remove from staff'),
            ),
          ],
        ),
      ),
    );
  }
}

/// "Today: 3 payments · KES 15,000 cash · 12 check-ins"
String _todayLine(StaffDay day) {
  if (day.isEmpty) return 'Today: nothing yet';
  final parts = [
    '${day.payments} payment${day.payments == 1 ? '' : 's'}',
    if (day.cash > 0) '${formatMoney(day.cash, 'KES')} cash',
    if (day.mpesa > 0) '${formatMoney(day.mpesa, 'KES')} M-Pesa',
    '${day.checkIns} check-in${day.checkIns == 1 ? '' : 's'}',
  ];
  return 'Today: ${parts.join(' · ')}';
}

/// Staff always see their day; the owner only once they did something.
bool _showsToday(StaffMember member) {
  final day = member.today;
  if (day == null) return false;
  return !member.isPrimaryOwner || !day.isEmpty;
}
