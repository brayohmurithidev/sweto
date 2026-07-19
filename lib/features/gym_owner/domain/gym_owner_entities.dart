class Gym {
  const Gym({
    required this.id,
    required this.name,
    this.phoneNumber,
    this.email,
    this.description,
    this.location,
    this.legalBusinessName,
    this.businessType,
    this.registrationNumber,
    this.taxNumber,
    this.contactPersonName,
    this.contactPersonPhone,
  });
  final String id;
  final String name;
  final String? phoneNumber;
  final String? email;
  final String? description;
  final GymLocation? location;
  final String? legalBusinessName;
  final String? businessType;
  final String? registrationNumber;
  final String? taxNumber;
  final String? contactPersonName;
  final String? contactPersonPhone;
}

class GymBusinessDetails {
  const GymBusinessDetails({
    required this.legalBusinessName,
    required this.businessType,
    this.registrationNumber,
    this.taxNumber,
    required this.contactPersonName,
    required this.contactPersonPhone,
  });
  final String legalBusinessName;
  final String businessType;
  final String? registrationNumber;
  final String? taxNumber;
  final String contactPersonName;
  final String contactPersonPhone;
}

class GymAmenity {
  const GymAmenity({
    required this.id,
    required this.name,
    required this.slug,
    this.icon,
    this.description,
    required this.displayOrder,
  });
  final String id;
  final String name;
  final String slug;
  final String? icon;
  final String? description;
  final int displayOrder;
}

class OperatingDay {
  const OperatingDay({
    required this.dayOfWeek,
    required this.isClosed,
    required this.is24Hours,
    this.opensAt,
    this.closesAt,
  });
  final int dayOfWeek;
  final bool isClosed;
  final bool is24Hours;
  final String? opensAt;
  final String? closesAt;
}

class GymPricingPlan {
  const GymPricingPlan({
    required this.name,
    required this.amount,
    required this.billingPeriod,
    required this.isActive,
  });
  final String name;
  final int amount;
  final String billingPeriod;
  final bool isActive;
}

class GymPricing {
  const GymPricing({
    this.dayPasses = const [],
    this.membershipPlans = const [],
  });
  final List<GymPricingPlan> dayPasses;
  final List<GymPricingPlan> membershipPlans;
}

class VerificationDocument {
  const VerificationDocument({
    required this.id,
    required this.type,
    required this.name,
    required this.mimeType,
    required this.size,
    required this.active,
  });
  final String id;
  final String type;
  final String name;
  final String mimeType;
  final int size;
  final bool active;
}

class VerificationUploadIntent {
  const VerificationUploadIntent({
    required this.uploadId,
    required this.uploadUrl,
    required this.requiredHeaders,
    required this.expiresAt,
    required this.storageKey,
  });
  final String uploadId;
  final String uploadUrl;
  final Map<String, String> requiredHeaders;
  final DateTime expiresAt;
  final String storageKey;
}

class GymVerificationData {
  const GymVerificationData({
    required this.status,
    required this.requiredTypes,
    required this.missingTypes,
    required this.documents,
    this.rejectionReason,
  });
  final String status;
  final List<String> requiredTypes;
  final List<String> missingTypes;
  final List<VerificationDocument> documents;
  final String? rejectionReason;
}

class GymLocation {
  const GymLocation({
    required this.latitude,
    required this.longitude,
    required this.addressLine,
    required this.neighbourhood,
    required this.city,
    required this.countryCode,
  });
  final double latitude;
  final double longitude;
  final String addressLine;
  final String neighbourhood;
  final String city;
  final String countryCode;
}

class GymOnboarding {
  const GymOnboarding({
    required this.gymId,
    required this.nextStep,
    required this.completed,
    required this.verificationStatus,
  });
  final String gymId;
  final GymOnboardingStep nextStep;
  final bool completed;
  final GymVerificationStatus verificationStatus;
}

enum GymOnboardingStep {
  basicInformation,
  location,
  businessDetails,
  amenities,
  operatingHours,
  pricing,
  verification,
  waitingForVerification,
  completed,
  unknown,
}

enum GymVerificationStatus {
  notSubmitted,
  pending,
  approved,
  rejected,
  unknown,
}

GymOnboardingStep gymOnboardingStepFromApi(Object? value) {
  if (value is! String || value.trim().isEmpty) {
    return GymOnboardingStep.unknown;
  }
  final normalized = value
      .trim()
      .replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (m) => '${m[1]}_${m[2]}')
      .toLowerCase();
  return switch (normalized) {
    'basic_information' || 'basic_info' => GymOnboardingStep.basicInformation,
    'location' || 'gym_location' => GymOnboardingStep.location,
    'business_details' => GymOnboardingStep.businessDetails,
    'amenities' || 'gym_amenities' => GymOnboardingStep.amenities,
    'operating_hours' => GymOnboardingStep.operatingHours,
    'pricing' || 'membership_pricing' => GymOnboardingStep.pricing,
    'verification' ||
    'verification_documents' => GymOnboardingStep.verification,
    'waiting_for_verification' ||
    'pending_review' ||
    'pending' => GymOnboardingStep.waitingForVerification,
    'completed' ||
    'approved' ||
    'limited_dashboard' => GymOnboardingStep.completed,
    _ => GymOnboardingStep.unknown,
  };
}

GymVerificationStatus gymVerificationStatusFromApi(Object? value) =>
    switch (value) {
      'not_submitted' => GymVerificationStatus.notSubmitted,
      'pending' => GymVerificationStatus.pending,
      'approved' => GymVerificationStatus.approved,
      'rejected' => GymVerificationStatus.rejected,
      _ => GymVerificationStatus.unknown,
    };

class CreateGymInput {
  const CreateGymInput({
    required this.name,
    this.phoneNumber,
    this.email,
    this.description,
  });
  final String name;
  final String? phoneNumber;
  final String? email;
  final String? description;
  Map<String, Object> toJson() {
    final value = <String, Object>{'name': name};
    if (phoneNumber != null) value['phone_number'] = phoneNumber!;
    if (email != null) value['email'] = email!;
    if (description != null) value['description'] = description!;
    return value;
  }
}

class GymPhoto {
  const GymPhoto({
    required this.id,
    required this.url,
    required this.originalFilename,
    required this.mimeType,
    required this.fileSize,
    required this.displayOrder,
    required this.isCover,
    required this.createdAt,
  });
  final String id;
  final String url;
  final String originalFilename;
  final String mimeType;
  final int fileSize;
  final int displayOrder;
  final bool isCover;
  final DateTime createdAt;
}

class GymPhotoUploadIntent {
  const GymPhotoUploadIntent({
    required this.uploadId,
    required this.uploadUrl,
    required this.expiresAt,
    this.storageKey,
    this.requiredHeaders = const <String, String>{},
  });
  final String uploadId;
  final String uploadUrl;
  final String? storageKey;
  final DateTime expiresAt;
  final Map<String, String> requiredHeaders;
}
