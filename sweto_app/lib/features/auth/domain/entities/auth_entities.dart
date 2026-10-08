/// How the sign-in code reaches the user. The API decides per country
/// (decision D-011): SMS in Kenya, WhatsApp in other supported countries.
enum OtpDeliveryChannel {
  sms,
  whatsapp;

  /// Parses the API's `delivery_channel`; older responses without it were SMS.
  static OtpDeliveryChannel fromApi(Object? value) =>
      value == 'whatsapp' ? whatsapp : sms;
}

/// Where a sign-in code is on its way, as reported by the provider.
///
/// Says nothing about whether the code can still be used.
enum OtpDeliveryStatus {
  pending,
  accepted,
  sent,
  delivered,
  read,
  failed;

  static OtpDeliveryStatus fromApi(Object? value) => switch (value) {
    'accepted' => accepted,
    'sent' => sent,
    'delivered' => delivered,
    'read' => read,
    'failed' => failed,
    _ => pending,
  };

  /// No further reports will change what the user should do.
  bool get isFinal => this == delivered || this == read || this == failed;
}

/// A country whose numbers can sign in now, with the channel its codes use.
class SignInCountry {
  const SignInCountry({required this.isoCode, required this.channel});

  final String isoCode;
  final OtpDeliveryChannel channel;
}

class OtpChallenge {
  const OtpChallenge({
    required this.challengeId,
    required this.phoneNumber,
    required this.expiresAt,
    required this.resendAvailableAt,
    this.deliveryChannel = OtpDeliveryChannel.sms,
  });

  final String challengeId;
  final String phoneNumber;
  final DateTime expiresAt;
  final DateTime resendAvailableAt;
  final OtpDeliveryChannel deliveryChannel;
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
