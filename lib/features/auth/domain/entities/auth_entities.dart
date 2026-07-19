class OtpChallenge {
  const OtpChallenge({
    required this.challengeId,
    required this.phoneNumber,
    required this.expiresAt,
    required this.resendAvailableAt,
  });

  final String challengeId;
  final String phoneNumber;
  final DateTime expiresAt;
  final DateTime resendAvailableAt;
}

class AuthTokens {
  const AuthTokens({required this.accessToken, required this.refreshToken});

  final String accessToken;
  final String refreshToken;
}

class AuthUser {
  const AuthUser({required this.id, required this.mustChangePassword});

  final String id;
  final bool mustChangePassword;
}

class AccountOnboarding {
  const AccountOnboarding({required this.completed, required this.nextStep});

  final bool completed;
  final String nextStep;
}
