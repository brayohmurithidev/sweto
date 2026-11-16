class AppRoutes {
  AppRoutes._();

  static const splashName = 'splash';
  static const splashPath = '/';

  static const onboardingName = 'onboarding';
  static const onboardingPath = '/onboarding';

  static const phoneLoginName = 'phone-login';
  static const phoneLoginPath = '/auth/phone';

  static const otpName = 'otp-verification';
  static const otpPath = '/auth/otp';

  static const homeName = 'home';
  static const homePath = '/home';
  static const profileCompletionName = 'profile-completion';
  static const profileCompletionPath = '/profile-completion';
  static const accountTypeName = 'account-type';
  static const accountTypePath = '/onboarding/account-type';
  static const gymRegistrationName = 'gym-registration';
  static const gymRegistrationPath = '/onboarding/gym/register';
  static const gymLocationName = 'gym-location';
  static const gymLocationPath = '/onboarding/gym/location';
  static const gymBusinessDetailsName = 'gym-business-details';
  static const gymBusinessDetailsPath = '/onboarding/gym/business-details';
  static const gymAmenitiesName = 'gym-amenities';
  static const gymAmenitiesPath = '/onboarding/gym/amenities';
  static const gymOperatingHoursName = 'gym-operating-hours';
  static const gymOperatingHoursPath = '/onboarding/gym/operating-hours';
  static const gymPricingName = 'gym-pricing';
  static const gymPricingPath = '/onboarding/gym/pricing';
  static const memberComingSoonName = 'member-coming-soon';
  static const memberComingSoonPath = '/onboarding/member-coming-soon';
  static const verificationPendingName = 'verification-pending';
  static const verificationPendingPath = '/onboarding/verification-pending';
  static const gymVerificationName = 'gym-verification';
  static const gymVerificationPath = '/onboarding/gym/verification';
  static const unsupportedOnboardingName = 'unsupported-onboarding';
  static const unsupportedOnboardingPath = '/onboarding/unsupported';

  static const membersName = 'members';
  static const membersPath = '/gyms/:gymId/members';
  static const addMemberName = 'add-member';
  static const addMemberPath = '/gyms/:gymId/members/new';
  static const memberDetailName = 'member-detail';
  static const memberDetailPath = '/gyms/:gymId/members/:memberId';

  static const checkInName = 'check-in';
  static const checkInPath = '/gyms/:gymId/check-in';

  static const mpesaTillName = 'mpesa-till';
  static const mpesaTillPath = '/gyms/:gymId/mpesa-till';

  static const activityName = 'activity';
  static const activityPath = '/gyms/:gymId/activity';

  static const staffName = 'staff';
  static const staffPath = '/gyms/:gymId/staff';
  static const staffSuspendedName = 'staff-suspended';
  static const staffSuspendedPath = '/onboarding/staff-suspended';

  // A verified gym's details, edited from More.
  static const gymProfileSettingsName = 'gym-settings-profile';
  static const gymProfileSettingsPath = '/gyms/:gymId/settings/profile';
  static const gymLocationSettingsName = 'gym-settings-location';
  static const gymLocationSettingsPath = '/gyms/:gymId/settings/location';
  static const gymPlansSettingsName = 'gym-settings-plans';
  static const gymPlansSettingsPath = '/gyms/:gymId/settings/plans';
  static const gymHoursSettingsName = 'gym-settings-hours';
  static const gymHoursSettingsPath = '/gyms/:gymId/settings/hours';
  static const gymAmenitiesSettingsName = 'gym-settings-amenities';
  static const gymAmenitiesSettingsPath = '/gyms/:gymId/settings/amenities';

  static const healthName = 'health';
  static const healthPath = '/health';

  // SWETO staff.
  static const adminSignInName = 'admin-sign-in';
  static const adminSignInPath = '/auth/staff';
  static const adminHomeName = 'admin-home';
  static const adminHomePath = '/admin';
  static const adminGymReviewName = 'admin-gym-review';
  static const adminGymReviewPath = '/admin/gyms/:gymId';
}
