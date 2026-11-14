import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/phone/phone_country.dart';
import 'package:sweto_app/core/phone/phone_number.dart';
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
import 'package:sweto_app/shared/widgets/phone_number_field.dart';
import 'package:sweto_app/shared/widgets/sweto_snackbar.dart';

/// How far back a first payment can start (matches the API).
const backdateLimitDays = 90;

class AddMemberScreen extends ConsumerStatefulWidget {
  const AddMemberScreen({required this.gymId, this.today, super.key});

  final String gymId;

  /// Overrides "today" in tests.
  final DateTime? today;

  @override
  ConsumerState<AddMemberScreen> createState() => _AddMemberScreenState();
}

class _AddMemberScreenState extends ConsumerState<AddMemberScreen> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _phoneFocus = FocusNode();
  PhoneCountry _country = kenya;
  String? _nameError;
  String? _phoneError;
  String? _error;
  bool _saving = false;

  List<GymPricingPlan>? _plans;
  String? _gymName;
  bool _smsConsent = false;
  bool _recordPayment = true;
  GymPricingPlan? _plan;
  int? _amount;
  DateTime? _startedOn;

  DateTime get _today {
    final now = widget.today ?? DateTime.now();
    return DateTime(now.year, now.month, now.day);
  }

  @override
  void initState() {
    super.initState();
    _loadPlans();
    _loadGymName();
  }

  Future<void> _loadGymName() async {
    try {
      final gym = await ref.read(gymOwnerRepositoryProvider).getCurrentGym();
      if (mounted) setState(() => _gymName = gym.name);
    } catch (_) {
      // The consent line falls back to "your gym".
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _phoneFocus.dispose();
    super.dispose();
  }

  Future<void> _loadPlans() async {
    try {
      final pricing = await ref
          .read(gymOwnerRepositoryProvider)
          .getGymPricing(widget.gymId);
      if (!mounted) return;
      final plans = sellablePlans(pricing);
      setState(() {
        _plans = plans;
        _recordPayment = plans.isNotEmpty;
      });
    } catch (_) {
      // Adding a member still works; the payment can be recorded later.
      if (mounted) {
        setState(() {
          _plans = const [];
          _recordPayment = false;
        });
      }
    }
  }

  Future<void> _pickStartDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _startedOn ?? _today,
      firstDate: _today.subtract(const Duration(days: backdateLimitDays)),
      lastDate: _today,
      helpText: 'When did this membership start?',
    );
    if (picked != null) setState(() => _startedOn = picked);
  }

  bool _validate() {
    final name = _name.text.trim();
    final phone = _phone.text.trim();
    setState(() {
      _error = null;
      _nameError = name.length < 2 ? 'Enter the member\'s name.' : null;
      _phoneError = phone.isEmpty
          ? 'Enter the member\'s phone number.'
          : !PhoneNumbers.isValid(_country, phone)
          ? 'Enter a valid mobile number for ${_country.name}.'
          : null;
      if (_recordPayment && (_plan == null || _amount == null)) {
        _error = 'Choose a plan and enter the amount received.';
      }
    });
    return _nameError == null && _phoneError == null && _error == null;
  }

  Future<void> _save() async {
    if (!_validate()) return;
    setState(() => _saving = true);
    final repository = ref.read(membersRepositoryProvider);
    final GymMember member;
    try {
      member = await repository.addMember(
        widget.gymId,
        fullName: _name.text.trim(),
        phoneNumber: PhoneNumbers.toE164(_country, _phone.text.trim()),
        smsConsent: _smsConsent,
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = memberErrorMessage(error);
      });
      return;
    }

    String? paymentError;
    String? smsStatus;
    if (_recordPayment) {
      try {
        final detail = await repository.recordCashPayment(
          widget.gymId,
          member.id,
          CashPaymentInput(
            planId: _plan!.id!,
            amount: _amount,
            startsOn: _startedOn == _today ? null : _startedOn,
          ),
        );
        smsStatus = detail.smsStatus;
      } catch (error) {
        paymentError = memberErrorMessage(error);
      }
    }
    if (!mounted) return;
    showSwetoSnackBar(
      context,
      message: paymentError != null
          ? 'Member added, but the payment wasn\'t saved: $paymentError'
          : switch (smsStatus) {
              'sent' => '${member.fullName} added. Welcome SMS sent.',
              'failed' =>
                '${member.fullName} added. The welcome SMS couldn\'t be sent.',
              _ => '${member.fullName} added.',
            },
      type: paymentError == null
          ? SwetoSnackBarType.success
          : SwetoSnackBarType.warning,
      duration: Duration(seconds: paymentError == null ? 3 : 6),
    );
    // The list opens the new member, so it can refresh first.
    context.pop(member.id);
  }

  @override
  Widget build(BuildContext context) {
    final plans = _plans;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        title: const Text('Add member'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppSpacing.md),
          children: [
            TextField(
              key: const Key('member-name-field'),
              controller: _name,
              textCapitalization: TextCapitalization.words,
              decoration: _decoration('Full name', _nameError),
              onChanged: (_) => setState(() => _nameError = null),
            ),
            const SizedBox(height: AppSpacing.sm),
            PhoneNumberField(
              key: const Key('member-phone-field'),
              fieldKey: const Key('member-phone-input'),
              compact: true,
              country: _country,
              onCountryChanged: (country) => setState(() {
                _country = country;
                _phoneError = null;
              }),
              controller: _phone,
              focusNode: _phoneFocus,
              errorText: _phoneError,
              onChanged: (_) => setState(() => _phoneError = null),
            ),
            CheckboxListTile(
              key: const Key('member-sms-consent'),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _smsConsent,
              onChanged: (value) =>
                  setState(() => _smsConsent = value ?? false),
              title: Text(
                'Member agreed to receive SMS from ${_gymName ?? 'your gym'}',
              ),
              subtitle: Text(
                'Welcome with their check-in code, receipts and expiry '
                'reminders. Leave unticked if they didn\'t agree.',
                style: AppTextStyles.bodySmall,
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            if (plans == null)
              const LinearProgressIndicator(color: AppColors.primary)
            else ...[
              SwitchListTile(
                key: const Key('member-record-payment'),
                contentPadding: EdgeInsets.zero,
                value: _recordPayment,
                onChanged: plans.isEmpty
                    ? null
                    : (value) => setState(() => _recordPayment = value),
                title: const Text('Record a cash payment now'),
                subtitle: Text(
                  plans.isEmpty
                      ? 'Add a membership plan in your pricing first.'
                      : 'You can also record it later.',
                  style: AppTextStyles.bodySmall,
                ),
              ),
              if (_recordPayment) ...[
                const SizedBox(height: AppSpacing.xs),
                CashPaymentForm(
                  plans: plans,
                  onChanged: (plan, amount) => setState(() {
                    _plan = plan;
                    _amount = amount;
                  }),
                ),
                const SizedBox(height: AppSpacing.xs),
                ListTile(
                  key: const Key('member-start-date'),
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.event, color: AppColors.primary),
                  title: Text(
                    _startedOn == null || _startedOn == _today
                        ? 'Starts today'
                        : 'Started ${formatDay(_startedOn!)}',
                  ),
                  subtitle: Text(
                    'Paid earlier? Pick the start date (up to '
                    '$backdateLimitDays days back).',
                    style: AppTextStyles.bodySmall,
                  ),
                  onTap: _pickStartDate,
                ),
              ],
            ],
            if (_error != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                _error!,
                key: const Key('add-member-error'),
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
              ),
            ],
            const SizedBox(height: AppSpacing.lg),
            AppPrimaryButton(
              key: const Key('add-member-submit'),
              label: _saving ? 'Saving…' : 'Add member',
              onPressed: _saving ? null : _save,
            ),
          ],
        ),
      ),
    );
  }

  InputDecoration _decoration(String label, String? error) => InputDecoration(
    labelText: label,
    errorText: error,
    filled: true,
    fillColor: AppColors.surface,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(AppRadius.md),
      borderSide: const BorderSide(color: AppColors.border),
    ),
  );
}
