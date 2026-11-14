import 'dart:async';

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
import 'package:sweto_app/features/members/presentation/member_formatting.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';

/// Sends an M-Pesa prompt and waits for the member's PIN.
///
/// Resolves to the payment once it completes; null if closed before then
/// (a pending payment still completes in the background).
Future<MpesaPayment?> showMpesaPaymentSheet(
  BuildContext context, {
  required String gymId,
  required GymMember member,
  Duration pollEvery = const Duration(seconds: 3),
  Duration giveUpAfter = const Duration(minutes: 2),
}) => showModalBottomSheet<MpesaPayment>(
  context: context,
  isScrollControlled: true,
  isDismissible: false,
  backgroundColor: AppColors.background,
  shape: const RoundedRectangleBorder(
    borderRadius: BorderRadius.vertical(
      top: Radius.circular(AppRadius.bottomSheet),
    ),
  ),
  builder: (_) => _MpesaSheet(
    gymId: gymId,
    member: member,
    pollEvery: pollEvery,
    giveUpAfter: giveUpAfter,
  ),
);

class _MpesaSheet extends ConsumerStatefulWidget {
  const _MpesaSheet({
    required this.gymId,
    required this.member,
    required this.pollEvery,
    required this.giveUpAfter,
  });

  final String gymId;
  final GymMember member;
  final Duration pollEvery;
  final Duration giveUpAfter;

  @override
  ConsumerState<_MpesaSheet> createState() => _MpesaSheetState();
}

class _MpesaSheetState extends ConsumerState<_MpesaSheet> {
  List<GymPricingPlan>? _plans;
  GymPricingPlan? _plan;
  int? _amount;
  String? _error;
  bool _sending = false;
  MpesaPayment? _payment;
  bool _stillWaiting = false;
  Timer? _poll;
  int _checks = 0;

  @override
  void initState() {
    super.initState();
    _loadPlans();
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _loadPlans() async {
    try {
      final pricing = await ref
          .read(gymOwnerRepositoryProvider)
          .getGymPricing(widget.gymId);
      if (mounted) setState(() => _plans = sellablePlans(pricing));
    } catch (error) {
      if (mounted) setState(() => _error = memberErrorMessage(error));
    }
  }

  Future<void> _send() async {
    final plan = _plan;
    if (plan == null || _amount == null) {
      setState(() => _error = 'Choose a plan and check the amount.');
      return;
    }
    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      final payment = await ref
          .read(membersRepositoryProvider)
          .requestMpesaPayment(
            widget.gymId,
            widget.member.id,
            planId: plan.id!,
            amount: _amount,
          );
      if (!mounted) return;
      setState(() {
        _payment = payment;
        _sending = false;
        _checks = 0;
      });
      _poll = Timer.periodic(widget.pollEvery, (_) => _check());
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _sending = false;
        _error = memberErrorMessage(error);
      });
    }
  }

  Future<void> _check() async {
    final current = _payment;
    if (current == null) return;
    try {
      final payment = await ref
          .read(membersRepositoryProvider)
          .getPayment(widget.gymId, current.paymentId);
      if (!mounted) return;
      setState(() => _payment = payment);
      if (payment.state != PaymentState.pending) {
        _poll?.cancel();
        if (payment.state == PaymentState.completed) {
          Navigator.of(context).pop(payment);
        }
        return;
      }
    } catch (_) {
      // A missed check is retried on the next tick.
    }
    _checks += 1;
    if (widget.pollEvery * _checks >= widget.giveUpAfter) {
      _poll?.cancel();
      if (mounted) setState(() => _stillWaiting = true);
    }
  }

  void _tryAgain() => setState(() {
    _payment = null;
    _stillWaiting = false;
    _error = null;
  });

  @override
  Widget build(BuildContext context) {
    final payment = _payment;
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
          Text('M-Pesa payment', style: AppTextStyles.titleLarge),
          const SizedBox(height: 4),
          Text(
            '${widget.member.fullName} · ${widget.member.phoneNumber}',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.bodySmall,
          ),
          const SizedBox(height: AppSpacing.md),
          if (payment == null) ..._requestForm() else ..._waiting(payment),
        ],
      ),
    );
  }

  List<Widget> _requestForm() {
    final plans = _plans;
    return [
      if (plans == null && _error == null)
        const Center(child: CircularProgressIndicator(color: AppColors.primary))
      else if (plans != null)
        CashPaymentForm(
          plans: plans,
          amountLabel: 'Amount to request (KES)',
          onChanged: (plan, amount) => setState(() {
            _plan = plan;
            _amount = amount;
          }),
        ),
      if (_error != null) ...[
        const SizedBox(height: AppSpacing.sm),
        Text(
          _error!,
          key: const Key('mpesa-error'),
          style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
        ),
      ],
      const SizedBox(height: AppSpacing.md),
      AppPrimaryButton(
        key: const Key('mpesa-send'),
        label: _sending ? 'Sending…' : 'Send M-Pesa prompt',
        onPressed: _sending || plans == null || plans.isEmpty ? null : _send,
      ),
      TextButton(
        onPressed: _sending ? null : () => Navigator.of(context).pop(),
        child: const Text('Cancel'),
      ),
    ];
  }

  List<Widget> _waiting(MpesaPayment payment) {
    final failed = payment.state == PaymentState.failed;
    return [
      Container(
        key: Key('mpesa-state-${payment.state.name}'),
        padding: const EdgeInsets.all(AppSpacing.lg),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(
            color: failed ? AppColors.error : AppColors.border,
          ),
        ),
        child: Column(
          children: [
            if (failed)
              const Icon(Icons.error_outline, color: AppColors.error, size: 48)
            else
              const SizedBox(
                width: 40,
                height: 40,
                child: CircularProgressIndicator(color: AppColors.primary),
              ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              failed
                  ? payment.message
                  : _stillWaiting
                  ? 'Still waiting for M-Pesa. You can close this: the '
                        'membership updates by itself when the payment '
                        'comes through.'
                  : 'Waiting for ${widget.member.fullName} to enter their '
                        'M-Pesa PIN…',
              key: const Key('mpesa-message'),
              textAlign: TextAlign.center,
              style: AppTextStyles.bodyMedium,
            ),
          ],
        ),
      ),
      const SizedBox(height: AppSpacing.md),
      if (failed)
        AppPrimaryButton(
          key: const Key('mpesa-try-again'),
          label: 'Try again',
          onPressed: _tryAgain,
        ),
      TextButton(
        key: const Key('mpesa-close'),
        onPressed: () => Navigator.of(context).pop(),
        child: const Text('Close'),
      ),
    ];
  }
}

/// Snack-bar text after a completed M-Pesa payment.
String mpesaPaidMessage(MpesaPayment payment) {
  final until = payment.paidUntil;
  final receipt = payment.receipt == null ? '' : ' Receipt ${payment.receipt}.';
  return until == null
      ? 'M-Pesa payment received.$receipt'
      : 'M-Pesa payment received. Paid until ${formatDay(until)}.$receipt';
}
