import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';

/// Plan picker and amount (prefilled from the plan) for a cash payment.
class CashPaymentForm extends StatefulWidget {
  const CashPaymentForm({
    required this.plans,
    required this.onChanged,
    this.amountLabel = 'Amount received (KES)',
    super.key,
  });

  final String amountLabel;

  /// Active, saved membership plans.
  final List<GymPricingPlan> plans;

  /// The chosen plan and the amount typed (null when not a whole number > 0).
  final void Function(GymPricingPlan? plan, int? amount) onChanged;

  @override
  State<CashPaymentForm> createState() => _CashPaymentFormState();
}

class _CashPaymentFormState extends State<CashPaymentForm> {
  late GymPricingPlan? _plan = widget.plans.isEmpty ? null : widget.plans.first;
  late final _amount = TextEditingController(
    text: _plan == null ? '' : '${_plan!.amount}',
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _notify());
  }

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  int? get _parsedAmount {
    final value = int.tryParse(_amount.text.replaceAll(',', '').trim());
    return value != null && value > 0 ? value : null;
  }

  void _notify() {
    if (mounted) widget.onChanged(_plan, _parsedAmount);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.plans.isEmpty) {
      return Text(
        'Add a membership plan in your pricing first.',
        key: const Key('cash-no-plans'),
        style: AppTextStyles.bodySmall.copyWith(color: AppColors.warning),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        DropdownButtonFormField<GymPricingPlan>(
          key: const Key('cash-plan-field'),
          initialValue: _plan,
          isExpanded: true,
          decoration: _decoration('Plan'),
          dropdownColor: AppColors.surfaceElevated,
          items: [
            for (final plan in widget.plans)
              DropdownMenuItem(
                value: plan,
                child: Text(
                  '${plan.name} · KES ${plan.amount}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
          ],
          onChanged: (plan) {
            setState(() {
              _plan = plan;
              _amount.text = plan == null ? '' : '${plan.amount}';
            });
            _notify();
          },
        ),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          key: const Key('cash-amount-field'),
          controller: _amount,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: _decoration(widget.amountLabel),
          onChanged: (_) => _notify(),
        ),
      ],
    );
  }

  InputDecoration _decoration(String label) => InputDecoration(
    labelText: label,
    filled: true,
    fillColor: AppColors.surface,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(AppRadius.md),
      borderSide: const BorderSide(color: AppColors.border),
    ),
  );
}

/// Active membership plans that can be sold (saved, so they have an ID).
List<GymPricingPlan> sellablePlans(GymPricing pricing) => [
  for (final plan in pricing.membershipPlans)
    if (plan.isActive && plan.id != null) plan,
];
