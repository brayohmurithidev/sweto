import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/cash_payment_form.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';

/// Records cash for [member]; resolves to the refreshed detail, or null.
Future<MemberDetail?> showRecordCashPaymentSheet(
  BuildContext context, {
  required String gymId,
  required GymMember member,
}) => showModalBottomSheet<MemberDetail>(
  context: context,
  isScrollControlled: true,
  backgroundColor: AppColors.background,
  shape: const RoundedRectangleBorder(
    borderRadius: BorderRadius.vertical(
      top: Radius.circular(AppRadius.bottomSheet),
    ),
  ),
  builder: (_) => _RecordCashPaymentSheet(gymId: gymId, member: member),
);

class _RecordCashPaymentSheet extends ConsumerStatefulWidget {
  const _RecordCashPaymentSheet({required this.gymId, required this.member});

  final String gymId;
  final GymMember member;

  @override
  ConsumerState<_RecordCashPaymentSheet> createState() => _SheetState();
}

class _SheetState extends ConsumerState<_RecordCashPaymentSheet> {
  List<GymPricingPlan>? _plans;
  GymPricingPlan? _plan;
  int? _amount;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPlans();
  }

  Future<void> _loadPlans() async {
    setState(() => _error = null);
    try {
      final pricing = await ref
          .read(gymOwnerRepositoryProvider)
          .getGymPricing(widget.gymId);
      if (mounted) setState(() => _plans = sellablePlans(pricing));
    } catch (error) {
      if (mounted) setState(() => _error = memberErrorMessage(error));
    }
  }

  Future<void> _save() async {
    final plan = _plan;
    final amount = _amount;
    if (plan == null || amount == null) {
      setState(() => _error = 'Choose a plan and enter the amount received.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final detail = await ref
          .read(membersRepositoryProvider)
          .recordCashPayment(
            widget.gymId,
            widget.member.id,
            CashPaymentInput(planId: plan.id!, amount: amount),
          );
      if (mounted) Navigator.of(context).pop(detail);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = memberErrorMessage(error);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final plans = _plans;
    return Padding(
      padding: EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.lg + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Record cash payment', style: AppTextStyles.titleLarge),
          const SizedBox(height: 4),
          Text(
            widget.member.fullName,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.bodySmall,
          ),
          const SizedBox(height: AppSpacing.md),
          if (plans == null && _error == null)
            const Center(
              child: CircularProgressIndicator(color: AppColors.primary),
            )
          else if (plans != null)
            CashPaymentForm(
              plans: plans,
              onChanged: (plan, amount) => setState(() {
                _plan = plan;
                _amount = amount;
              }),
            ),
          if (_error != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(
              _error!,
              key: const Key('cash-payment-error'),
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          if (plans == null && _error != null)
            AppPrimaryButton(label: 'Retry', onPressed: _loadPlans)
          else
            AppPrimaryButton(
              key: const Key('cash-payment-submit'),
              label: _saving ? 'Saving…' : 'Confirm payment',
              onPressed: _saving || plans == null || plans.isEmpty
                  ? null
                  : _save,
            ),
        ],
      ),
    );
  }
}
