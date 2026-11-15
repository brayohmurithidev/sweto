import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/check_in_code_dialog.dart';
import 'package:sweto_app/features/members/presentation/member_formatting.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/features/members/presentation/mpesa_payment_sheet.dart';
import 'package:sweto_app/features/members/presentation/record_cash_payment_sheet.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';
import 'package:sweto_app/shared/widgets/sweto_dialog.dart';
import 'package:sweto_app/shared/widgets/sweto_snackbar.dart';

class MemberDetailScreen extends ConsumerStatefulWidget {
  const MemberDetailScreen({
    required this.gymId,
    required this.memberId,
    this.today,
    super.key,
  });

  final String gymId;
  final String memberId;

  /// Overrides "today" in tests.
  final DateTime? today;

  @override
  ConsumerState<MemberDetailScreen> createState() => _MemberDetailState();
}

class _MemberDetailState extends ConsumerState<MemberDetailScreen> {
  MemberDetail? _detail;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final detail = await ref
          .read(membersRepositoryProvider)
          .getMember(widget.gymId, widget.memberId);
      if (mounted) setState(() => _detail = detail);
    } catch (error) {
      if (mounted) setState(() => _error = memberErrorMessage(error));
    }
  }

  Future<void> _recordPayment() async {
    final member = _detail?.member;
    if (member == null) return;
    final updated = await showRecordCashPaymentSheet(
      context,
      gymId: widget.gymId,
      member: member,
      today: widget.today,
    );
    if (updated == null || !mounted) return;
    setState(() => _detail = updated);
    final sms = switch (updated.smsStatus) {
      'sent' => ' Receipt sent by SMS.',
      'failed' => ' The SMS receipt couldn\'t be sent.',
      _ => '',
    };
    showSwetoSnackBar(
      context,
      message: 'Payment recorded. ${standingLabel(updated.member)}.$sms',
      type: updated.smsStatus == 'failed'
          ? SwetoSnackBarType.warning
          : SwetoSnackBarType.success,
    );
  }

  Future<void> _issueCode() async {
    final member = _detail?.member;
    if (member == null) return;
    if (member.hasCheckInCode) {
      final confirmed = await showSwetoConfirmationDialog(
        context,
        title: 'Issue a new code?',
        message:
            '${member.fullName}\'s current code and QR will stop working '
            'straight away.',
        confirmLabel: 'New code',
      );
      if (!confirmed || !mounted) return;
    }
    setState(() => _busy = true);
    try {
      final code = await ref
          .read(membersRepositoryProvider)
          .issueCheckInCode(widget.gymId, member.id);
      if (!mounted) return;
      await showCheckInCodeDialog(
        context,
        memberName: member.fullName,
        code: code,
      );
      await _load();
    } catch (error) {
      if (mounted) {
        showSwetoSnackBar(
          context,
          message: memberErrorMessage(error),
          type: SwetoSnackBarType.error,
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _requestMpesa() async {
    final member = _detail?.member;
    if (member == null) return;
    final paid = await showMpesaPaymentSheet(
      context,
      gymId: widget.gymId,
      member: member,
    );
    if (!mounted) return;
    await _load();
    if (paid != null && mounted) {
      showSwetoSnackBar(
        context,
        message: mpesaPaidMessage(paid),
        type: SwetoSnackBarType.success,
      );
    }
  }

  Future<void> _setSms(bool enabled) async {
    final member = _detail?.member;
    if (member == null) return;
    if (enabled) {
      final confirmed = await showSwetoConfirmationDialog(
        context,
        title: 'Turn on SMS?',
        message:
            'Confirm that ${member.fullName} agreed to receive SMS from the '
            'gym: their check-in code, receipts and expiry reminders.',
        confirmLabel: 'They agreed',
      );
      if (!confirmed || !mounted) return;
    }
    setState(() => _busy = true);
    try {
      await ref
          .read(membersRepositoryProvider)
          .setSms(widget.gymId, member.id, enabled: enabled);
      await _load();
    } catch (error) {
      if (mounted) {
        showSwetoSnackBar(
          context,
          message: memberErrorMessage(error),
          type: SwetoSnackBarType.error,
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggleArchived() async {
    final member = _detail?.member;
    if (member == null) return;
    final archiving = !member.isArchived;
    if (archiving) {
      final confirmed = await showSwetoConfirmationDialog(
        context,
        title: 'Archive ${member.fullName}?',
        message:
            'They leave your member list. Their payment history is kept '
            'and you can restore them at any time.',
        confirmLabel: 'Archive',
        type: SwetoDialogType.destructive,
      );
      if (!confirmed || !mounted) return;
    }
    setState(() => _busy = true);
    try {
      await ref
          .read(membersRepositoryProvider)
          .setArchived(widget.gymId, member.id, archived: archiving);
      await _load();
    } catch (error) {
      if (mounted) {
        showSwetoSnackBar(
          context,
          message: memberErrorMessage(error),
          type: SwetoSnackBarType.error,
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final detail = _detail;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        title: const Text('Member'),
        actions: [
          if (detail != null)
            IconButton(
              key: const Key('member-archive-toggle'),
              tooltip: detail.member.isArchived ? 'Restore' : 'Archive',
              onPressed: _busy ? null : _toggleArchived,
              icon: Icon(
                detail.member.isArchived
                    ? Icons.unarchive_outlined
                    : Icons.archive_outlined,
              ),
            ),
        ],
      ),
      body: detail == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator(color: AppColors.primary)
                  : Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_error!, key: const Key('member-detail-error')),
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
                padding: const EdgeInsets.all(AppSpacing.md),
                children: [
                  _header(detail.member),
                  const SizedBox(height: AppSpacing.md),
                  if (detail.member.isArchived)
                    Text(
                      'Archived. Restore this member to record payments.',
                      key: const Key('member-archived-note'),
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.warning,
                      ),
                    )
                  else ...[
                    AppPrimaryButton(
                      key: const Key('record-cash-button'),
                      label: 'Record cash payment',
                      onPressed: _busy ? null : _recordPayment,
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    SizedBox(
                      height: 52,
                      child: OutlinedButton.icon(
                        key: const Key('request-mpesa-button'),
                        onPressed: _busy ? null : _requestMpesa,
                        icon: const Icon(Icons.phone_android),
                        label: const Text('Request M-Pesa payment'),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    _checkInCodeCard(detail.member),
                    const SizedBox(height: AppSpacing.sm),
                    _smsCard(detail.member),
                  ],
                  const SizedBox(height: AppSpacing.lg),
                  Text('Membership history', style: AppTextStyles.titleLarge),
                  const SizedBox(height: AppSpacing.xs),
                  if (detail.memberships.isEmpty)
                    Text(
                      'No payments recorded yet.',
                      style: AppTextStyles.bodySmall,
                    )
                  else
                    for (final membership in detail.memberships)
                      _MembershipTile(membership: membership),
                ],
              ),
            ),
    );
  }

  Widget _smsCard(GymMember member) => Material(
    color: AppColors.surface,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(AppRadius.lg),
      side: const BorderSide(color: AppColors.border),
    ),
    clipBehavior: Clip.antiAlias,
    child: SwitchListTile(
      key: const Key('member-sms-switch'),
      secondary: const Icon(Icons.sms_outlined, color: AppColors.primary),
      title: const Text('SMS'),
      subtitle: Text(
        member.smsEnabled
            ? 'Code, receipts and expiry reminders by SMS.'
            : member.smsOptedOutAt != null
            ? 'Opted out on ${formatDay(member.smsOptedOutAt!)}.'
            : 'No consent recorded. No SMS are sent.',
        style: AppTextStyles.bodySmall,
      ),
      value: member.smsEnabled,
      onChanged: _busy ? null : _setSms,
    ),
  );

  Widget _checkInCodeCard(GymMember member) => Material(
    color: AppColors.surface,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(AppRadius.lg),
      side: const BorderSide(color: AppColors.border),
    ),
    clipBehavior: Clip.antiAlias,
    child: ListTile(
      leading: const Icon(Icons.qr_code_2, color: AppColors.primary),
      title: const Text('Check-in code'),
      subtitle: Text(
        member.hasCheckInCode
            ? 'Issued. Codes are shown once; a new one replaces it.'
            : 'Not issued yet.',
        style: AppTextStyles.bodySmall,
      ),
      trailing: TextButton(
        key: const Key('issue-check-in-code'),
        onPressed: _busy ? null : _issueCode,
        child: Text(member.hasCheckInCode ? 'New code' : 'Show QR'),
      ),
    ),
  );

  Widget _header(GymMember member) => Container(
    padding: const EdgeInsets.all(AppSpacing.md),
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      border: Border.all(color: AppColors.border),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          member.fullName,
          key: const Key('member-detail-name'),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: AppTextStyles.headingMedium,
        ),
        const SizedBox(height: 4),
        Text(member.phoneNumber, style: AppTextStyles.bodyMedium),
        const SizedBox(height: AppSpacing.sm),
        StandingBadge(member: member, key: const Key('member-detail-standing')),
      ],
    ),
  );
}

class _MembershipTile extends StatelessWidget {
  const _MembershipTile({required this.membership});

  final GymMembership membership;

  @override
  Widget build(BuildContext context) {
    final status = switch (membership.status) {
      'active' => 'Active',
      'expired' => 'Expired',
      'cancelled' => 'Cancelled',
      _ => 'Awaiting payment',
    };
    final method = membership.payments.isEmpty
        ? ''
        : ' · ${membership.payments.first.method == 'mpesa' ? 'M-Pesa' : 'Cash'}';
    return Card(
      color: AppColors.surface,
      margin: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: ListTile(
        title: Text(
          membership.planName,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        subtitle: Text(
          '${formatDay(membership.startsOn)} – ${formatDay(membership.endsOn)}'
          '\n$status$method',
          style: AppTextStyles.bodySmall,
        ),
        isThreeLine: true,
        trailing: Text(
          formatMoney(membership.amount, membership.currency),
          style: AppTextStyles.labelMedium,
        ),
      ),
    );
  }
}
