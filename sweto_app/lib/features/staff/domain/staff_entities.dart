/// A role someone holds at a gym.
enum StaffRole {
  owner('owner', 'Owner'),
  manager('manager', 'Manager'),
  receptionist('receptionist', 'Receptionist'),
  trainer('trainer', 'Trainer');

  const StaffRole(this.apiValue, this.label);
  final String apiValue;
  final String label;

  static StaffRole fromApi(Object? value) => StaffRole.values.firstWhere(
    (role) => role.apiValue == value,
    orElse: () => StaffRole.trainer,
  );

  /// Roles an owner can give the people they add.
  static const assignable = [manager, receptionist, trainer];

  String get summary => switch (this) {
    owner => 'Everything, including staff and the M-Pesa till',
    manager => 'Members, payments, finance and gym settings',
    receptionist => 'Members, payments and check-ins',
    trainer => 'Look members up and check them in',
  };
}

/// Something a role may do. Mirrors the API's permission names.
enum GymPermission {
  viewGym('view_gym'),
  editGym('edit_gym'),
  manageVerification('manage_verification'),
  managePaymentSettings('manage_payment_settings'),
  manageStaff('manage_staff'),
  viewFinance('view_finance'),
  viewActivity('view_activity'),
  viewMembers('view_members'),
  editMembers('edit_members'),
  archiveMembers('archive_members'),
  takePayments('take_payments'),
  issueCheckInCodes('issue_check_in_codes'),
  checkIn('check_in');

  const GymPermission(this.apiValue);
  final String apiValue;
}

/// What the signed-in person may do at their gym.
class GymAccess {
  const GymAccess({
    required this.role,
    required this.permissions,
    this.isPrimaryOwner = false,
  });

  /// Before the role is known: the app shows everything and the API decides.
  static final owner = GymAccess(
    role: StaffRole.owner,
    permissions: GymPermission.values.toSet(),
    isPrimaryOwner: true,
  );

  final StaffRole role;
  final Set<GymPermission> permissions;
  final bool isPrimaryOwner;

  bool can(GymPermission permission) => permissions.contains(permission);
}

/// Someone who works at the gym.
class StaffMember {
  const StaffMember({
    required this.id,
    required this.role,
    required this.status,
    required this.isPrimaryOwner,
    required this.hasSignedIn,
    this.userId,
    this.fullName,
    this.phoneNumber,
    this.today,
  });

  final String id;
  final String? userId;
  final String? fullName;
  final String? phoneNumber;
  final StaffRole role;

  /// 'active' or 'suspended'.
  final String status;
  final bool isPrimaryOwner;

  /// False until they first sign in: shown as invited.
  final bool hasSignedIn;

  /// What they did today (staff list only).
  final StaffDay? today;

  bool get isSuspended => status == 'suspended';
  String get displayName =>
      (fullName?.trim().isNotEmpty ?? false) ? fullName! : (phoneNumber ?? '');
}

class AddedStaff {
  const AddedStaff({required this.staff, required this.inviteSent});
  final StaffMember staff;
  final bool inviteSent;
}

/// One staff member's day, for the owner's end-of-day check.
class StaffDay {
  const StaffDay({
    required this.payments,
    required this.cash,
    required this.mpesa,
    required this.checkIns,
  });

  final int payments;
  final double cash;
  final double mpesa;
  final int checkIns;

  bool get isEmpty => payments == 0 && checkIns == 0;
}
