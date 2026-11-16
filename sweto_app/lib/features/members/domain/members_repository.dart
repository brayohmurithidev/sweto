import 'package:sweto_app/features/members/domain/member_entities.dart';

abstract interface class MembersRepository {
  Future<MemberPage> listMembers(
    String gymId, {
    MemberStanding? standing,
    String? search,
    bool archived = false,
    int limit = 30,
    int offset = 0,
  });
  Future<GymMember> addMember(
    String gymId, {
    required String fullName,
    required String phoneNumber,
    bool smsConsent = false,
  });
  Future<GymMember> setSms(
    String gymId,
    String memberId, {
    required bool enabled,
  });
  Future<MemberDetail> getMember(String gymId, String memberId);
  Future<GymMember> setArchived(
    String gymId,
    String memberId, {
    required bool archived,
  });
  Future<MemberDetail> recordCashPayment(
    String gymId,
    String memberId,
    CashPaymentInput input,
  );

  /// [phoneNumber] (E.164) prompts someone else's phone, e.g. a parent
  /// paying; null prompts the member's own number.
  Future<MpesaPayment> requestMpesaPayment(
    String gymId,
    String memberId, {
    required String planId,
    int? amount,
    String? phoneNumber,
  });
  Future<MpesaPayment> getPayment(String gymId, String paymentId);
  Future<CheckInCode> issueCheckInCode(String gymId, String memberId);
  Future<CheckInOutcome> checkIn(String gymId, String code);
  Future<CheckInDay> checkInsToday(String gymId);
  Future<DashboardSummary> getDashboard(String gymId);

  /// [month] is any day in the month; null for this month.
  Future<FinanceSummary> getFinance(String gymId, {DateTime? month});

  /// [mpesa] true for M-Pesa only, false for cash only, null for both.
  Future<FinanceTransactionPage> getFinanceTransactions(
    String gymId, {
    DateTime? month,
    bool? mpesa,
    int limit = 30,
    int offset = 0,
  });
  Future<MpesaTill> getMpesaTill(String gymId);
  Future<MpesaTill> saveMpesaTill(
    String gymId, {
    required bool isTill,
    required String shortcode,
    String? tillNumber,
    String? passkey,
    String? consumerKey,
    String? consumerSecret,
  });
}
