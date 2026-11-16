import 'package:sweto_app/features/staff/domain/staff_entities.dart';
import 'package:sweto_app/features/staff/domain/staff_repository.dart';

/// Staff API double: a fixed role for the signed-in person and an in-memory
/// staff list the owner can change.
class FakeStaffRepository implements StaffRepository {
  FakeStaffRepository({GymAccess? access, List<StaffMember>? staff})
    : access = access ?? GymAccess.owner,
      staff = staff ?? [];

  GymAccess access;
  List<StaffMember> staff;
  final added = <(String, String, StaffRole)>[];
  final updates = <(String, StaffRole?, bool?)>[];
  final removed = <String>[];
  bool inviteSent = true;
  Object? failure;

  static GymAccess accessFor(StaffRole role) {
    const front = {
      GymPermission.viewGym,
      GymPermission.viewMembers,
      GymPermission.editMembers,
      GymPermission.takePayments,
      GymPermission.issueCheckInCodes,
      GymPermission.checkIn,
    };
    return GymAccess(
      role: role,
      permissions: switch (role) {
        StaffRole.owner => GymPermission.values.toSet(),
        StaffRole.manager => {
          ...front,
          GymPermission.editGym,
          GymPermission.viewFinance,
          GymPermission.archiveMembers,
        },
        StaffRole.receptionist => front,
        StaffRole.trainer => {
          GymPermission.viewGym,
          GymPermission.viewMembers,
          GymPermission.checkIn,
        },
      },
    );
  }

  @override
  Future<GymAccess> getMyAccess(String gymId) async => access;

  @override
  Future<List<StaffMember>> listStaff(String gymId) async => List.of(staff);

  @override
  Future<AddedStaff> addStaff(
    String gymId, {
    required String fullName,
    required String phoneNumber,
    required StaffRole role,
  }) async {
    if (failure != null) throw failure!;
    added.add((fullName, phoneNumber, role));
    final member = StaffMember(
      id: 'staff-${staff.length + 1}',
      fullName: fullName,
      phoneNumber: phoneNumber,
      role: role,
      status: 'active',
      isPrimaryOwner: false,
      hasSignedIn: false,
    );
    staff.add(member);
    return AddedStaff(staff: member, inviteSent: inviteSent);
  }

  @override
  Future<StaffMember> updateStaff(
    String gymId,
    String staffId, {
    StaffRole? role,
    bool? suspended,
  }) async {
    updates.add((staffId, role, suspended));
    final i = staff.indexWhere((s) => s.id == staffId);
    final old = staff[i];
    staff[i] = StaffMember(
      id: old.id,
      fullName: old.fullName,
      phoneNumber: old.phoneNumber,
      role: role ?? old.role,
      status: suspended == null
          ? old.status
          : (suspended ? 'suspended' : 'active'),
      isPrimaryOwner: old.isPrimaryOwner,
      hasSignedIn: old.hasSignedIn,
    );
    return staff[i];
  }

  @override
  Future<void> removeStaff(String gymId, String staffId) async {
    removed.add(staffId);
    staff.removeWhere((s) => s.id == staffId);
  }
}
