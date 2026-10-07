import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/repositories/auth_repository.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';

/// Whether the app currently holds a usable authenticated session.
enum SessionStatus {
  /// The stored session has not been checked yet (cold start).
  unknown,

  /// A valid session exists; authenticated routes are allowed.
  authenticated,

  /// No session; only the public and sign-in routes are allowed.
  unauthenticated,
}

/// Why the most recent session ended, so the sign-in screen can explain it.
enum SessionEndReason {
  /// The user chose to log out.
  loggedOut,

  /// The server rejected the session (refresh failed or token revoked).
  expired,
}

@immutable
class SessionState {
  const SessionState({required this.status, this.endReason});

  const SessionState.unknown() : this(status: SessionStatus.unknown);

  final SessionStatus status;
  final SessionEndReason? endReason;

  bool get isAuthenticated => status == SessionStatus.authenticated;

  @override
  bool operator ==(Object other) =>
      other is SessionState &&
      other.status == status &&
      other.endReason == endReason;

  @override
  int get hashCode => Object.hash(status, endReason);

  @override
  String toString() => 'SessionState($status, endReason: $endReason)';
}

/// Raised when the stored session could not be checked because the server
/// could not be reached. The session is kept so the user can retry.
class SessionRestoreException implements Exception {
  const SessionRestoreException();

  @override
  String toString() => 'SessionRestoreException';
}

const sessionExpiredMessage = 'Your session has expired. Please sign in again.';

/// The single source of truth for whether the user is signed in.
///
/// The router reads this state to decide which routes are reachable, so
/// screens never check authentication themselves. Every way a session starts
/// or ends goes through this controller.
class SessionController extends Notifier<SessionState> {
  static const logoutTimeout = Duration(seconds: 8);

  AuthRepository get _auth => ref.read(authRepositoryProvider);

  @override
  SessionState build() => const SessionState.unknown();

  /// Checks the stored session on app start by rotating the refresh token.
  ///
  /// - No stored token: signed out.
  /// - The server rejects the token: tokens are cleared and the session is
  ///   marked expired.
  /// - The server cannot be reached: tokens are kept and
  ///   [SessionRestoreException] is thrown so the caller can offer a retry.
  Future<SessionStatus> restore() async {
    final refreshToken = await _auth.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      state = const SessionState(status: SessionStatus.unauthenticated);
      return state.status;
    }

    try {
      final tokens = await _auth.refresh(refreshToken);
      await _auth.saveTokens(tokens);
    } on DioException catch (error) {
      if (!isSessionRejection(error)) {
        throw const SessionRestoreException();
      }
      await _clearLocalSession();
      state = const SessionState(
        status: SessionStatus.unauthenticated,
        endReason: SessionEndReason.expired,
      );
      return state.status;
    } on FormatException {
      // A malformed refresh response cannot be trusted as a session.
      await _clearLocalSession();
      state = const SessionState(status: SessionStatus.unauthenticated);
      return state.status;
    }

    state = const SessionState(status: SessionStatus.authenticated);
    return state.status;
  }

  /// Stores tokens from a successful OTP verification and starts the session.
  Future<void> signIn(AuthTokens tokens) async {
    await _auth.saveTokens(tokens);
    state = const SessionState(status: SessionStatus.authenticated);
  }

  /// Ends the session on the server (best effort) and always clears it locally.
  ///
  /// A failed or slow server call never leaves the user signed in on the
  /// device: the local session is cleared regardless.
  Future<void> logout() async {
    try {
      final refreshToken = await _auth.readRefreshToken();
      if (refreshToken != null && refreshToken.isNotEmpty) {
        await _auth.logout(refreshToken).timeout(logoutTimeout);
      }
    } catch (error) {
      // Never log tokens; the status code is enough to diagnose.
      if (kDebugMode) {
        final status = error is DioException
            ? error.response?.statusCode
            : null;
        debugPrint(
          'Server logout failed (${error.runtimeType}, status: $status); '
          'local session cleared anyway.',
        );
      }
    } finally {
      await _clearLocalSession();
      state = const SessionState(
        status: SessionStatus.unauthenticated,
        endReason: SessionEndReason.loggedOut,
      );
    }
  }

  /// Called when the server rejects the session during normal use, for
  /// example when a token refresh fails. Only an active session can expire.
  Future<void> expire() async {
    if (state.status != SessionStatus.authenticated) return;
    await _clearLocalSession();
    state = const SessionState(
      status: SessionStatus.unauthenticated,
      endReason: SessionEndReason.expired,
    );
  }

  /// Clears the reason once the sign-in screen has acted on it.
  void clearEndReason() {
    if (state.endReason == null) return;
    state = SessionState(status: state.status);
  }

  Future<void> _clearLocalSession() async {
    try {
      await _auth.clearTokens();
    } catch (_) {
      if (kDebugMode) debugPrint('Clearing stored tokens failed.');
    }
  }
}

/// True when a token refresh was answered and refused by the server, as
/// opposed to a network or server failure where the session may still be
/// valid. The API answers 401 for invalid, expired or revoked refresh tokens,
/// 403 for suspended accounts and 422 for malformed tokens.
bool isSessionRejection(DioException error) {
  final status = error.response?.statusCode;
  return status == 400 || status == 401 || status == 403 || status == 422;
}

final sessionControllerProvider =
    NotifierProvider<SessionController, SessionState>(SessionController.new);
