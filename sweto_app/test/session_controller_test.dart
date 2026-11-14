import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';

import 'support/fake_auth_repository.dart';

void main() {
  late FakeAuthRepository auth;
  late ProviderContainer container;

  SessionController controller() =>
      container.read(sessionControllerProvider.notifier);
  SessionState session() => container.read(sessionControllerProvider);

  void createContainer(FakeAuthRepository repository) {
    auth = repository;
    container = ProviderContainer(
      overrides: [authRepositoryProvider.overrideWithValue(repository)],
    );
    addTearDown(container.dispose);
  }

  test('starts unknown until the stored session is checked', () {
    createContainer(FakeAuthRepository());
    expect(session().status, SessionStatus.unknown);
  });

  group('restore', () {
    test('no stored refresh token means signed out', () async {
      createContainer(FakeAuthRepository());

      expect(await controller().restore(), SessionStatus.unauthenticated);
      expect(session().endReason, isNull);
      expect(auth.refreshCount, 0);
    });

    test('a valid stored session is rotated and signed in', () async {
      createContainer(FakeAuthRepository(refreshToken: 'stored-refresh'));

      expect(await controller().restore(), SessionStatus.authenticated);
      expect(
        auth.refreshToken,
        FakeAuthRepository.issuedTokens.refreshToken,
      );
    });

    test('a rejected session is cleared and marked expired', () async {
      createContainer(
        FakeAuthRepository(refreshToken: 'stored-refresh')
          ..refreshError = rejectedRefresh(),
      );

      expect(await controller().restore(), SessionStatus.unauthenticated);
      expect(session().endReason, SessionEndReason.expired);
      expect(auth.refreshToken, isNull);
      expect(auth.clearCount, 1);
    });

    test('a network failure keeps the session and asks for a retry', () async {
      createContainer(
        FakeAuthRepository(refreshToken: 'stored-refresh')
          ..refreshError = unreachableRefresh(),
      );

      await expectLater(
        controller().restore(),
        throwsA(isA<SessionRestoreException>()),
      );
      expect(auth.refreshToken, 'stored-refresh');
      expect(auth.clearCount, 0);
      expect(session().status, SessionStatus.unknown);
    });
  });

  test('signIn stores the tokens and starts the session', () async {
    createContainer(FakeAuthRepository());

    await controller().signIn(FakeAuthRepository.issuedTokens);

    expect(session().status, SessionStatus.authenticated);
    expect(auth.accessToken, FakeAuthRepository.issuedTokens.accessToken);
  });

  group('logout', () {
    test('revokes the session on the server and clears it locally', () async {
      createContainer(FakeAuthRepository());
      await controller().signIn(FakeAuthRepository.issuedTokens);

      await controller().logout();

      expect(auth.revokedRefreshTokens, [
        FakeAuthRepository.issuedTokens.refreshToken,
      ]);
      expect(auth.refreshToken, isNull);
      expect(
        session(),
        const SessionState(
          status: SessionStatus.unauthenticated,
          endReason: SessionEndReason.loggedOut,
        ),
      );
    });

    test('a server failure still clears the local session', () async {
      createContainer(FakeAuthRepository()..logoutError = unreachableRefresh());
      await controller().signIn(FakeAuthRepository.issuedTokens);

      await controller().logout();

      expect(auth.revokedRefreshTokens, hasLength(1));
      expect(auth.refreshToken, isNull);
      expect(auth.accessToken, isNull);
      expect(session().status, SessionStatus.unauthenticated);
    });
  });

  group('expire', () {
    test('ends an active session and records why', () async {
      createContainer(FakeAuthRepository());
      await controller().signIn(FakeAuthRepository.issuedTokens);

      await controller().expire();

      expect(session().status, SessionStatus.unauthenticated);
      expect(session().endReason, SessionEndReason.expired);
      expect(auth.refreshToken, isNull);
    });

    test('does nothing when there is no active session', () async {
      createContainer(FakeAuthRepository());
      await controller().restore();

      await controller().expire();

      expect(session().endReason, isNull);
      expect(auth.clearCount, 0);
    });

    test('the user can sign in again after expiry', () async {
      createContainer(FakeAuthRepository());
      await controller().signIn(FakeAuthRepository.issuedTokens);
      await controller().expire();

      await controller().signIn(FakeAuthRepository.issuedTokens);

      expect(
        session(),
        const SessionState(status: SessionStatus.authenticated),
      );
    });
  });

  test('clearEndReason keeps the status and drops the reason', () async {
    createContainer(FakeAuthRepository());
    await controller().signIn(FakeAuthRepository.issuedTokens);
    await controller().expire();

    controller().clearEndReason();

    expect(
      session(),
      const SessionState(status: SessionStatus.unauthenticated),
    );
  });
}
