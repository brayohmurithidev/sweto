import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';

enum GymOwnerStep {
  basicInformation,
  location,
  businessDetails,
  amenities,
  operatingHours,
  pricing,
  verification,
}

class GymOwnerProgress {
  const GymOwnerProgress({required this.current, required this.locked});

  static const ordered = <GymOwnerStep>[
    GymOwnerStep.basicInformation,
    GymOwnerStep.location,
    GymOwnerStep.businessDetails,
    GymOwnerStep.amenities,
    GymOwnerStep.operatingHours,
    GymOwnerStep.pricing,
    GymOwnerStep.verification,
  ];

  final GymOwnerStep current;
  final bool locked;

  int get currentIndex => ordered.indexOf(current);
  int get stepNumber => currentIndex + 1;
  int get totalSteps => ordered.length;

  bool isEnabled(GymOwnerStep step) =>
      !locked && ordered.indexOf(step) <= currentIndex;

  GymOwnerStep? get previous =>
      currentIndex > 0 ? ordered[currentIndex - 1] : null;

  static GymOwnerProgress fromBackend(GymOnboarding state) {
    final current = switch (state.nextStep) {
      GymOnboardingStep.basicInformation => GymOwnerStep.basicInformation,
      GymOnboardingStep.location => GymOwnerStep.location,
      GymOnboardingStep.businessDetails => GymOwnerStep.businessDetails,
      GymOnboardingStep.amenities => GymOwnerStep.amenities,
      GymOnboardingStep.operatingHours => GymOwnerStep.operatingHours,
      GymOnboardingStep.pricing => GymOwnerStep.pricing,
      _ => GymOwnerStep.verification,
    };
    return GymOwnerProgress(
      current: current,
      locked:
          state.verificationStatus == GymVerificationStatus.pending ||
          state.verificationStatus == GymVerificationStatus.approved ||
          state.completed,
    );
  }
}
