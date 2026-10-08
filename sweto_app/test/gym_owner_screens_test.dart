import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/repositories/auth_repository.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';
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

  testWidgets('limited access screen logs out through the session', (
    tester,
  ) async {
    final auth = _AuthFake();
    final container = ProviderContainer(
      overrides: [authRepositoryProvider.overrideWithValue(auth)],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: VerificationPendingScreen()),
      ),
    );

    await tester.tap(find.byKey(const Key('verification-pending-logout')));
    await tester.pump();

    expect(auth.revokedRefreshToken, _storedRefreshToken);
    expect(auth.tokensCleared, isTrue);
    expect(
      container.read(sessionControllerProvider),
      const SessionState(
        status: SessionStatus.unauthenticated,
        endReason: SessionEndReason.loggedOut,
      ),
    );
  });

  testWidgets('unsupported onboarding screen logs out through the session', (
    tester,
  ) async {
    final auth = _AuthFake();
    final container = ProviderContainer(
      overrides: [authRepositoryProvider.overrideWithValue(auth)],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: UnsupportedOnboardingScreen()),
      ),
    );

    await tester.tap(find.byKey(const Key('unsupported-onboarding-logout')));
    await tester.pump();

    expect(auth.revokedRefreshToken, _storedRefreshToken);
    expect(auth.tokensCleared, isTrue);
    expect(
      container.read(sessionControllerProvider).status,
      SessionStatus.unauthenticated,
    );
  });

  testWidgets('onboarding steps offer logout from the account menu', (
    tester,
  ) async {
    final auth = _AuthFake();
    final container = ProviderContainer(
      overrides: [authRepositoryProvider.overrideWithValue(auth)],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: AccountTypeScreen()),
      ),
    );

    await tester.tap(find.byKey(const Key('onboarding-account-menu')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('onboarding-account-menu-logout')));
    await tester.pumpAndSettle();
    expect(find.text('Log out of SWETO?'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Log out'));
    await tester.pumpAndSettle();

    expect(auth.revokedRefreshToken, _storedRefreshToken);
    expect(auth.tokensCleared, isTrue);
    expect(
      container.read(sessionControllerProvider).status,
      SessionStatus.unauthenticated,
    );
  });

  testWidgets('screens with their own logout do not repeat it in a menu', (
    tester,
  ) async {
    await tester.pumpWidget(
      _scope(_AuthFake(), const VerificationPendingScreen()),
    );
    expect(find.byKey(const Key('onboarding-account-menu')), findsNothing);

    await tester.pumpWidget(
      _scope(_AuthFake(), const UnsupportedOnboardingScreen()),
    );
    expect(find.byKey(const Key('onboarding-account-menu')), findsNothing);
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

const _storedRefreshToken = 'stored-refresh-token';

class _AuthFake implements AuthRepository {
  bool roleSelected = false;
  bool tokensCleared = false;
  String? revokedRefreshToken;
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
  Future<String?> readRefreshToken() async =>
      tokensCleared ? null : _storedRefreshToken;
  @override
  Future<AuthTokens> refresh(String refreshToken) => throw UnimplementedError();
  @override
  Future<void> logout(String refreshToken) async {
    revokedRefreshToken = refreshToken;
  }
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
