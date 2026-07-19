import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/repositories/auth_repository.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/gym_owner/presentation/gym_owner_screens.dart';

void main() {
  testWidgets('member card shows Coming Soon and does not submit member role', (
    tester,
  ) async {
    final auth = _AuthFake();
    await tester.pumpWidget(_scope(auth, const AccountTypeScreen()));
    expect(find.text('Coming Soon'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('account-type-continue')));
    await tester.tap(find.byKey(const Key('account-type-continue')));
    await tester.pumpAndSettle();
    expect(find.text('Member access is coming soon'), findsOneWidget);
    expect(auth.roleSelected, isFalse);
  });

  testWidgets('gym owner card enables continue and form requires gym name', (
    tester,
  ) async {
    await tester.pumpWidget(_scope(_AuthFake(), const AccountTypeScreen()));
    await tester.tap(find.byKey(const Key('gym-owner-role-card')));
    await tester.pump();
    final button = tester.widget<FilledButton>(find.byType(FilledButton).last);
    expect(button.onPressed, isNotNull);

    await tester.pumpWidget(_scope(_AuthFake(), const GymRegistrationScreen()));
    await tester.ensureVisible(find.byKey(const Key('create-gym-button')));
    await tester.tap(find.byKey(const Key('create-gym-button')));
    await tester.pump();
    expect(find.text('Enter your gym name.'), findsOneWidget);
  });

  testWidgets('limited access screen can log out', (tester) async {
    final auth = _AuthFake();
    final router = GoRouter(
      initialLocation: '/pending',
      routes: [
        GoRoute(
          path: '/pending',
          builder: (_, _) => const VerificationPendingScreen(),
        ),
        GoRoute(
          path: '/phone',
          name: AppRoutes.phoneLoginName,
          builder: (_, _) => const Text('Phone login'),
        ),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authRepositoryProvider.overrideWithValue(auth)],
        child: MaterialApp.router(routerConfig: router),
      ),
    );

    await tester.tap(find.byKey(const Key('verification-pending-logout')));
    await tester.pumpAndSettle();

    expect(auth.tokensCleared, isTrue);
    expect(find.text('Phone login'), findsOneWidget);
  });

  testWidgets('unsupported onboarding screen uses recovery language', (
    tester,
  ) async {
    await tester.pumpWidget(
      _scope(_AuthFake(), const UnsupportedOnboardingScreen()),
    );
    expect(find.text('Continue setting up your gym'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
    expect(find.text('Sign out'), findsOneWidget);
    expect(find.textContaining('unsupported'), findsNothing);
  });
}

ProviderScope _scope(_AuthFake auth, Widget child) => ProviderScope(
  overrides: [authRepositoryProvider.overrideWithValue(auth)],
  child: MaterialApp(home: child),
);

class _AuthFake implements AuthRepository {
  bool roleSelected = false;
  bool tokensCleared = false;
  @override
  Future<void> clearTokens() async {
    tokensCleared = true;
  }

  @override
  Future<AuthUser> getMe() async => const AuthUser(
    id: 'user',
    mustChangePassword: false,
    phoneNumber: '+254712345678',
  );
  @override
  Future<AccountOnboarding> getOnboarding() async => const AccountOnboarding(
    roles: [AccountRole.gymOwner],
    defaultRole: AccountRole.gymOwner,
    status: AccountOnboardingStatus.gymSetupPending,
    completed: false,
    nextStep: 'gym_setup',
  );
  @override
  Future<String?> readRefreshToken() async => null;
  @override
  Future<AuthTokens> refresh(String refreshToken) => throw UnimplementedError();
  @override
  Future<OtpChallenge> requestOtp(String phoneNumber) =>
      throw UnimplementedError();
  @override
  Future<void> saveTokens(AuthTokens tokens) async {}
  @override
  Future<AccountOnboarding> selectGymOwnerRole() async {
    roleSelected = true;
    return getOnboarding();
  }

  @override
  Future<AuthTokens> verifyOtp({
    required String challengeId,
    required String code,
  }) => throw UnimplementedError();
}
