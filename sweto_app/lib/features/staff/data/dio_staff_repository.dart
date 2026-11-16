import 'package:dio/dio.dart';
import 'package:sweto_app/core/network/api_endpoints.dart';
import 'package:sweto_app/features/staff/domain/staff_entities.dart';
import 'package:sweto_app/features/staff/domain/staff_repository.dart';

class DioStaffRepository implements StaffRepository {
  DioStaffRepository(this._dio);
  final Dio _dio;

  @override
  Future<GymAccess> getMyAccess(String gymId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymStaffMe(gymId),
    );
    final d = _data(r.data);
    final names = (d['permissions'] as List? ?? const []).toSet();
    return GymAccess(
      role: StaffRole.fromApi(d['role']),
      isPrimaryOwner: d['is_primary_owner'] == true,
      permissions: {
        for (final p in GymPermission.values)
          if (names.contains(p.apiValue)) p,
      },
    );
  }

  @override
  Future<List<StaffMember>> listStaff(String gymId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymStaff(gymId),
    );
    return (_data(r.data)['staff'] as List? ?? const [])
        .map((item) => _staff(_map(item)))
        .toList();
  }

  @override
  Future<AddedStaff> addStaff(
    String gymId, {
    required String fullName,
    required String phoneNumber,
    required StaffRole role,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymStaff(gymId),
      data: {
        'full_name': fullName,
        'phone_number': phoneNumber,
        'role': role.apiValue,
      },
    );
    final d = _data(r.data);
    return AddedStaff(
      staff: _staff(_map(d['staff'])),
      inviteSent: d['invite_sms'] == 'sent',
    );
  }

  @override
  Future<StaffMember> updateStaff(
    String gymId,
    String staffId, {
    StaffRole? role,
    bool? suspended,
  }) async {
    final r = await _dio.patch<Map<String, dynamic>>(
      ApiEndpoints.gymStaffMember(gymId, staffId),
      data: {
        if (role != null) 'role': role.apiValue,
        if (suspended != null) 'status': suspended ? 'suspended' : 'active',
      },
    );
    return _staff(_data(r.data));
  }

  @override
  Future<void> removeStaff(String gymId, String staffId) async {
    await _dio.delete<void>(ApiEndpoints.gymStaffMember(gymId, staffId));
  }

  StaffMember _staff(Map<String, dynamic> d) => StaffMember(
    id: '${d['id']}',
    userId: d['user_id'] as String?,
    today: d['today'] is Map<String, dynamic> ? _day(_map(d['today'])) : null,
    fullName: d['full_name'] as String?,
    phoneNumber: d['phone_number'] as String?,
    role: StaffRole.fromApi(d['role']),
    status: d['status'] as String? ?? 'active',
    isPrimaryOwner: d['is_primary_owner'] == true,
    hasSignedIn: d['has_signed_in'] == true,
  );

  StaffDay _day(Map<String, dynamic> d) => StaffDay(
    payments: (d['payments'] as num?)?.toInt() ?? 0,
    cash: double.tryParse('${d['cash']}') ?? 0,
    mpesa: double.tryParse('${d['mpesa']}') ?? 0,
    checkIns: (d['check_ins'] as num?)?.toInt() ?? 0,
  );

  Map<String, dynamic> _data(Map<String, dynamic>? body) => _map(body?['data']);

  Map<String, dynamic> _map(Object? value) =>
      value is Map<String, dynamic> ? value : <String, dynamic>{};
}
