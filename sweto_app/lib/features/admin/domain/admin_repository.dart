import 'package:sweto_app/features/admin/domain/admin_entities.dart';

/// SWETO staff: sign-in and gym verification review.
abstract interface class AdminRepository {
  Future<AdminSignIn> signIn({required String email, required String password});

  /// Replaces the password, authorised by [accessToken] from [signIn] (it
  /// isn't stored: nothing is saved until the password is changed). The
  /// server then ends every session, so sign in again with the new one.
  Future<void> changePassword({
    required String accessToken,
    required String currentPassword,
    required String newPassword,
  });

  Future<VerificationQueuePage> listVerifications(
    VerificationStatus status, {
    int limit = 50,
    int offset = 0,
  });

  Future<VerificationDetail> getVerification(String gymId);

  /// A short-lived link to one uploaded document.
  Future<Uri> documentDownloadUrl(String gymId, String documentType);

  Future<VerificationDetail> approve(String gymId, {String? notes});

  Future<VerificationDetail> reject(String gymId, {required String reason});
}
