import 'package:dio/dio.dart';
import 'package:sweto_app/core/network/api_endpoints.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/domain/members_repository.dart';

class DioMembersRepository implements MembersRepository {
  DioMembersRepository(this._dio);
  final Dio _dio;

  @override
  Future<MemberPage> listMembers(
    String gymId, {
    MemberStanding? standing,
    String? search,
    bool archived = false,
    int limit = 30,
    int offset = 0,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymMembers(gymId),
      queryParameters: {
        'standing': ?standing?.apiValue,
        if (search != null && search.trim().isNotEmpty) 'search': search.trim(),
        if (archived) 'status': 'archived',
        'limit': limit,
        'offset': offset,
      },
    );
    final data = _data(r.data);
    final members = (data['members'] as List? ?? const [])
        .map((m) => _member(_map(m)))
        .toList();
    return MemberPage(
      members: members,
      total: (data['total'] as num?)?.toInt() ?? members.length,
    );
  }

  @override
  Future<GymMember> addMember(
    String gymId, {
    required String fullName,
    required String phoneNumber,
    bool smsConsent = false,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymMembers(gymId),
      data: {
        'full_name': fullName,
        'phone_number': phoneNumber,
        'sms_consent': smsConsent,
      },
    );
    return _member(_data(r.data));
  }

  @override
  Future<GymMember> setSms(
    String gymId,
    String memberId, {
    required bool enabled,
  }) async {
    final r = await _dio.put<Map<String, dynamic>>(
      '${ApiEndpoints.gymMember(gymId, memberId)}/sms',
      data: {'enabled': enabled},
    );
    return _member(_data(r.data));
  }

  @override
  Future<MemberDetail> getMember(String gymId, String memberId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymMember(gymId, memberId),
    );
    return _detail(_data(r.data));
  }

  @override
  Future<GymMember> setArchived(
    String gymId,
    String memberId, {
    required bool archived,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '${ApiEndpoints.gymMember(gymId, memberId)}/'
      '${archived ? 'archive' : 'restore'}',
    );
    return _member(_data(r.data));
  }

  @override
  Future<MemberDetail> recordCashPayment(
    String gymId,
    String memberId,
    CashPaymentInput input,
  ) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymMemberCashPayment(gymId, memberId),
      data: {
        'plan_id': input.planId,
        'amount': ?input.amount,
        if (input.startsOn != null) 'starts_on': _isoDate(input.startsOn!),
      },
    );
    final sms = _data(r.data)['sms'] as String?;
    final detail = await getMember(gymId, memberId);
    return MemberDetail(
      member: detail.member,
      memberships: detail.memberships,
      smsStatus: sms,
    );
  }

  @override
  Future<MpesaPayment> requestMpesaPayment(
    String gymId,
    String memberId, {
    required String planId,
    int? amount,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymMemberMpesaPayment(gymId, memberId),
      data: {'plan_id': planId, 'amount': ?amount},
    );
    return _mpesa(_data(r.data));
  }

  @override
  Future<MpesaPayment> getPayment(String gymId, String paymentId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymPayment(gymId, paymentId),
    );
    return _mpesa(_data(r.data));
  }

  MpesaPayment _mpesa(Map<String, dynamic> d) => MpesaPayment(
    paymentId: _string(d, 'payment_id'),
    state: PaymentState.fromApi(d['status'] as String?),
    message: d['message'] as String? ?? '',
    receipt: d['receipt'] as String?,
    paidUntil: _date(d['paid_until']),
  );

  @override
  Future<CheckInCode> issueCheckInCode(String gymId, String memberId) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymMemberCheckInCode(gymId, memberId),
    );
    final d = _data(r.data);
    return CheckInCode(
      code: _string(d, 'code'),
      qrPayload: _string(d, 'qr_payload'),
      smsStatus: d['sms'] as String?,
    );
  }

  @override
  Future<CheckInOutcome> checkIn(String gymId, String code) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymCheckIns(gymId),
      data: {'code': code},
    );
    final d = _data(r.data);
    final member = d['member'] is Map ? _map(d['member']) : null;
    final membership = d['membership'] is Map ? _map(d['membership']) : null;
    return CheckInOutcome(
      result: CheckInResult.fromApi(d['result'] as String?),
      alreadyCheckedInToday: d['already_checked_in_today'] == true,
      message: d['message'] as String? ?? '',
      memberName: member?['full_name'] as String?,
      paidUntil: _date(member?['paid_until']),
      planName: membership?['plan_name'] as String?,
      visitsUsed: (membership?['visits_used'] as num?)?.toInt(),
      visitLimit: (membership?['visit_limit'] as num?)?.toInt(),
    );
  }

  @override
  Future<CheckInDay> checkInsToday(String gymId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymCheckIns(gymId),
    );
    final d = _data(r.data);
    return CheckInDay(
      visits: (d['visits'] as num?)?.toInt() ?? 0,
      refused: (d['refused'] as num?)?.toInt() ?? 0,
      entries: (d['check_ins'] as List? ?? const [])
          .map((e) => _map(e))
          .map(
            (e) => CheckInEntry(
              id: _string(e, 'id'),
              result: CheckInResult.fromApi(e['result'] as String?),
              alreadyCheckedInToday: e['already_checked_in_today'] == true,
              checkedInAt:
                  DateTime.tryParse('${e['checked_in_at']}')?.toLocal() ??
                  DateTime.now(),
              memberName: e['member_name'] as String?,
            ),
          )
          .toList(),
    );
  }

  @override
  Future<DashboardSummary> getDashboard(String gymId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymDashboard(gymId),
    );
    final d = _data(r.data);
    final revenue = _map(d['revenue']);
    return DashboardSummary(
      gymName: _string(d, 'gym_name'),
      ownerFirstName: d['owner_first_name'] as String?,
      activeMembers: (d['active_members'] as num?)?.toInt() ?? 0,
      expiringMembers: (d['expiring_members'] as num?)?.toInt() ?? 0,
      checkInsToday: (d['check_ins_today'] as num?)?.toInt() ?? 0,
      revenueThisMonth: _number(revenue['this_month']),
      currency: revenue['currency'] as String? ?? 'KES',
      revenueChangePercent: (revenue['change_percent'] as num?)?.toDouble(),
      dailyRevenue: (revenue['daily'] as List? ?? const [])
          .map((day) => _number(_map(day)['amount']))
          .toList(),
      recentActivity: (d['recent_activity'] as List? ?? const [])
          .map((item) => _map(item))
          .map(
            (item) => ActivityItem(
              kind: item['kind'] as String? ?? '',
              at:
                  DateTime.tryParse('${item['at']}')?.toLocal() ??
                  DateTime.now(),
              detail: item['detail'] as String? ?? '',
              ok: item['ok'] != false,
              memberId: item['member_id'] as String?,
              memberName: item['member_name'] as String?,
            ),
          )
          .toList(),
    );
  }

  MemberDetail _detail(Map<String, dynamic> d) => MemberDetail(
    member: _member(_map(d['member'])),
    memberships: (d['memberships'] as List? ?? const [])
        .map((m) => _membership(_map(m)))
        .toList(),
  );

  GymMember _member(Map<String, dynamic> d) => GymMember(
    id: _string(d, 'id'),
    fullName: _string(d, 'full_name'),
    phoneNumber: _string(d, 'phone_number'),
    status: MemberStatus.fromApi(d['status'] as String?),
    standing: MemberStanding.fromApi(d['standing'] as String?),
    paidUntil: _date(d['paid_until']),
    hasCheckInCode: d['has_check_in_code'] == true,
    smsEnabled: d['sms_enabled'] == true,
    smsOptedOutAt: DateTime.tryParse('${d['sms_opted_out_at']}')?.toLocal(),
  );

  GymMembership _membership(Map<String, dynamic> d) => GymMembership(
    id: _string(d, 'id'),
    planName: _string(d, 'plan_name'),
    amount: _number(d['amount']),
    currency: d['currency'] as String? ?? 'KES',
    startsOn: _date(d['starts_on']) ?? DateTime(1970),
    endsOn: _date(d['ends_on']) ?? DateTime(1970),
    status: d['status'] as String? ?? 'active',
    payments: (d['payments'] as List? ?? const [])
        .map((p) => _map(p))
        .map(
          (p) => MemberPayment(
            id: _string(p, 'id'),
            amount: _number(p['amount']),
            currency: p['currency'] as String? ?? 'KES',
            method: p['method'] as String? ?? 'cash',
            paidAt: DateTime.tryParse('${p['paid_at']}')?.toLocal(),
          ),
        )
        .toList(),
  );

  Map<String, dynamic> _data(Map<String, dynamic>? json) {
    if (json == null || json['success'] != true) {
      throw const FormatException('The server response is invalid.');
    }
    return _map(json['data']);
  }

  Map<String, dynamic> _map(Object? v) {
    if (v is Map<String, dynamic>) return v;
    throw const FormatException('The server response is invalid.');
  }

  String _string(Map<String, dynamic> d, String k) {
    final v = d[k];
    if (v is String && v.isNotEmpty) return v;
    throw FormatException('Missing $k in server response.');
  }

  double _number(Object? v) =>
      v is num ? v.toDouble() : double.tryParse('$v') ?? 0;

  /// API dates are calendar dates ("2026-12-13"), kept as local midnight.
  DateTime? _date(Object? v) {
    if (v is! String) return null;
    final parsed = DateTime.tryParse(v);
    return parsed == null
        ? null
        : DateTime(parsed.year, parsed.month, parsed.day);
  }

  String _isoDate(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';
}
