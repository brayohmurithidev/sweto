import 'package:dio/dio.dart';
import 'package:sweto_app/core/network/api_endpoints.dart';
import 'package:sweto_app/core/network/api_response.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_repository.dart';

class DioGymOwnerRepository implements GymOwnerRepository {
  DioGymOwnerRepository(this._dio);
  final Dio _dio;
  @override
  Future<Gym> createGym(CreateGymInput input) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gyms,
      data: input.toJson(),
    );
    return _envelope(r.data, (d) => _gym(_map(d['gym'])));
  }

  @override
  Future<Gym> updateBasicInformation(String gymId, CreateGymInput input) async {
    final r = await _dio.patch<Map<String, dynamic>>(
      ApiEndpoints.gymBasicInformation(gymId),
      data: input.toJson(),
    );
    return _envelope(r.data, (d) => _gym(_map(d['gym'])));
  }

  @override
  Future<Gym> updateGymLocation(String gymId, GymLocation location) async {
    final r = await _dio.patch<Map<String, dynamic>>(
      ApiEndpoints.gymLocation(gymId),
      data: {
        'address_line': location.addressLine,
        'neighbourhood': location.neighbourhood,
        'city': location.city,
        'country_code': location.countryCode,
        'latitude': location.latitude,
        'longitude': location.longitude,
      },
    );
    return _envelope(r.data, (d) => _gym(_map(d['gym'])));
  }

  @override
  Future<Gym> updateGymBusinessDetails(
    String gymId,
    GymBusinessDetails details,
  ) async {
    final r = await _dio.patch<Map<String, dynamic>>(
      ApiEndpoints.gymBusinessDetails(gymId),
      data: {
        'legal_business_name': details.legalBusinessName,
        'business_type': details.businessType,
        'registration_number': details.registrationNumber,
        if (details.taxNumber != null) 'tax_number': details.taxNumber,
        'contact_person_name': details.contactPersonName,
        'contact_person_phone': details.contactPersonPhone,
      },
    );
    return _envelope(r.data, (d) => _gym(_map(d['gym'])));
  }

  @override
  Future<Gym> getCurrentGym() async {
    final r = await _dio.get<Map<String, dynamic>>(ApiEndpoints.currentGym);
    return _envelope(r.data, _gym);
  }

  @override
  Future<GymOnboarding> getGymOnboarding(String id) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '${ApiEndpoints.gyms}/$id/onboarding',
    );
    return _envelope(
      r.data,
      (d) => GymOnboarding(
        gymId: _string(d, 'gym_id'),
        nextStep: gymOnboardingStepFromApi(d['next_step']),
        completed: d['onboarding_completed'] == true,
        verificationStatus: gymVerificationStatusFromApi(
          d['verification_status'],
        ),
      ),
    );
  }

  @override
  Future<GymPhotoUploadIntent> initiateGymPhotoUpload(
    String gymId, {
    required String filename,
    required String mimeType,
    required int fileSize,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymPhotoUpload(gymId),
      data: {
        'filename': filename,
        'mime_type': mimeType,
        'file_size': fileSize,
      },
    );
    return _envelope(
      r.data,
      (d) => GymPhotoUploadIntent(
        uploadId: _string(d, 'upload_id'),
        uploadUrl: _string(d, 'upload_url'),
        storageKey: d['storage_key'] as String?,
        expiresAt: DateTime.parse(_string(d, 'expires_at')),
        requiredHeaders: _headers(d['required_headers']),
      ),
    );
  }

  @override
  Future<void> uploadGymPhotoToPresignedUrl(
    GymPhotoUploadIntent intent,
    List<int> bytes, {
    required String mimeType,
    void Function(int sent, int total)? onProgress,
  }) async {
    final s3 = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 20),
        sendTimeout: const Duration(seconds: 60),
        receiveTimeout: const Duration(seconds: 30),
      ),
    );
    final headers = <String, dynamic>{
      'Content-Type': mimeType,
      ...intent.requiredHeaders,
    };
    final response = await s3.put<void>(
      intent.uploadUrl,
      data: bytes,
      options: Options(headers: headers, contentType: mimeType),
      onSendProgress: onProgress,
    );
    if (response.statusCode == null ||
        response.statusCode! < 200 ||
        response.statusCode! >= 300) {
      throw DioException(
        requestOptions: response.requestOptions,
        response: response,
      );
    }
  }

  @override
  Future<void> completeGymPhotoUpload(String gymId, String uploadId) async {
    await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymPhotoComplete(gymId, uploadId),
    );
  }

  @override
  Future<List<GymPhoto>> getGymPhotos(String gymId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymPhotos(gymId),
    );
    return _envelope(r.data, (d) {
      final values = d['photos'];
      if (values is! List)
        throw const FormatException('Invalid photo response.');
      return values.map((value) {
        final photo = _map(value);
        return GymPhoto(
          id: _string(photo, 'id'),
          url: _string(photo, 'url'),
          originalFilename: _string(photo, 'original_filename'),
          mimeType: _string(photo, 'mime_type'),
          fileSize: (photo['file_size'] as num).toInt(),
          displayOrder: (photo['display_order'] as num).toInt(),
          isCover: photo['is_cover'] == true,
          createdAt: DateTime.parse(_string(photo, 'created_at')),
        );
      }).toList();
    });
  }

  @override
  Future<void> deleteGymPhoto(String gymId, String photoId) async {
    await _dio.delete<Map<String, dynamic>>(
      ApiEndpoints.gymPhoto(gymId, photoId),
    );
  }

  @override
  Future<List<GymAmenity>> getAmenities() async {
    final r = await _dio.get<Map<String, dynamic>>(ApiEndpoints.amenities);
    final envelope = r.data;
    final raw = envelope?['data'];
    if (raw is! List) {
      throw const FormatException('Invalid amenities response.');
    }
    return raw.map((value) {
      final item = _map(value);
      return GymAmenity(
        id: _string(item, 'id'),
        name: _string(item, 'name'),
        slug: _string(item, 'slug'),
        icon: item['icon'] as String?,
        description: item['description'] as String?,
        displayOrder: (item['display_order'] as num).toInt(),
      );
    }).toList();
  }

  @override
  Future<List<GymAmenity>> getGymAmenities(String gymId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymAmenities(gymId),
    );
    final raw = r.data?['data'];
    if (raw is! List)
      throw const FormatException('Invalid gym amenities response.');
    return raw.map((value) {
      final item = _map(value);
      return GymAmenity(
        id: _string(item, 'id'),
        name: _string(item, 'name'),
        slug: _string(item, 'slug'),
        icon: item['icon'] as String?,
        description: item['description'] as String?,
        displayOrder: (item['display_order'] as num).toInt(),
      );
    }).toList();
  }

  @override
  Future<void> updateGymAmenities(String gymId, Set<String> amenityIds) async {
    await _dio.put<Map<String, dynamic>>(
      ApiEndpoints.gymAmenities(gymId),
      data: {'amenity_ids': amenityIds.toList()},
    );
  }

  @override
  Future<List<OperatingDay>> getOperatingHours(String gymId) async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymOperatingHours(gymId),
    );
    final raw = response.data?['data'];
    if (raw is! List)
      throw const FormatException('Invalid operating hours response.');
    return raw.map((value) {
      final item = _map(value);
      return OperatingDay(
        dayOfWeek: (item['day_of_week'] as num).toInt(),
        isClosed: item['is_closed'] as bool? ?? false,
        is24Hours: item['is_24_hours'] as bool? ?? false,
        opensAt: item['opens_at'] as String?,
        closesAt: item['closes_at'] as String?,
      );
    }).toList();
  }

  @override
  Future<void> updateOperatingHours(
    String gymId,
    List<OperatingDay> days,
  ) async {
    await _dio.put<Map<String, dynamic>>(
      ApiEndpoints.gymOperatingHours(gymId),
      data: {
        'operating_hours': days
            .map(
              (day) => {
                'day_of_week': day.dayOfWeek,
                'is_closed': day.isClosed,
                'is_24_hours': day.is24Hours,
                'opens_at': day.opensAt,
                'closes_at': day.closesAt,
              },
            )
            .toList(),
      },
    );
  }

  @override
  Future<GymPricing> getGymPricing(String gymId) async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymPricing(gymId),
    );
    final data = response.data?['data'];
    if (data is! Map) throw const FormatException('Invalid pricing response.');
    List<GymPricingPlan> parse(Object? value, {required bool dayPass}) =>
        (value is List ? value : const []).map((raw) {
          final item = _map(raw);
          return GymPricingPlan(
            name: _string(item, 'name'),
            amount: (double.tryParse('${item['amount']}') ?? 0).round(),
            billingPeriod: dayPass
                ? 'day_pass'
                : item['billing_period'] as String? ?? 'monthly',
            isActive: item['is_active'] as bool? ?? true,
          );
        }).toList();
    return GymPricing(
      dayPasses: parse(data['day_passes'], dayPass: true),
      membershipPlans: parse(data['membership_plans'], dayPass: false),
    );
  }

  @override
  Future<void> updateGymPricing(String gymId, GymPricing pricing) async {
    await _dio.put<Map<String, dynamic>>(
      ApiEndpoints.gymPricing(gymId),
      data: {
        'day_passes': pricing.dayPasses
            .map(
              (plan) => {
                'name': plan.name,
                'amount': plan.amount,
                'currency': 'KES',
                'validity_hours': 24,
                'is_active': plan.isActive,
                'display_order': 0,
              },
            )
            .toList(),
        'membership_plans': pricing.membershipPlans
            .map(
              (plan) => {
                'name': plan.name,
                'amount': plan.amount,
                'currency': 'KES',
                'billing_period': plan.billingPeriod,
                'is_active': plan.isActive,
                'is_featured': false,
                'display_order': 0,
                'benefits': [],
              },
            )
            .toList(),
      },
    );
  }

  @override
  Future<GymVerificationData> getGymVerification(String gymId) async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.gymVerification(gymId),
    );
    final data = response.data?['data'];
    if (data is! Map)
      throw const FormatException('Invalid verification response.');
    final documents =
        (data['documents'] is List ? data['documents'] as List : const []).map((
          raw,
        ) {
          final item = _map(raw);
          return VerificationDocument(
            id: _string(item, 'id'),
            type: _string(item, 'document_type'),
            name: _string(item, 'document_name'),
            mimeType: _string(item, 'mime_type'),
            size: (item['file_size_bytes'] as num?)?.toInt() ?? 0,
            active: item['is_active'] == true,
          );
        }).toList();
    return GymVerificationData(
      status: data['verification_status'] as String? ?? 'not_submitted',
      requiredTypes: (data['required_document_types'] as List? ?? const [])
          .map((e) => '$e')
          .toList(),
      missingTypes:
          (data['missing_required_document_types'] as List? ?? const [])
              .map((e) => '$e')
              .toList(),
      documents: documents,
      rejectionReason: data['verification_rejection_reason'] as String?,
    );
  }

  @override
  Future<VerificationUploadIntent> initiateVerificationUpload(
    String gymId,
    String documentType, {
    required String filename,
    required String mimeType,
    required int fileSizeBytes,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymVerificationUpload(gymId, documentType),
      data: {
        'filename': filename,
        'mime_type': mimeType,
        'file_size_bytes': fileSizeBytes,
      },
    );
    return _envelope(
      response.data,
      (data) => VerificationUploadIntent(
        uploadId: _string(data, 'upload_id'),
        uploadUrl: _string(data, 'upload_url'),
        requiredHeaders: _headers(data['required_headers']),
        expiresAt: DateTime.parse(_string(data, 'expires_at')),
        storageKey: _string(data, 'storage_key'),
      ),
    );
  }

  @override
  Future<void> uploadVerificationFile(
    VerificationUploadIntent intent,
    List<int> bytes, {
    required String mimeType,
    void Function(int sent, int total)? onProgress,
  }) async {
    final storageDio = Dio();
    final response = await storageDio.put<void>(
      intent.uploadUrl,
      data: bytes,
      options: Options(
        headers: {'Content-Type': mimeType, ...intent.requiredHeaders},
        contentType: mimeType,
      ),
      onSendProgress: onProgress,
    );
    if ((response.statusCode ?? 0) < 200 || (response.statusCode ?? 0) >= 300) {
      throw DioException(
        requestOptions: response.requestOptions,
        response: response,
      );
    }
  }

  @override
  Future<VerificationDocument> completeVerificationUpload(
    String gymId,
    String documentType,
    String uploadId,
  ) async {
    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymVerificationComplete(gymId, documentType, uploadId),
    );
    return _envelope(
      response.data,
      (item) => VerificationDocument(
        id: _string(item, 'id'),
        type: _string(item, 'document_type'),
        name: _string(item, 'document_name'),
        mimeType: _string(item, 'mime_type'),
        size: (item['file_size_bytes'] as num?)?.toInt() ?? 0,
        active: item['is_active'] == true,
      ),
    );
  }

  @override
  Future<void> submitGymVerification(String gymId) async {
    await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.gymVerificationSubmit(gymId),
    );
  }

  T _envelope<T>(
    Map<String, dynamic>? json,
    T Function(Map<String, dynamic>) parse,
  ) {
    if (json == null) {
      throw const FormatException('The server returned an empty response.');
    }
    return ApiResponse<T>.fromJson(json, (v) => parse(_map(v))).data;
  }

  Gym _gym(Map<String, dynamic> d) {
    final latitude = _number(
      d['latitude'] ?? _mapOrNull(d['location'])?['latitude'],
    );
    final longitude = _number(
      d['longitude'] ?? _mapOrNull(d['location'])?['longitude'],
    );
    final location = latitude != null && longitude != null
        ? GymLocation(
            latitude: latitude,
            longitude: longitude,
            addressLine:
                (d['address_line'] ??
                        _mapOrNull(d['location'])?['address_line'])
                    as String? ??
                '',
            neighbourhood:
                (d['neighbourhood'] ??
                        _mapOrNull(d['location'])?['neighbourhood'])
                    as String? ??
                '',
            city:
                (d['city'] ?? _mapOrNull(d['location'])?['city']) as String? ??
                '',
            countryCode:
                (d['country_code'] ??
                        _mapOrNull(d['location'])?['country_code'])
                    as String? ??
                'KE',
          )
        : null;
    return Gym(
      id: _string(d, 'id'),
      name: _string(d, 'name'),
      phoneNumber: d['phone_number'] as String?,
      email: d['email'] as String?,
      description: d['description'] as String?,
      location: location,
      legalBusinessName: d['legal_business_name'] as String?,
      businessType: d['business_type'] as String?,
      registrationNumber: d['registration_number'] as String?,
      taxNumber: d['tax_number'] as String?,
      contactPersonName: d['contact_person_name'] as String?,
      contactPersonPhone: d['contact_person_phone'] as String?,
    );
  }

  Map<String, dynamic>? _mapOrNull(Object? value) => value is Map
      ? value.map((key, value) => MapEntry(key.toString(), value))
      : null;

  double? _number(Object? value) =>
      value is num ? value.toDouble() : double.tryParse('$value');
  Map<String, dynamic> _map(Object? v) {
    if (v is Map<String, dynamic>) return v;
    throw const FormatException('The server response is invalid.');
  }

  String _string(Map<String, dynamic> d, String k) {
    final v = d[k];
    if (v is String && v.isNotEmpty) return v;
    throw FormatException('Missing $k in server response.');
  }

  Map<String, String> _headers(Object? value) {
    if (value is! Map) return const {};
    return value.map(
      (key, value) => MapEntry(key.toString(), value.toString()),
    );
  }
}
