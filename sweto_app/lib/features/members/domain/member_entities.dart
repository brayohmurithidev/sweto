/// Where a member stands today, from their latest paid membership.
enum MemberStanding {
  active('active'),
  expiring('expiring'),
  expired('expired'),
  noMembership('no_membership');

  const MemberStanding(this.apiValue);
  final String apiValue;

  static MemberStanding fromApi(String? value) => MemberStanding.values
      .firstWhere((s) => s.apiValue == value, orElse: () => noMembership);
}

enum MemberStatus {
  active,
  archived;

  static MemberStatus fromApi(String? value) =>
      value == 'archived' ? archived : active;
}

class GymMember {
  const GymMember({
    required this.id,
    required this.fullName,
    required this.phoneNumber,
    required this.status,
    required this.standing,
    this.paidUntil,
  });

  final String id;
  final String fullName;
  final String phoneNumber;
  final MemberStatus status;
  final MemberStanding standing;

  /// Last day covered by a paid membership, in the gym's local calendar.
  final DateTime? paidUntil;

  bool get isArchived => status == MemberStatus.archived;
}

class MemberPage {
  const MemberPage({required this.members, required this.total});
  final List<GymMember> members;
  final int total;
}

class MemberPayment {
  const MemberPayment({
    required this.id,
    required this.amount,
    required this.currency,
    required this.method,
    this.paidAt,
  });
  final String id;
  final double amount;
  final String currency;
  final String method;
  final DateTime? paidAt;
}

class GymMembership {
  const GymMembership({
    required this.id,
    required this.planName,
    required this.amount,
    required this.currency,
    required this.startsOn,
    required this.endsOn,
    required this.status,
    this.payments = const [],
  });
  final String id;
  final String planName;
  final double amount;
  final String currency;
  final DateTime startsOn;
  final DateTime endsOn;

  /// active, expired, pending_payment or cancelled.
  final String status;
  final List<MemberPayment> payments;
}

class MemberDetail {
  const MemberDetail({required this.member, required this.memberships});
  final GymMember member;
  final List<GymMembership> memberships;
}

class CashPaymentInput {
  const CashPaymentInput({required this.planId, this.amount, this.startsOn});
  final String planId;

  /// Defaults to the plan price on the server.
  final int? amount;

  /// Only for a member who paid before being added (up to 90 days back).
  final DateTime? startsOn;
}
