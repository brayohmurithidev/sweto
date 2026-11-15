import 'package:dio/dio.dart';
import 'package:sweto_app/core/network/api_endpoints.dart';
import 'package:sweto_app/features/admin/domain/admin_entities.dart';
import 'package:sweto_app/features/admin/domain/admin_repository.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';

class DioAdminRepository implements AdminRepository {
  DioAdminRepository(this._dio);
  final Dio _dio;

  @override
  Future<AdminSignIn> signIn({
    required String email,
    required String password,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.passwordLogin,
      data: {'email': email, 'password': password},
      options: Options(extra: const {'requiresAuthentication': false}),
    );
    final d = _data(r.data);
    final tokens = _map(d['tokens']);
    return AdminSignIn(
      tokens: AuthTokens(
        accessToken: _string(tokens, 'access_token'),
        refreshToken: _string(tokens, 'refresh_token'),
      ),
      mustChangePassword: d['must_change_password'] == true,
    );
  }

  @override
  Future<void> changePassword({
    required String accessToken,
    required String currentPassword,
    required String newPassword,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.changePassword,
      data: {'current_password': currentPassword, 'new_password': newPassword},
      options: Options(
        headers: {'Authorization': 'Bearer $accessToken'},
        extra: const {'requiresAuthentication': false, 'skipRefresh': true},
      ),
    );
    _data(r.data);
  }

  @override
  Future<VerificationQueuePage> listVerifications(
    VerificationStatus status, {
    int limit = 50,
    int offset = 0,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.adminGymVerifications,
      queryParameters: {
        'status': status.apiValue,
        'limit': limit,
        'offset': offset,
      },
    );
    final d = _data(r.data);
    return VerificationQueuePage(
      total: (d['total'] as num?)?.toInt() ?? 0,
      gyms: (d['gyms'] as List? ?? const [])
          .map(_map)
          .map(
            (g) => VerificationSummary(
              gymId: _string(g, 'gym_id'),
              gymName: g['gym_name'] as String? ?? '',
              status: VerificationStatus.fromApi(
                g['verification_status'] as String?,
              ),
              submittedAt: _time(g['verification_submitted_at']),
              reviewedAt: _time(g['verification_reviewed_at']),
              missingDocuments: _strings(g['missing_required_document_types']),
            ),
          )
          .toList(),
    );
  }

  @override
  Future<VerificationDetail> getVerification(String gymId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.adminGymVerification(gymId),
    );
    return _detail(_data(r.data));
  }

  @override
  Future<Uri> documentDownloadUrl(String gymId, String documentType) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymVerificationDownload(gymId, documentType),
    );
    return Uri.parse(_string(_data(r.data), 'download_url'));
  }

  @override
  Future<VerificationDetail> approve(String gymId, {String? notes}) =>
      _review(gymId, {
        'decision': 'approve',
        if (notes != null && notes.trim().isNotEmpty) 'notes': notes.trim(),
      });

  @override
  Future<VerificationDetail> reject(String gymId, {required String reason}) =>
      _review(gymId, {'decision': 'reject', 'rejection_reason': reason.trim()});

  Future<VerificationDetail> _review(
    String gymId,
    Map<String, Object> body,
  ) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.adminGymReview(gymId),
      data: body,
    );
    return _detail(_data(r.data));
  }

  VerificationDetail _detail(Map<String, dynamic> d) {
    final gym = d['gym'] is Map<String, dynamic> ? _map(d['gym']) : null;
    return VerificationDetail(
      gymId: _string(d, 'gym_id'),
      status: VerificationStatus.fromApi(d['verification_status'] as String?),
      submittedAt: _time(d['verification_submitted_at']),
      reviewedAt: _time(d['verification_reviewed_at']),
      rejectionReason: d['verification_rejection_reason'] as String?,
      requiredDocuments: _strings(d['required_document_types']),
      missingDocuments: _strings(d['missing_required_document_types']),
      documents: (d['documents'] as List? ?? const [])
          .map(_map)
          .where((doc) => doc['is_active'] != false)
          .map(
            (doc) => VerificationDocument(
              type: _string(doc, 'document_type'),
              name: doc['document_name'] as String? ?? '',
              mimeType: doc['mime_type'] as String? ?? '',
              sizeBytes: (doc['file_size_bytes'] as num?)?.toInt() ?? 0,
              uploadedAt: _time(doc['created_at']) ?? DateTime.now(),
            ),
          )
          .toList(),
      history:
          (d['review_history'] as List? ?? const [])
              .map(_map)
              .map(
                (h) => VerificationReviewEntry(
                  approved: h['decision'] == 'approve',
                  reviewedAt: _time(h['reviewed_at']) ?? DateTime.now(),
                  reason: h['rejection_reason'] as String?,
                  notes: h['notes'] as String?,
                ),
              )
              .toList()
            ..sort((a, b) => b.reviewedAt.compareTo(a.reviewedAt)),
      gym: gym == null
          ? null
          : ReviewedGym(
              name: gym['name'] as String? ?? '',
              phoneNumber: gym['phone_number'] as String?,
              email: gym['email'] as String?,
              description: gym['description'] as String?,
              legalBusinessName: gym['legal_business_name'] as String?,
              businessType: gym['business_type'] as String?,
              registrationNumber: gym['registration_number'] as String?,
              taxNumber: gym['tax_number'] as String?,
              contactPersonName: gym['contact_person_name'] as String?,
              contactPersonPhone: gym['contact_person_phone'] as String?,
              addressLine: gym['address_line'] as String?,
              neighbourhood: gym['neighbourhood'] as String?,
              city: gym['city'] as String?,
            ),
    );
  }

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

  List<String> _strings(Object? v) =>
      (v as List? ?? const []).whereType<String>().toList();

  DateTime? _time(Object? v) =>
      v is String ? DateTime.tryParse(v)?.toLocal() : null;
}
