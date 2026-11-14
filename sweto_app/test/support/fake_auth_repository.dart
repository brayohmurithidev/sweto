import 'package:dio/dio.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/repositories/auth_repository.dart';

/// In-memory [AuthRepository] for session tests. Tokens live in fields so
/// tests can assert exactly what was stored, cleared and revoked.
class FakeAuthRepository implements AuthRepository {
  FakeAuthRepository({this.refreshToken, this.nextStep = 'choose_account'});

  String? refreshToken;
  String? accessToken;
  String nextStep;

  /// When set, [refresh] throws this instead of returning new tokens.
  DioException? refreshError;

  /// When set, [logout] throws this to simulate a failed server logout.
  Object? logoutError;

  final List<String> revokedRefreshTokens = [];
  int clearCount = 0;
  int refreshCount = 0;

  static const issuedTokens = AuthTokens(
    accessToken: 'issued-access-token',
    refreshToken: 'issued-refresh-token-0123456789-0123456789-0123',
  );

  @override
  Future<String?> readRefreshToken() async => refreshToken;

  @override
  Future<void> saveTokens(AuthTokens tokens) async {
    accessToken = tokens.accessToken;
    refreshToken = tokens.refreshToken;
  }

  @override
  Future<void> clearTokens() async {
    clearCount++;
    accessToken = null;
    refreshToken = null;
  }

  @override
  Future<AuthTokens> refresh(String refreshToken) async {
    refreshCount++;
    final error = refreshError;
    if (error != null) throw error;
    return issuedTokens;
  }

  @override
  Future<void> logout(String refreshToken) async {
    revokedRefreshTokens.add(refreshToken);
    final error = logoutError;
    if (error != null) throw error;
  }

  @override
  Future<AuthTokens> verifyOtp({
    required String challengeId,
    required String code,
  }) async => issuedTokens;

  /// E.164 numbers passed to [requestOtp], in order.
  final List<String> requestedPhoneNumbers = [];

  /// Mirrors the API's channel policy: SMS in Kenya, WhatsApp elsewhere.
  @override
  Future<OtpChallenge> requestOtp(String phoneNumber) async {
    requestedPhoneNumbers.add(phoneNumber);
    return OtpChallenge(
      challengeId: 'challenge',
      phoneNumber: phoneNumber,
      expiresAt: DateTime.now().add(const Duration(minutes: 5)),
      resendAvailableAt: DateTime.now().add(const Duration(seconds: 60)),
      deliveryChannel: phoneNumber.startsWith('+254')
          ? OtpDeliveryChannel.sms
          : OtpDeliveryChannel.whatsapp,
    );
  }

  @override
  Future<AuthUser> getMe() async =>
      const AuthUser(id: 'user', mustChangePassword: false);

  @override
  Future<AccountOnboarding> getOnboarding() async => AccountOnboarding(
    roles: const [AccountRole.gymOwner],
    defaultRole: AccountRole.gymOwner,
    status: AccountOnboardingStatus.accountSelectionPending,
    completed: false,
    nextStep: nextStep,
  );

  @override
  Future<AccountOnboarding> selectGymOwnerRole() => throw UnimplementedError();
}

/// A response the server would send when it refuses a refresh token.
DioException rejectedRefresh() {
  final options = RequestOptions(path: '/api/v1/auth/refresh');
  return DioException(
    requestOptions: options,
    response: Response<void>(requestOptions: options, statusCode: 401),
    type: DioExceptionType.badResponse,
  );
}

/// A refresh attempt that never reached the server.
DioException unreachableRefresh() => DioException(
  requestOptions: RequestOptions(path: '/api/v1/auth/refresh'),
  type: DioExceptionType.connectionError,
);
