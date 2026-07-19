class ApiEndpoints {
  ApiEndpoints._();

  static const health = '/api/v1/health';

  static const passwordLogin = '/api/v1/auth/password/login';
  static const requestOtp = '/api/v1/auth/request-otp';
  static const verifyOtp = '/api/v1/auth/verify-otp';

  static const refreshToken = '/api/v1/auth/refresh';

  static const currentUser = '/api/v1/auth/me';
  static const accountOnboarding = '/api/v1/account/onboarding';

  static const changePassword = '/api/v1/auth/change-password';
}
