import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/admin/domain/admin_entities.dart';
import 'package:sweto_app/features/admin/presentation/admin_providers.dart';
import 'package:sweto_app/features/members/presentation/member_formatting.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/shared/widgets/sweto_dialog.dart';

/// One gym's verification: what it told us, its documents, the history, and
/// approve or reject. Pops true when a decision was made.
class AdminGymReviewScreen extends ConsumerStatefulWidget {
  const AdminGymReviewScreen({required this.gymId, super.key});

  final String gymId;

  @override
  ConsumerState<AdminGymReviewScreen> createState() =>
      _AdminGymReviewScreenState();
}

class _AdminGymReviewScreenState extends ConsumerState<AdminGymReviewScreen> {
  VerificationDetail? _detail;
  String? _error;
  bool _busy = false;
  String? _opening;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final detail = await ref
          .read(adminRepositoryProvider)
          .getVerification(widget.gymId);
      if (mounted) {
        setState(() {
          _detail = detail;
          _error = null;
        });
      }
    } catch (error) {
      if (mounted) setState(() => _error = memberErrorMessage(error));
    }
  }

  Future<void> _openDocument(VerificationDocument document) async {
    setState(() => _opening = document.type);
    try {
      final url = await ref
          .read(adminRepositoryProvider)
          .documentDownloadUrl(widget.gymId, document.type);
      final opened = await ref.read(linkOpenerProvider)(url);
      if (!opened) _snack('No app on this phone can open that file.');
    } catch (error) {
      _snack(memberErrorMessage(error));
    } finally {
      if (mounted) setState(() => _opening = null);
    }
  }

  Future<void> _approve() async {
    final name = _detail?.gym?.name ?? 'this gym';
    final confirmed = await showSwetoConfirmationDialog(
      context,
      title: 'Approve $name?',
      message:
          'The gym goes live: it can add members, take payments and be '
          'listed.',
      confirmLabel: 'Approve',
    );
    if (!confirmed || !mounted) return;
    await _decide(
      () => ref.read(adminRepositoryProvider).approve(widget.gymId),
    );
  }

  Future<void> _reject() async {
    final reason = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => const _RejectSheet(),
    );
    if (reason == null || !mounted) return;
    await _decide(
      () => ref
          .read(adminRepositoryProvider)
          .reject(widget.gymId, reason: reason),
    );
  }

  Future<void> _decide(Future<VerificationDetail> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      if (mounted) context.pop(true);
    } catch (error) {
      _snack(memberErrorMessage(error));
      if (mounted) setState(() => _busy = false);
    }
  }

  void _snack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final detail = _detail;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        title: Text(detail?.gym?.name ?? 'Gym review'),
      ),
      bottomNavigationBar: detail?.status == VerificationStatus.pending
          ? SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        key: const Key('admin-reject'),
                        onPressed: _busy ? null : _reject,
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.error,
                          side: const BorderSide(color: AppColors.error),
                          minimumSize: const Size.fromHeight(52),
                        ),
                        child: const Text('Reject'),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: FilledButton(
                        key: const Key('admin-approve'),
                        onPressed: _busy ? null : _approve,
                        style: FilledButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          minimumSize: const Size.fromHeight(52),
                        ),
                        child: Text(_busy ? 'Saving…' : 'Approve'),
                      ),
                    ),
                  ],
                ),
              ),
            )
          : null,
      body: detail == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator(color: AppColors.primary)
                  : Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_error!, key: const Key('admin-review-error')),
                        TextButton(
                          onPressed: _load,
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 32),
              children: [
                _status(detail),
                const SizedBox(height: AppSpacing.md),
                ..._gymSection(detail.gym),
                const SizedBox(height: AppSpacing.md),
                ..._documents(detail),
                if (detail.history.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.md),
                  Text('History', style: AppTextStyles.titleLarge),
                  const SizedBox(height: AppSpacing.xs),
                  for (final entry in detail.history) _historyRow(entry),
                ],
              ],
            ),
    );
  }

  Widget _status(VerificationDetail d) {
    final (label, color) = switch (d.status) {
      VerificationStatus.pending => ('Waiting for review', AppColors.warning),
      VerificationStatus.approved => ('Approved', AppColors.secondary),
      VerificationStatus.rejected => ('Rejected', AppColors.error),
      VerificationStatus.notSubmitted => ('Not submitted', AppColors.textMuted),
    };
    final submitted = d.submittedAt;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          key: const Key('admin-review-status'),
          style: AppTextStyles.labelLarge.copyWith(color: color),
        ),
        if (submitted != null)
          Text(
            'Submitted ${formatDayTime(submitted)}',
            style: AppTextStyles.bodySmall,
          ),
        if (d.status == VerificationStatus.rejected &&
            d.rejectionReason != null)
          Text('Reason: ${d.rejectionReason}', style: AppTextStyles.bodySmall),
      ],
    );
  }

  List<Widget> _gymSection(ReviewedGym? gym) {
    if (gym == null) return const [];
    final location = [
      gym.addressLine,
      gym.neighbourhood,
      gym.city,
    ].whereType<String>().where((s) => s.trim().isNotEmpty).join(', ');
    final rows = <(String, String?)>[
      ('Legal name', gym.legalBusinessName),
      ('Business type', gym.businessType?.replaceAll('_', ' ')),
      ('Registration no.', gym.registrationNumber),
      ('KRA PIN', gym.taxNumber),
      ('Contact person', gym.contactPersonName),
      ('Contact phone', gym.contactPersonPhone),
      ('Gym phone', gym.phoneNumber),
      ('Gym email', gym.email),
      ('Location', location.isEmpty ? null : location),
    ];
    return [
      Text('Business', style: AppTextStyles.titleLarge),
      const SizedBox(height: AppSpacing.xs),
      Container(
        key: const Key('admin-review-business'),
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          children: [
            for (final (label, value) in rows)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 130,
                      child: Text(label, style: AppTextStyles.bodySmall),
                    ),
                    Expanded(
                      child: Text(
                        value == null || value.trim().isEmpty ? '—' : value,
                        style: AppTextStyles.bodyMedium.copyWith(
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    ];
  }

  List<Widget> _documents(VerificationDetail d) => [
    Text('Documents', style: AppTextStyles.titleLarge),
    const SizedBox(height: AppSpacing.xs),
    for (final type in d.missingDocuments)
      ListTile(
        contentPadding: EdgeInsets.zero,
        leading: const Icon(Icons.error_outline, color: AppColors.warning),
        title: Text(verificationDocumentLabel(type)),
        subtitle: Text('Missing', style: AppTextStyles.bodySmall),
      ),
    for (final doc in d.documents)
      ListTile(
        key: Key('admin-document-${doc.type}'),
        contentPadding: EdgeInsets.zero,
        leading: Icon(
          doc.mimeType == 'application/pdf'
              ? Icons.picture_as_pdf_outlined
              : Icons.image_outlined,
          color: AppColors.primary,
        ),
        title: Text(verificationDocumentLabel(doc.type)),
        subtitle: Text(
          '${doc.name} · uploaded ${formatDayTime(doc.uploadedAt)}',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppTextStyles.bodySmall,
        ),
        trailing: _opening == doc.type
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.open_in_new, size: 20),
        onTap: _opening == null ? () => _openDocument(doc) : null,
      ),
  ];

  Widget _historyRow(VerificationReviewEntry entry) => ListTile(
    contentPadding: EdgeInsets.zero,
    leading: Icon(
      entry.approved ? Icons.check_circle : Icons.cancel,
      color: entry.approved ? AppColors.secondary : AppColors.error,
    ),
    title: Text(entry.approved ? 'Approved' : 'Rejected'),
    subtitle: Text(
      [
        formatDayTime(entry.reviewedAt),
        if (entry.reason != null) entry.reason!,
        if (entry.notes != null) entry.notes!,
      ].join(' · '),
      style: AppTextStyles.bodySmall,
    ),
  );
}

/// Asks why, so the owner knows what to fix. Returns the reason, or null.
class _RejectSheet extends StatefulWidget {
  const _RejectSheet();

  @override
  State<_RejectSheet> createState() => _RejectSheetState();
}

class _RejectSheetState extends State<_RejectSheet> {
  final _reason = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  void _submit() {
    final reason = _reason.text.trim();
    if (reason.length < 5) {
      setState(() => _error = 'Tell the owner what to fix.');
      return;
    }
    Navigator.of(context).pop(reason);
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.fromLTRB(
      20,
      20,
      20,
      MediaQuery.viewInsetsOf(context).bottom + 24,
    ),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Reject this gym', style: AppTextStyles.headingMedium),
        const SizedBox(height: 6),
        Text(
          'The owner sees this reason and can fix it and resubmit.',
          style: AppTextStyles.bodySmall,
        ),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          key: const Key('admin-reject-reason'),
          controller: _reason,
          autofocus: true,
          maxLines: 3,
          maxLength: 2000,
          onChanged: (_) {
            if (_error != null) setState(() => _error = null);
          },
          decoration: InputDecoration(
            hintText: 'e.g. The business permit photo is blurry.',
            errorText: _error,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        FilledButton(
          key: const Key('admin-reject-confirm'),
          onPressed: _submit,
          style: FilledButton.styleFrom(
            backgroundColor: AppColors.error,
            minimumSize: const Size.fromHeight(52),
          ),
          child: const Text('Reject'),
        ),
      ],
    ),
  );
}
