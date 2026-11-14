import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/member_formatting.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';

/// Builds the camera view; calls [onCode] with each scanned value.
typedef CheckInScannerBuilder =
    Widget Function(BuildContext context, ValueChanged<String> onCode);

class CheckInScreen extends ConsumerStatefulWidget {
  const CheckInScreen({required this.gymId, this.scannerBuilder, super.key});

  final String gymId;

  /// Replaces the camera (widget tests have none).
  final CheckInScannerBuilder? scannerBuilder;

  @override
  ConsumerState<CheckInScreen> createState() => _CheckInScreenState();
}

class _CheckInScreenState extends ConsumerState<CheckInScreen> {
  final _code = TextEditingController();
  CheckInOutcome? _outcome;
  CheckInDay? _today;
  String? _codeError;
  bool _busy = false;
  String? _lastScan;
  DateTime? _lastScanAt;

  @override
  void initState() {
    super.initState();
    _loadToday();
  }

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _loadToday() async {
    try {
      final today = await ref
          .read(membersRepositoryProvider)
          .checkInsToday(widget.gymId);
      if (mounted) setState(() => _today = today);
    } catch (_) {
      // The list is a convenience; checking in still works without it.
    }
  }

  void _onScan(String value) {
    // The camera reports the same code many times a second.
    final now = DateTime.now();
    final recent =
        _lastScan == value &&
        _lastScanAt != null &&
        now.difference(_lastScanAt!) < const Duration(seconds: 3);
    if (_busy || _outcome != null || recent) return;
    _lastScan = value;
    _lastScanAt = now;
    _submit(value);
  }

  void _submitTyped() {
    final code = normalizeCheckInCode(_code.text);
    if (code == null) {
      setState(
        () => _codeError = 'Enter the 8-character code, e.g. 7KQ2-M9XD.',
      );
      return;
    }
    _submit(code);
  }

  Future<void> _submit(String code) async {
    setState(() {
      _busy = true;
      _codeError = null;
    });
    try {
      final outcome = await ref
          .read(membersRepositoryProvider)
          .checkIn(widget.gymId, code);
      if (!mounted) return;
      HapticFeedback.mediumImpact();
      setState(() {
        _outcome = outcome;
        _busy = false;
      });
      _code.clear();
      _loadToday();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _codeError = memberErrorMessage(error);
      });
    }
  }

  void _next() => setState(() => _outcome = null);

  @override
  Widget build(BuildContext context) {
    final outcome = _outcome;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        title: const Text('Check in'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppSpacing.md),
          children: [
            if (outcome != null)
              _ResultCard(outcome: outcome, onNext: _next)
            else ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(AppRadius.lg),
                child: SizedBox(
                  height: 260,
                  child: (widget.scannerBuilder ?? _cameraScanner)(
                    context,
                    _onScan,
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Text('Or type the code', style: AppTextStyles.labelMedium),
              const SizedBox(height: AppSpacing.xs),
              TextField(
                key: const Key('check-in-code-field'),
                controller: _code,
                textCapitalization: TextCapitalization.characters,
                autocorrect: false,
                enableSuggestions: false,
                textInputAction: TextInputAction.go,
                onSubmitted: (_) => _submitTyped(),
                onChanged: (_) {
                  if (_codeError != null) setState(() => _codeError = null);
                },
                style: AppTextStyles.titleLarge.copyWith(letterSpacing: 2),
                decoration: InputDecoration(
                  hintText: '7KQ2-M9XD',
                  errorText: _codeError,
                  errorMaxLines: 2,
                  filled: true,
                  fillColor: AppColors.surface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    borderSide: const BorderSide(color: AppColors.border),
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              AppPrimaryButton(
                key: const Key('check-in-submit'),
                label: _busy ? 'Checking…' : 'Check in',
                onPressed: _busy ? null : _submitTyped,
              ),
            ],
            const SizedBox(height: AppSpacing.lg),
            _TodayList(today: _today),
          ],
        ),
      ),
    );
  }

  Widget _cameraScanner(BuildContext context, ValueChanged<String> onCode) =>
      MobileScanner(
        onDetect: (capture) {
          final value = capture.barcodes.firstOrNull?.rawValue;
          if (value != null) onCode(value);
        },
        errorBuilder: (context, error) => Container(
          key: const Key('check-in-camera-unavailable'),
          color: AppColors.surface,
          alignment: Alignment.center,
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.no_photography_outlined, size: 36),
              const SizedBox(height: AppSpacing.xs),
              // iOS doesn't always report a refused permission as such, so
              // one message covers both cases.
              Text(
                'Can\'t use the camera. If access is off, allow it for SWETO '
                'in Settings. Meanwhile, type the code below.',
                textAlign: TextAlign.center,
                style: AppTextStyles.bodyMedium,
              ),
            ],
          ),
        ),
      );
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.outcome, required this.onNext});

  final CheckInOutcome outcome;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    final (color, icon, title) = outcome.allowed
        ? outcome.alreadyCheckedInToday
              ? (AppColors.warning, Icons.history, 'Already in today')
              : (AppColors.secondary, Icons.check_circle, 'Allowed in')
        : (AppColors.error, Icons.block, _refusalTitle(outcome.result));
    final visits = outcome.visitLimit == null
        ? null
        : '${outcome.visitsUsed} of ${outcome.visitLimit} visits used';
    return Container(
      key: Key('check-in-result-${outcome.result.apiValue}'),
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .12),
        borderRadius: BorderRadius.circular(AppRadius.xl),
        border: Border.all(color: color, width: 2),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 72),
          const SizedBox(height: AppSpacing.sm),
          Text(
            title,
            style: AppTextStyles.headingLarge.copyWith(color: color),
            textAlign: TextAlign.center,
          ),
          if (outcome.memberName != null) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(
              outcome.memberName!,
              key: const Key('check-in-member-name'),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.center,
              style: AppTextStyles.headingMedium,
            ),
          ],
          const SizedBox(height: AppSpacing.xs),
          Text(
            outcome.message,
            key: const Key('check-in-message'),
            textAlign: TextAlign.center,
            style: AppTextStyles.bodyMedium,
          ),
          if (outcome.planName != null || outcome.paidUntil != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(
              [
                ?outcome.planName,
                if (outcome.paidUntil != null)
                  'paid until ${formatDay(outcome.paidUntil!)}',
                ?visits,
              ].join(' · '),
              textAlign: TextAlign.center,
              style: AppTextStyles.bodySmall,
            ),
          ],
          const SizedBox(height: AppSpacing.lg),
          AppPrimaryButton(
            key: const Key('check-in-next'),
            label: 'Next member',
            onPressed: onNext,
          ),
        ],
      ),
    );
  }

  static String _refusalTitle(CheckInResult result) => switch (result) {
    CheckInResult.expired => 'Membership expired',
    CheckInResult.notStarted => 'Not started yet',
    CheckInResult.noMembership => 'No membership',
    CheckInResult.archived => 'Member archived',
    CheckInResult.visitLimitReached => 'Visits used up',
    _ => 'Code not recognised',
  };
}

class _TodayList extends StatelessWidget {
  const _TodayList({required this.today});

  final CheckInDay? today;

  @override
  Widget build(BuildContext context) {
    final day = today;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text('Today', style: AppTextStyles.titleLarge)),
            if (day != null)
              Text(
                '${day.visits} in · ${day.refused} refused',
                key: const Key('check-in-today-counts'),
                style: AppTextStyles.bodySmall,
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        if (day == null)
          const SizedBox.shrink()
        else if (day.entries.isEmpty)
          Text('No check-ins yet today.', style: AppTextStyles.bodySmall)
        else
          for (final entry in day.entries.take(30))
            ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              leading: Icon(
                entry.result == CheckInResult.allowed
                    ? Icons.check_circle_outline
                    : Icons.block,
                color: entry.result == CheckInResult.allowed
                    ? AppColors.secondary
                    : AppColors.error,
              ),
              title: Text(
                entry.memberName ?? 'Unknown code',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              trailing: Text(
                '${entry.checkedInAt.hour.toString().padLeft(2, '0')}:'
                '${entry.checkedInAt.minute.toString().padLeft(2, '0')}',
                style: AppTextStyles.bodySmall,
              ),
            ),
      ],
    );
  }
}
