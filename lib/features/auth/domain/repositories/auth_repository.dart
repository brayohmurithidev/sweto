import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';

abstract interface class AuthRepository {
  Future<OtpChallenge> requestOtp(String phoneNumber);
  Future<AuthTokens> verifyOtp({
    required String challengeId,
    required String code,
  });
  Future<AuthTokens> refresh(String refreshToken);
  Future<AuthUser> getMe();
  Future<AccountOnboarding> getOnboarding();
  Future<void> saveTokens(AuthTokens tokens);
  Future<void> clearTokens();
  Future<String?> readRefreshToken();
}
