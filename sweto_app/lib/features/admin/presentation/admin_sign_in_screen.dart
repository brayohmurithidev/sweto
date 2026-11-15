import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/admin/domain/admin_entities.dart';
import 'package:sweto_app/features/admin/presentation/admin_providers.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';

/// Email and password sign-in for SWETO staff who review gyms.
///
/// A first sign-in with a generated password must replace it before any
/// admin action. That happens here too, with the sign-in's token held only
/// in memory: nothing is stored until the new password works.
class AdminSignInScreen extends ConsumerStatefulWidget {
  const AdminSignInScreen({super.key});

  @override
  ConsumerState<AdminSignInScreen> createState() => _AdminSignInScreenState();
}

class _AdminSignInScreenState extends ConsumerState<AdminSignInScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _newPassword = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  String? _error;

  /// Set after a sign-in that must change its password first.
  AdminSignIn? _pendingChange;

  static const _minPasswordLength = 12;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _newPassword.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _signIn() async {
    final email = _email.text.trim();
    if (!email.contains('@') || _password.text.isEmpty) {
      setState(() => _error = 'Enter your staff email and password.');
      return;
    }
    await _run(() async {
      final result = await ref
          .read(adminRepositoryProvider)
          .signIn(email: email, password: _password.text);
      if (result.mustChangePassword) {
        if (mounted) setState(() => _pendingChange = result);
        return;
      }
      await _finish(result);
    });
  }

  Future<void> _changePassword() async {
    final pending = _pendingChange;
    if (pending == null) return;
    final next = _newPassword.text;
    if (next.length < _minPasswordLength) {
      setState(
        () => _error =
            'Use at least $_minPasswordLength characters, ideally from a '
            'password manager.',
      );
      return;
    }
    if (next != _confirm.text) {
      setState(() => _error = 'The two new passwords don\'t match.');
      return;
    }
    if (next == _password.text) {
      setState(() => _error = 'Choose a password different from the old one.');
      return;
    }
    await _run(() async {
      final admin = ref.read(adminRepositoryProvider);
      await admin.changePassword(
        accessToken: pending.tokens.accessToken,
        currentPassword: _password.text,
        newPassword: next,
      );
      // Changing the password ends every session; sign in with the new one.
      final fresh = await admin.signIn(
        email: _email.text.trim(),
        password: next,
      );
      await _finish(fresh);
    });
  }

  Future<void> _finish(AdminSignIn result) async {
    await ref.read(sessionControllerProvider.notifier).signIn(result.tokens);
    if (mounted) context.goNamed(AppRoutes.splashName);
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (error) {
      final message = error is DioException && error.response?.statusCode == 422
          ? 'Check the email address and try again.'
          : memberErrorMessage(error);
      if (mounted) setState(() => _error = message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final changing = _pendingChange != null;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        leading: IconButton(
          tooltip: 'Back',
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop()
              ? context.pop()
              : context.goNamed(AppRoutes.phoneLoginName),
        ),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
          children: [
            Text(
              changing ? 'Set a new password' : 'Staff sign-in',
              style: AppTextStyles.headingLarge,
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              changing
                  ? 'Your password was generated for you. Replace it before '
                        'reviewing gyms.'
                  : 'For SWETO staff who review gyms. Gym owners sign in '
                        'with their phone number.',
              style: AppTextStyles.bodyMedium,
            ),
            const SizedBox(height: AppSpacing.lg),
            if (!changing) ...[
              _field(
                _email,
                'Email',
                key: 'admin-email',
                keyboardType: TextInputType.emailAddress,
              ),
              _field(
                _password,
                'Password',
                key: 'admin-password',
                obscure: true,
              ),
            ] else ...[
              _field(
                _newPassword,
                'New password',
                key: 'admin-new-password',
                obscure: true,
              ),
              _field(
                _confirm,
                'New password again',
                key: 'admin-confirm-password',
                obscure: true,
              ),
            ],
            if (_error != null) ...[
              Text(
                _error!,
                key: const Key('admin-sign-in-error'),
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
              ),
              const SizedBox(height: AppSpacing.sm),
            ],
            AppPrimaryButton(
              key: const Key('admin-sign-in-submit'),
              label: _busy
                  ? 'Please wait…'
                  : changing
                  ? 'Save and continue'
                  : 'Sign in',
              onPressed: _busy ? null : (changing ? _changePassword : _signIn),
            ),
          ],
        ),
      ),
    );
  }

  Widget _field(
    TextEditingController controller,
    String label, {
    required String key,
    bool obscure = false,
    TextInputType? keyboardType,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: TextField(
      key: Key(key),
      controller: controller,
      obscureText: obscure,
      autocorrect: false,
      enableSuggestions: false,
      keyboardType: keyboardType,
      onChanged: (_) {
        if (_error != null) setState(() => _error = null);
      },
      decoration: InputDecoration(
        labelText: label,
        filled: true,
        fillColor: AppColors.surface,
      ),
    ),
  );
}
