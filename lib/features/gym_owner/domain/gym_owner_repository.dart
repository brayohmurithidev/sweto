import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';

abstract interface class GymOwnerRepository {
  Future<Gym> createGym(CreateGymInput input);
  Future<Gym> updateBasicInformation(String gymId, CreateGymInput input);
  Future<Gym> getCurrentGym();
  Future<GymOnboarding> getGymOnboarding(String gymId);
  Future<Gym> updateGymLocation(String gymId, GymLocation location);
  Future<Gym> updateGymBusinessDetails(
    String gymId,
    GymBusinessDetails details,
  );
  Future<GymPhotoUploadIntent> initiateGymPhotoUpload(
    String gymId, {
    required String filename,
    required String mimeType,
    required int fileSize,
  });
  Future<void> uploadGymPhotoToPresignedUrl(
    GymPhotoUploadIntent intent,
    List<int> bytes, {
    required String mimeType,
    void Function(int sent, int total)? onProgress,
  });
  Future<void> completeGymPhotoUpload(String gymId, String uploadId);
  Future<List<GymPhoto>> getGymPhotos(String gymId);
  Future<void> deleteGymPhoto(String gymId, String photoId);
  Future<List<GymAmenity>> getAmenities();
  Future<List<GymAmenity>> getGymAmenities(String gymId);
  Future<void> updateGymAmenities(String gymId, Set<String> amenityIds);
  Future<List<OperatingDay>> getOperatingHours(String gymId);
  Future<void> updateOperatingHours(String gymId, List<OperatingDay> days);
  Future<GymPricing> getGymPricing(String gymId);
  Future<void> updateGymPricing(String gymId, GymPricing pricing);
  Future<GymVerificationData> getGymVerification(String gymId);
  Future<VerificationUploadIntent> initiateVerificationUpload(
    String gymId,
    String documentType, {
    required String filename,
    required String mimeType,
    required int fileSizeBytes,
  });
  Future<void> uploadVerificationFile(
    VerificationUploadIntent intent,
    List<int> bytes, {
    required String mimeType,
    void Function(int sent, int total)? onProgress,
  });
  Future<VerificationDocument> completeVerificationUpload(
    String gymId,
    String documentType,
    String uploadId,
  );
  Future<void> submitGymVerification(String gymId);
}
