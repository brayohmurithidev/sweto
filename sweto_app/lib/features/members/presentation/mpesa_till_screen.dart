import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';
import 'package:sweto_app/shared/widgets/sweto_snackbar.dart';

/// The gym's own Pay Bill or Till that members' M-Pesa payments go to.
class MpesaTillScreen extends ConsumerStatefulWidget {
  const MpesaTillScreen({required this.gymId, super.key});

  final String gymId;

  @override
  ConsumerState<MpesaTillScreen> createState() => _MpesaTillScreenState();
}

class _MpesaTillScreenState extends ConsumerState<MpesaTillScreen> {
  static final _digits = RegExp(r'^\d{5,7}$');

  final _shortcode = TextEditingController();
  final _tillNumber = TextEditingController();
  final _passkey = TextEditingController();
  final _consumerKey = TextEditingController();
  final _consumerSecret = TextEditingController();
  MpesaTill? _saved;
  bool _isTill = true;
  bool _saving = false;
  bool _showPasskey = false;
  bool _showSecret = false;
  String? _loadError;
  String? _shortcodeError;
  String? _tillError;
  String? _passkeyError;
  String? _keysError;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _shortcode.dispose();
    _tillNumber.dispose();
    _passkey.dispose();
    _consumerKey.dispose();
    _consumerSecret.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loadError = null);
    try {
      final till = await ref
          .read(membersRepositoryProvider)
          .getMpesaTill(widget.gymId);
      if (!mounted) return;
      setState(() {
        _saved = till;
        if (till.configured) {
          _isTill = till.isTill;
          _shortcode.text = till.shortcode ?? '';
          _tillNumber.text = till.tillNumber ?? '';
        }
      });
    } catch (error) {
      if (mounted) setState(() => _loadError = memberErrorMessage(error));
    }
  }

  bool _validate() {
    final saved = _saved;
    final passkey = _passkey.text.trim();
    final key = _consumerKey.text.trim();
    final secret = _consumerSecret.text.trim();
    setState(() {
      _keysError = (key.isEmpty) != (secret.isEmpty)
          ? 'Enter both the consumer key and the consumer secret.'
          : key.isEmpty &&
                (saved?.isLive ?? false) &&
                !(saved?.appKeysSaved ?? false)
          ? 'Enter the consumer key and secret from your Daraja app.'
          : null;
      _error = null;
      _shortcodeError = _digits.hasMatch(_shortcode.text.trim())
          ? null
          : 'Enter the 5 to 7 digit number.';
      _tillError = !_isTill || _digits.hasMatch(_tillNumber.text.trim())
          ? null
          : 'Enter the 5 to 7 digit till number.';
      _passkeyError = passkey.isEmpty
          ? (saved?.passkeySaved ?? false)
                ? null
                : 'Enter the passkey from Safaricom.'
          : passkey.length < 20
          ? 'That passkey looks too short.'
          : null;
    });
    return _shortcodeError == null &&
        _tillError == null &&
        _passkeyError == null &&
        _keysError == null;
  }

  Future<void> _save() async {
    if (!_validate()) return;
    setState(() => _saving = true);
    try {
      final passkey = _passkey.text.trim();
      final key = _consumerKey.text.trim();
      final secret = _consumerSecret.text.trim();
      final till = await ref
          .read(membersRepositoryProvider)
          .saveMpesaTill(
            widget.gymId,
            isTill: _isTill,
            shortcode: _shortcode.text.trim(),
            tillNumber: _isTill ? _tillNumber.text.trim() : null,
            passkey: passkey.isEmpty ? null : passkey,
            consumerKey: key.isEmpty ? null : key,
            consumerSecret: secret.isEmpty ? null : secret,
          );
      if (!mounted) return;
      _passkey.clear();
      _consumerKey.clear();
      _consumerSecret.clear();
      setState(() {
        _saved = till;
        _saving = false;
      });
      showSwetoSnackBar(
        context,
        message: 'M-Pesa till saved.',
        type: SwetoSnackBarType.success,
      );
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
    final saved = _saved;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        title: const Text('M-Pesa till'),
      ),
      body: saved == null
          ? Center(
              child: _loadError == null
                  ? const CircularProgressIndicator(color: AppColors.primary)
                  : Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_loadError!, key: const Key('till-load-error')),
                        OutlinedButton(
                          onPressed: _load,
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
            )
          : SafeArea(
              child: ListView(
                padding: const EdgeInsets.all(AppSpacing.md),
                children: [
                  Text(
                    'Members\' M-Pesa payments go straight to this account. '
                    'SWETO only sends the payment prompt and never holds your '
                    'money.',
                    style: AppTextStyles.bodyMedium,
                  ),
                  if (!saved.isLive) ...[
                    const SizedBox(height: AppSpacing.sm),
                    Container(
                      key: const Key('till-test-mode'),
                      padding: const EdgeInsets.all(AppSpacing.sm),
                      decoration: BoxDecoration(
                        color: AppColors.warning.withValues(alpha: .12),
                        borderRadius: BorderRadius.circular(AppRadius.md),
                        border: Border.all(color: AppColors.warning),
                      ),
                      child: Text(
                        'Test mode: M-Pesa isn\'t live on this server yet, so '
                        'no real money moves.',
                        style: AppTextStyles.bodySmall,
                      ),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.md),
                  SegmentedButton<bool>(
                    key: const Key('till-type'),
                    segments: const [
                      ButtonSegment(
                        value: true,
                        label: Text('Till (Buy Goods)'),
                      ),
                      ButtonSegment(value: false, label: Text('Pay Bill')),
                    ],
                    selected: {_isTill},
                    onSelectionChanged: (value) =>
                        setState(() => _isTill = value.first),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  _field(
                    key: 'till-shortcode',
                    controller: _shortcode,
                    label: _isTill
                        ? 'Store number (head office)'
                        : 'Pay Bill number',
                    error: _shortcodeError,
                  ),
                  if (_isTill)
                    _field(
                      key: 'till-number',
                      controller: _tillNumber,
                      label: 'Till number',
                      error: _tillError,
                    ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    'Your gym\'s Daraja app',
                    style: AppTextStyles.titleLarge,
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  _DarajaSteps(
                    key: const ValueKey('daraja-steps'),
                    isTill: _isTill,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  _secretField(
                    key: 'till-consumer-key',
                    controller: _consumerKey,
                    label: saved.appKeysSaved
                        ? 'Consumer key (saved)'
                        : 'Consumer key',
                    saved: saved.appKeysSaved,
                    obscure: false,
                  ),
                  _secretField(
                    key: 'till-consumer-secret',
                    controller: _consumerSecret,
                    label: saved.appKeysSaved
                        ? 'Consumer secret (saved)'
                        : 'Consumer secret',
                    saved: saved.appKeysSaved,
                    obscure: !_showSecret,
                    error: _keysError,
                    onToggle: () => setState(() => _showSecret = !_showSecret),
                  ),
                  TextField(
                    key: const Key('till-passkey'),
                    controller: _passkey,
                    obscureText: !_showPasskey,
                    autocorrect: false,
                    enableSuggestions: false,
                    decoration:
                        _decoration(
                          saved.passkeySaved
                              ? 'Passkey (saved)'
                              : 'Lipa na M-Pesa Online passkey',
                          _passkeyError,
                        ).copyWith(
                          hintText: saved.passkeySaved
                              ? 'Leave empty to keep it'
                              : null,
                          suffixIcon: IconButton(
                            tooltip: _showPasskey ? 'Hide' : 'Show',
                            icon: Icon(
                              _showPasskey
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                            ),
                            onPressed: () =>
                                setState(() => _showPasskey = !_showPasskey),
                          ),
                        ),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    'Your Daraja app shows the passkey after go-live. The keys '
                    'and passkey are stored encrypted and never shown again.',
                    style: AppTextStyles.bodySmall,
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      _error!,
                      key: const Key('till-error'),
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.error,
                      ),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.lg),
                  AppPrimaryButton(
                    key: const Key('till-save'),
                    label: _saving ? 'Saving…' : 'Save',
                    onPressed: _saving ? null : _save,
                  ),
                ],
              ),
            ),
    );
  }

  Widget _secretField({
    required String key,
    required TextEditingController controller,
    required String label,
    required bool saved,
    required bool obscure,
    String? error,
    VoidCallback? onToggle,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: TextField(
      key: Key(key),
      controller: controller,
      obscureText: obscure,
      autocorrect: false,
      enableSuggestions: false,
      decoration: _decoration(label, error).copyWith(
        hintText: saved ? 'Leave empty to keep it' : null,
        suffixIcon: onToggle == null
            ? null
            : IconButton(
                tooltip: obscure ? 'Show' : 'Hide',
                icon: Icon(obscure ? Icons.visibility : Icons.visibility_off),
                onPressed: onToggle,
              ),
      ),
    ),
  );

  Widget _field({
    required String key,
    required TextEditingController controller,
    required String label,
    String? error,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: TextField(
      key: Key(key),
      controller: controller,
      keyboardType: TextInputType.number,
      inputFormatters: [
        FilteringTextInputFormatter.digitsOnly,
        LengthLimitingTextInputFormatter(7),
      ],
      decoration: _decoration(label, error),
    ),
  );

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

/// How a gym gets its own Daraja app keys, as Safaricom describes it.
class _DarajaSteps extends StatelessWidget {
  const _DarajaSteps({required this.isTill, super.key});
  final bool isTill;

  @override
  Widget build(BuildContext context) => Material(
    key: const Key('till-daraja-steps'),
    color: AppColors.surface,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(AppRadius.md),
      side: const BorderSide(color: AppColors.border),
    ),
    clipBehavior: Clip.antiAlias,
    child: Theme(
      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
        childrenPadding: const EdgeInsets.fromLTRB(
          AppSpacing.sm,
          0,
          AppSpacing.sm,
          AppSpacing.sm,
        ),
        leading: const Icon(Icons.help_outline, color: AppColors.primary),
        title: Text('How to get these', style: AppTextStyles.bodyMedium),
        children: [
          for (final (i, step) in [
            'On developer.safaricom.co.ke, create an app with Lipa na M-Pesa '
                'Online.',
            isTill
                ? 'Go Live with the store (head office) number, your business '
                      'name and the primary till operator ID.'
                : 'Go Live with the Pay Bill number, your business name and '
                      'the business administrator or manager username.',
            'Safaricom texts that operator a code. Entering it is how your '
                'gym approves SWETO.',
            'Copy the app\'s consumer key, consumer secret and passkey here.',
          ].indexed)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${i + 1}. ', style: AppTextStyles.bodySmall),
                  Expanded(child: Text(step, style: AppTextStyles.bodySmall)),
                ],
              ),
            ),
        ],
      ),
    ),
  );
}
