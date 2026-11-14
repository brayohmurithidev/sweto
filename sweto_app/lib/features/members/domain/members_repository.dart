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
  Future<CheckInCode> issueCheckInCode(String gymId, String memberId);
  Future<CheckInOutcome> checkIn(String gymId, String code);
  Future<CheckInDay> checkInsToday(String gymId);
}
