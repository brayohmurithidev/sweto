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
    this.hasCheckInCode = false,
    this.smsEnabled = false,
    this.smsOptedOutAt,
  });

  final String id;
  final String fullName;
  final String phoneNumber;
  final MemberStatus status;
  final MemberStanding standing;

  /// Last day covered by a paid membership, in the gym's local calendar.
  final DateTime? paidUntil;

  /// Whether a check-in code has been issued (the code itself is never kept).
  final bool hasCheckInCode;

  /// Staff recorded the member's consent and they haven't opted out.
  final bool smsEnabled;
  final DateTime? smsOptedOutAt;

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
  const MemberDetail({
    required this.member,
    required this.memberships,
    this.smsStatus,
  });
  final GymMember member;
  final List<GymMembership> memberships;

  /// After recording a payment: "sent", "failed", or null when no SMS was
  /// due (no consent, opted out).
  final String? smsStatus;
}

class CashPaymentInput {
  const CashPaymentInput({required this.planId, this.amount, this.startsOn});
  final String planId;

  /// Defaults to the plan price on the server.
  final int? amount;

  /// Only for a member who paid before being added (up to 90 days back).
  final DateTime? startsOn;
}

/// A freshly issued check-in code. Shown once; only a hash is stored.
class CheckInCode {
  const CheckInCode({
    required this.code,
    required this.qrPayload,
    this.smsStatus,
  });

  /// Display form, e.g. "7KQ2-M9XD".
  final String code;
  final String qrPayload;

  /// "sent", "failed", or null when the member gets no SMS.
  final String? smsStatus;
}

enum CheckInResult {
  allowed('allowed'),
  expired('expired'),
  notStarted('not_started'),
  noMembership('no_membership'),
  archived('archived'),
  visitLimitReached('visit_limit_reached'),
  unknownCode('unknown_code');

  const CheckInResult(this.apiValue);
  final String apiValue;

  static CheckInResult fromApi(String? value) => CheckInResult.values
      .firstWhere((r) => r.apiValue == value, orElse: () => unknownCode);
}

class CheckInOutcome {
  const CheckInOutcome({
    required this.result,
    required this.alreadyCheckedInToday,
    required this.message,
    this.memberName,
    this.paidUntil,
    this.planName,
    this.visitsUsed,
    this.visitLimit,
  });

  final CheckInResult result;
  final bool alreadyCheckedInToday;
  final String message;
  final String? memberName;
  final DateTime? paidUntil;
  final String? planName;
  final int? visitsUsed;
  final int? visitLimit;

  bool get allowed => result == CheckInResult.allowed;
}

class CheckInEntry {
  const CheckInEntry({
    required this.id,
    required this.result,
    required this.alreadyCheckedInToday,
    required this.checkedInAt,
    this.memberName,
  });

  final String id;
  final CheckInResult result;
  final bool alreadyCheckedInToday;
  final DateTime checkedInAt;
  final String? memberName;
}

class CheckInDay {
  const CheckInDay({
    required this.visits,
    required this.refused,
    required this.entries,
  });

  final int visits;
  final int refused;
  final List<CheckInEntry> entries;
}

/// Canonical form of a typed or scanned code, or null if it can't be one.
///
/// Mirrors the API: 8 characters without look-alikes (no 0/O, 1/I/L), any
/// case, spaces and dashes ignored, optionally the QR payload.
String? normalizeCheckInCode(String raw) {
  const alphabet = '23456789ABCDEFGHJKMNPQRSTUVWXYZ';
  const prefix = 'sweto:checkin:';
  var value = raw.trim();
  if (value.toLowerCase().startsWith(prefix)) {
    value = value.substring(prefix.length);
  }
  value = value.replaceAll(RegExp(r'[\s-]'), '').toUpperCase();
  if (value.length != 8 || value.split('').any((c) => !alphabet.contains(c))) {
    return null;
  }
  return value;
}

enum PaymentState {
  pending,
  completed,
  failed;

  static PaymentState fromApi(String? value) => switch (value) {
    'completed' => completed,
    'failed' => failed,
    _ => pending,
  };
}

/// An M-Pesa payment request and where it stands.
class MpesaPayment {
  const MpesaPayment({
    required this.paymentId,
    required this.state,
    required this.message,
    this.receipt,
    this.paidUntil,
  });

  final String paymentId;
  final PaymentState state;

  /// Plain words from the server, e.g. "The member cancelled the M-Pesa prompt."
  final String message;
  final String? receipt;
  final DateTime? paidUntil;
}

class ActivityItem {
  const ActivityItem({
    required this.kind,
    required this.at,
    required this.detail,
    required this.ok,
    this.memberId,
    this.memberName,
  });

  /// check_in, payment or member_added
  final String kind;
  final DateTime at;
  final String detail;
  final bool ok;
  final String? memberId;
  final String? memberName;
}

class DashboardSummary {
  const DashboardSummary({
    required this.gymName,
    required this.activeMembers,
    required this.expiringMembers,
    required this.checkInsToday,
    required this.revenueThisMonth,
    required this.currency,
    required this.dailyRevenue,
    required this.recentActivity,
    this.ownerFirstName,
    this.revenueChangePercent,
  });

  final String gymName;
  final String? ownerFirstName;
  final int activeMembers;
  final int expiringMembers;
  final int checkInsToday;
  final double revenueThisMonth;
  final String currency;

  /// Null when last month had no revenue to compare with.
  final double? revenueChangePercent;

  /// Each day of this month so far.
  final List<double> dailyRevenue;
  final List<ActivityItem> recentActivity;
}

/// The gym's own M-Pesa Pay Bill or Till. The passkey never comes back.
class MpesaTill {
  const MpesaTill({
    required this.configured,
    required this.mode,
    this.isTill = false,
    this.shortcode,
    this.tillNumber,
    this.passkeySaved = false,
  });

  final bool configured;

  /// disabled, simulated, sandbox or production.
  final String mode;
  final bool isTill;
  final String? shortcode;
  final String? tillNumber;
  final bool passkeySaved;

  bool get isLive => mode == 'production';
}

/// Revenue for one plan in a month.
class PlanRevenue {
  const PlanRevenue({
    required this.planName,
    required this.amount,
    required this.count,
  });

  final String planName;
  final double amount;
  final int count;
}

/// One month's revenue, for the trend chart.
class MonthRevenue {
  const MonthRevenue({required this.month, required this.amount});

  /// First day of the month.
  final DateTime month;
  final double amount;
}

/// A month's money for the Finance tab, by the gym's calendar.
class FinanceSummary {
  const FinanceSummary({
    required this.currency,
    required this.month,
    required this.through,
    required this.isCurrentMonth,
    required this.total,
    required this.paymentsCount,
    required this.previousMonthTotal,
    required this.cashAmount,
    required this.cashCount,
    required this.mpesaAmount,
    required this.mpesaCount,
    required this.byPlan,
    required this.trend,
    this.changePercent,
    this.failedMpesaCount = 0,
    this.pendingMpesaCount = 0,
  });

  final String currency;

  /// First day of the month shown.
  final DateTime month;

  /// Last day counted: today in the current month.
  final DateTime through;
  final bool isCurrentMonth;
  final double total;
  final int paymentsCount;

  /// The month before, over the same days when this month is in progress.
  final double previousMonthTotal;

  /// Null when the month before had nothing to compare with.
  final double? changePercent;
  final double cashAmount;
  final int cashCount;
  final double mpesaAmount;
  final int mpesaCount;

  /// Largest first.
  final List<PlanRevenue> byPlan;

  /// Six months ending with [month], oldest first.
  final List<MonthRevenue> trend;
  final int failedMpesaCount;
  final int pendingMpesaCount;
}

/// One payment on the Finance tab, paid or not.
class FinanceTransaction {
  const FinanceTransaction({
    required this.paymentId,
    required this.memberId,
    required this.memberName,
    required this.planName,
    required this.amount,
    required this.currency,
    required this.isMpesa,
    required this.state,
    required this.at,
    this.receipt,
    this.recordedByName,
  });

  final String paymentId;
  final String memberId;
  final String memberName;
  final String planName;
  final double amount;
  final String currency;
  final bool isMpesa;
  final PaymentState state;
  final DateTime at;

  /// M-Pesa receipt number, once paid.
  final String? receipt;
  final String? recordedByName;
}

class FinanceTransactionPage {
  const FinanceTransactionPage({
    required this.transactions,
    required this.total,
  });

  final List<FinanceTransaction> transactions;
  final int total;
}
