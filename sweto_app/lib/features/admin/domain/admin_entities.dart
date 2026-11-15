import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';

/// Where a gym stands with SWETO's review.
enum VerificationStatus {
  notSubmitted('not_submitted'),
  pending('pending'),
  approved('approved'),
  rejected('rejected');

  const VerificationStatus(this.apiValue);
  final String apiValue;

  static VerificationStatus fromApi(String? value) => VerificationStatus.values
      .firstWhere((s) => s.apiValue == value, orElse: () => notSubmitted);
}

/// The result of an email and password sign-in by SWETO staff.
class AdminSignIn {
  const AdminSignIn({required this.tokens, required this.mustChangePassword});

  final AuthTokens tokens;

  /// The first sign-in with a generated password must replace it before any
  /// admin action.
  final bool mustChangePassword;
}

/// One gym in the review queue.
class VerificationSummary {
  const VerificationSummary({
    required this.gymId,
    required this.gymName,
    required this.status,
    required this.missingDocuments,
    this.submittedAt,
    this.reviewedAt,
  });

  final String gymId;
  final String gymName;
  final VerificationStatus status;
  final DateTime? submittedAt;
  final DateTime? reviewedAt;

  /// Required document types not uploaded yet.
  final List<String> missingDocuments;
}

class VerificationQueuePage {
  const VerificationQueuePage({required this.gyms, required this.total});

  final List<VerificationSummary> gyms;
  final int total;
}

class VerificationDocument {
  const VerificationDocument({
    required this.type,
    required this.name,
    required this.mimeType,
    required this.sizeBytes,
    required this.uploadedAt,
  });

  /// API value, e.g. business_registration.
  final String type;
  final String name;
  final String mimeType;
  final int sizeBytes;
  final DateTime uploadedAt;
}

class VerificationReviewEntry {
  const VerificationReviewEntry({
    required this.approved,
    required this.reviewedAt,
    this.reason,
    this.notes,
  });

  final bool approved;
  final DateTime reviewedAt;
  final String? reason;
  final String? notes;
}

/// What the gym told us about itself during onboarding.
class ReviewedGym {
  const ReviewedGym({
    required this.name,
    this.phoneNumber,
    this.email,
    this.description,
    this.legalBusinessName,
    this.businessType,
    this.registrationNumber,
    this.taxNumber,
    this.contactPersonName,
    this.contactPersonPhone,
    this.addressLine,
    this.neighbourhood,
    this.city,
  });

  final String name;
  final String? phoneNumber;
  final String? email;
  final String? description;
  final String? legalBusinessName;
  final String? businessType;
  final String? registrationNumber;
  final String? taxNumber;
  final String? contactPersonName;
  final String? contactPersonPhone;
  final String? addressLine;
  final String? neighbourhood;
  final String? city;
}

class VerificationDetail {
  const VerificationDetail({
    required this.gymId,
    required this.status,
    required this.requiredDocuments,
    required this.missingDocuments,
    required this.documents,
    required this.history,
    this.gym,
    this.submittedAt,
    this.reviewedAt,
    this.rejectionReason,
  });

  final String gymId;
  final VerificationStatus status;
  final ReviewedGym? gym;
  final DateTime? submittedAt;
  final DateTime? reviewedAt;
  final String? rejectionReason;
  final List<String> requiredDocuments;
  final List<String> missingDocuments;
  final List<VerificationDocument> documents;

  /// Newest first.
  final List<VerificationReviewEntry> history;
}

/// "Business Registration Certificate" for business_registration.
String verificationDocumentLabel(String type) => switch (type) {
  'business_registration' => 'Business Registration Certificate',
  'owner_identification' => 'Owner Identification',
  'tax_certificate' => 'KRA PIN Certificate',
  'operating_license' => 'County Business Permit',
  'proof_of_address' => 'Proof of Address',
  'other' => 'Other document',
  _ => type.replaceAll('_', ' '),
};
