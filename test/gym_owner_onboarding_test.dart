import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/repositories/auth_repository.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_repository.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';

void main() {
  test('account onboarding enums safely parse known and unknown values', () {
    expect(accountRoleFromApi('gym_owner'), AccountRole.gymOwner);
    expect(accountRoleFromApi('future_role'), AccountRole.unknown);
    expect(
      accountOnboardingStatusFromApi('gym_setup_pending'),
      AccountOnboardingStatus.gymSetupPending,
    );
    expect(
      accountOnboardingStatusFromApi('future_status'),
      AccountOnboardingStatus.unknown,
    );
    expect(
      gymOnboardingStepFromApi('basic_information'),
      GymOnboardingStep.basicInformation,
    );
  });

  test('gym creation request serializes only supported fields', () {
    const input = CreateGymInput(
      name: 'FlexFit',
      phoneNumber: '+254712345678',
      description: 'A gym',
    );
    expect(input.toJson(), {
      'name': 'FlexFit',
      'phone_number': '+254712345678',
      'description': 'A gym',
    });
  });

  test(
    'coordinator routes account selection and unknown states safely',
    () async {
      final auth = _AuthFake();
      final gyms = _GymFake();
      final coordinator = OnboardingCoordinator(auth, gyms);
      expect(
        await coordinator.resolveAccount(_account('choose_account')),
        OnboardingDestination.accountType,
      );
      expect(
        await coordinator.resolveAccount(_account('future_step')),
        OnboardingDestination.unsupported,
      );
    },
  );

  test('gym setup with no current gym routes to registration', () async {
    final coordinator = OnboardingCoordinator(
      _AuthFake(),
      _GymFake(noGym: true),
    );
    expect(
      await coordinator.resolveAccount(_account('gym_setup')),
      OnboardingDestination.gymRegistration,
    );
  });

  test('basic information gym state routes to registration', () async {
    final coordinator = OnboardingCoordinator(
      _AuthFake(),
      _GymFake(step: GymOnboardingStep.basicInformation),
    );
    expect(
      await coordinator.resolveAccount(_account('gym_setup')),
      OnboardingDestination.gymRegistration,
    );
  });

  test('amenities gym state routes to the amenities screen', () async {
    final coordinator = OnboardingCoordinator(
      _AuthFake(),
      _GymFake(step: GymOnboardingStep.amenities),
    );
    expect(
      await coordinator.resolveAccount(_account('gym_setup')),
      OnboardingDestination.amenities,
    );
  });

  test(
    'gym setup with a current gym fetches its persisted onboarding',
    () async {
      final gyms = _GymFake();
      final coordinator = OnboardingCoordinator(_AuthFake(), gyms);
      expect(
        await coordinator.resolveAccount(_account('gym_setup')),
        OnboardingDestination.location,
      );
      expect(gyms.requestedOnboardingFor, 'gym-id');
    },
  );

  test('selecting gym owner calls the role endpoint once', () async {
    final auth = _AuthFake();
    final coordinator = OnboardingCoordinator(auth, _GymFake(noGym: true));
    expect(
      await coordinator.selectGymOwner(),
      OnboardingDestination.gymRegistration,
    );
    expect(auth.roleSelections, 1);
  });
}

AccountOnboarding _account(String nextStep) => AccountOnboarding(
  roles: const [AccountRole.gymOwner],
  defaultRole: AccountRole.gymOwner,
  status: AccountOnboardingStatus.gymSetupPending,
  completed: false,
  nextStep: nextStep,
);

class _AuthFake implements AuthRepository {
  int roleSelections = 0;
  @override
  Future<void> clearTokens() async {}
  @override
  Future<AuthUser> getMe() => throw UnimplementedError();
  @override
  Future<AccountOnboarding> getOnboarding() async => _account('choose_account');
  @override
  Future<String?> readRefreshToken() async => null;
  @override
  Future<AuthTokens> refresh(String refreshToken) => throw UnimplementedError();
  @override
  Future<OtpChallenge> requestOtp(String phoneNumber) =>
      throw UnimplementedError();
  @override
  Future<void> saveTokens(AuthTokens tokens) async {}
  @override
  Future<AccountOnboarding> selectGymOwnerRole() async {
    roleSelections++;
    return _account('gym_setup');
  }

  @override
  Future<AuthTokens> verifyOtp({
    required String challengeId,
    required String code,
  }) => throw UnimplementedError();
}

class _GymFake implements GymOwnerRepository {
  _GymFake({this.noGym = false, this.step = GymOnboardingStep.location});
  final bool noGym;
  final GymOnboardingStep step;
  @override
  Future<List<GymAmenity>> getAmenities() => throw UnimplementedError();
  @override
  Future<List<GymAmenity>> getGymAmenities(String gymId) =>
      throw UnimplementedError();
  @override
  Future<void> updateGymAmenities(String gymId, Set<String> amenityIds) =>
      throw UnimplementedError();

  @override
  Future<List<OperatingDay>> getOperatingHours(String gymId) =>
      throw UnimplementedError();

  @override
  Future<void> updateOperatingHours(String gymId, List<OperatingDay> days) =>
      throw UnimplementedError();
  @override
  Future<GymPricing> getGymPricing(String gymId) => throw UnimplementedError();
  @override
  Future<void> updateGymPricing(String gymId, GymPricing pricing) =>
      throw UnimplementedError();
  @override
  Future<GymVerificationData> getGymVerification(String gymId) =>
      throw UnimplementedError();
  @override
  Future<VerificationUploadIntent> initiateVerificationUpload(
    String gymId,
    String documentType, {
    required String filename,
    required String mimeType,
    required int fileSizeBytes,
  }) => throw UnimplementedError();
  @override
  Future<void> uploadVerificationFile(
    VerificationUploadIntent intent,
    List<int> bytes, {
    required String mimeType,
    void Function(int sent, int total)? onProgress,
  }) => throw UnimplementedError();
  @override
  Future<VerificationDocument> completeVerificationUpload(
    String gymId,
    String documentType,
    String uploadId,
  ) => throw UnimplementedError();
  @override
  Future<void> submitGymVerification(String gymId) =>
      throw UnimplementedError();
  @override
  Future<Gym> updateGymBusinessDetails(
    String gymId,
    GymBusinessDetails details,
  ) => throw UnimplementedError();
  @override
  Future<Gym> updateGymLocation(String gymId, GymLocation location) =>
      throw UnimplementedError();
  @override
  Future<GymPhotoUploadIntent> initiateGymPhotoUpload(
    String gymId, {
    required String filename,
    required String mimeType,
    required int fileSize,
  }) => throw UnimplementedError();

  @override
  Future<void> uploadGymPhotoToPresignedUrl(
    GymPhotoUploadIntent intent,
    List<int> bytes, {
    required String mimeType,
    void Function(int sent, int total)? onProgress,
  }) => throw UnimplementedError();

  @override
  Future<void> completeGymPhotoUpload(String gymId, String uploadId) =>
      throw UnimplementedError();

  @override
  Future<List<GymPhoto>> getGymPhotos(String gymId) =>
      throw UnimplementedError();

  @override
  Future<void> deleteGymPhoto(String gymId, String photoId) =>
      throw UnimplementedError();
  @override
  Future<Gym> updateBasicInformation(String gymId, CreateGymInput input) =>
      throw UnimplementedError();
  String? requestedOnboardingFor;
  @override
  Future<Gym> createGym(CreateGymInput input) => throw UnimplementedError();
  @override
  Future<Gym> getCurrentGym() async {
    if (noGym) {
      throw DioException(
        requestOptions: RequestOptions(path: '/api/v1/gyms/current'),
        response: Response(
          statusCode: 404,
          requestOptions: RequestOptions(path: '/api/v1/gyms/current'),
        ),
      );
    }
    return const Gym(id: 'gym-id', name: 'Gym');
  }

  @override
  Future<GymOnboarding> getGymOnboarding(String gymId) async {
    requestedOnboardingFor = gymId;
    return GymOnboarding(
      gymId: 'gym-id',
      nextStep: step,
      completed: false,
      verificationStatus: GymVerificationStatus.notSubmitted,
    );
  }
}
