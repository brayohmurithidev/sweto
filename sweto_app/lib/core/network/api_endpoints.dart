class ApiEndpoints {
  ApiEndpoints._();

  static const health = '/api/v1/health';

  static const passwordLogin = '/api/v1/auth/password/login';
  static const requestOtp = '/api/v1/auth/request-otp';
  static const verifyOtp = '/api/v1/auth/verify-otp';

  static const refreshToken = '/api/v1/auth/refresh';
  static const logout = '/api/v1/auth/logout';

  static const currentUser = '/api/v1/auth/me';
  static const accountOnboarding = '/api/v1/account/onboarding';
  static const accountRoles = '/api/v1/account/roles';
  static const gyms = '/api/v1/gyms';
  static const currentGym = '/api/v1/gyms/current';

  static String gymBasicInformation(String gymId) =>
      '$gyms/$gymId/basic-information';
  static String gymLocation(String gymId) => '$gyms/$gymId/location';
  static String gymBusinessDetails(String gymId) =>
      '$gyms/$gymId/business-details';
  static const amenities = '$gyms/amenities';
  static String gymAmenities(String gymId) => '$gyms/$gymId/amenities';
  static String gymOperatingHours(String gymId) =>
      '$gyms/$gymId/operating-hours';
  static String gymPricing(String gymId) => '$gyms/$gymId/pricing';
  static String gymVerification(String gymId) => '$gyms/$gymId/verification';
  static String gymVerificationSubmit(String gymId) =>
      '${gymVerification(gymId)}/submit';
  static String gymVerificationUpload(String gymId, String documentType) =>
      '${gymVerification(gymId)}/documents/$documentType/upload';
  static String gymVerificationComplete(
    String gymId,
    String documentType,
    String uploadId,
  ) => '${gymVerificationUpload(gymId, documentType)}/$uploadId/complete';
  static String gymPhotos(String gymId) => '$gyms/$gymId/photos';
  static String gymPhotoUpload(String gymId) => '${gymPhotos(gymId)}/upload';
  static String gymPhotoComplete(String gymId, String uploadId) =>
      '${gymPhotoUpload(gymId)}/$uploadId/complete';
  static String gymPhoto(String gymId, String photoId) =>
      '${gymPhotos(gymId)}/$photoId';

  static const changePassword = '/api/v1/auth/change-password';
}
