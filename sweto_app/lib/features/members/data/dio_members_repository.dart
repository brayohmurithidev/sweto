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
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymMembers(gymId),
      data: {'full_name': fullName, 'phone_number': phoneNumber},
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
    await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymMemberCashPayment(gymId, memberId),
      data: {
        'plan_id': input.planId,
        'amount': ?input.amount,
        if (input.startsOn != null) 'starts_on': _isoDate(input.startsOn!),
      },
    );
    return getMember(gymId, memberId);
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
