import 'package:sweto_app/features/staff/domain/staff_entities.dart';

abstract class StaffRepository {
  Future<GymAccess> getMyAccess(String gymId);
  Future<List<StaffMember>> listStaff(String gymId);
  Future<AddedStaff> addStaff(
    String gymId, {
    required String fullName,
    required String phoneNumber,
    required StaffRole role,
  });
  Future<StaffMember> updateStaff(
    String gymId,
    String staffId, {
    StaffRole? role,
    bool? suspended,
  });
  Future<void> removeStaff(String gymId, String staffId);
}
