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
  const AuthUser({
    required this.id,
    required this.mustChangePassword,
    this.phoneNumber,
    this.email,
  });

  final String id;
  final bool mustChangePassword;
  final String? phoneNumber;
  final String? email;
}

class AccountOnboarding {
  const AccountOnboarding({
    required this.roles,
    required this.defaultRole,
    required this.status,
    required this.completed,
    required this.nextStep,
  });

  final List<AccountRole> roles;
  final AccountRole? defaultRole;
  final AccountOnboardingStatus status;
  final bool completed;
  final String nextStep;
}

enum AccountRole { member, gymOwner, unknown }

enum AccountOnboardingStatus {
  accountSelectionPending,
  profileSetupPending,
  gymSetupPending,
  verificationPending,
  completed,
  unknown,
}

AccountRole accountRoleFromApi(Object? value) => switch (value) {
  'member' => AccountRole.member,
  'gym_owner' => AccountRole.gymOwner,
  _ => AccountRole.unknown,
};
AccountOnboardingStatus accountOnboardingStatusFromApi(Object? value) =>
    switch (value) {
      'account_selection_pending' =>
        AccountOnboardingStatus.accountSelectionPending,
      'profile_setup_pending' => AccountOnboardingStatus.profileSetupPending,
      'gym_setup_pending' => AccountOnboardingStatus.gymSetupPending,
      'verification_pending' => AccountOnboardingStatus.verificationPending,
      'completed' => AccountOnboardingStatus.completed,
      _ => AccountOnboardingStatus.unknown,
    };
