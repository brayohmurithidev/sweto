import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:sweto_app/core/network/api_endpoints.dart';
import 'package:sweto_app/core/network/api_response.dart';
import 'package:sweto_app/core/storage/token_storage.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/repositories/auth_repository.dart';

class DioAuthRepository implements AuthRepository {
  DioAuthRepository(this._dio, this._storage);
  final Dio _dio;
  final TokenStorage _storage;

  @override
  Future<OtpChallenge> requestOtp(String phoneNumber) async {
    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.requestOtp,
      data: {'phone_number': phoneNumber},
      options: Options(extra: const {'requiresAuthentication': false}),
    );
    return _envelope(
      response.data,
      (data) => OtpChallenge(
        challengeId: _string(data, 'challenge_id'),
        phoneNumber: _string(data, 'phone_number'),
        expiresAt: DateTime.parse(_string(data, 'expires_at')),
        resendAvailableAt: DateTime.parse(_string(data, 'resend_available_at')),
      ),
    );
  }

  @override
  Future<AuthTokens> verifyOtp({
    required String challengeId,
    required String code,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.verifyOtp,
      data: {'challenge_id': challengeId, 'code': code, 'platform': 'flutter'},
      options: Options(extra: const {'requiresAuthentication': false}),
    );
    return _envelope(response.data, (data) => _tokens(_map(data['tokens'])));
  }

  @override
  Future<AuthTokens> refresh(String refreshToken) async {
    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.refreshToken,
      data: {'refresh_token': refreshToken, 'platform': 'flutter'},
      options: Options(
        extra: const {'requiresAuthentication': false, 'skipRefresh': true},
      ),
    );
    return _envelope(response.data, (data) => _tokens(_map(data['tokens'])));
  }

  @override
  Future<void> logout(String refreshToken) async {
    await _dio.post<void>(
      ApiEndpoints.logout,
      data: {'refresh_token': refreshToken},
      options: Options(
        extra: const {'requiresAuthentication': false, 'skipRefresh': true},
      ),
    );
  }

  @override
  Future<AuthUser> getMe() async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.currentUser,
    );
    return _envelope(
      response.data,
      (data) => AuthUser(
        id: _string(data, 'id'),
        mustChangePassword: data['must_change_password'] == true,
        phoneNumber: data['phone_number'] as String?,
        email: data['email'] as String?,
      ),
    );
  }

  @override
  Future<AccountOnboarding> getOnboarding() async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.accountOnboarding,
    );
    if (kDebugMode) {
      debugPrint('ACCOUNT ONBOARDING RAW RESPONSE: ${response.data}');
    }
    return _envelope(response.data, _onboardingFromData);
  }

  @override
  Future<AccountOnboarding> selectGymOwnerRole() async {
    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.accountRoles,
      data: const {'role': 'gym_owner'},
    );
    if (kDebugMode) {
      debugPrint('ROLE SELECTION ONBOARDING RAW RESPONSE: ${response.data}');
    }
    return _envelope(response.data, _onboardingFromData);
  }

  @override
  Future<void> saveTokens(AuthTokens tokens) => _storage.saveTokens(
    accessToken: tokens.accessToken,
    refreshToken: tokens.refreshToken,
  );
  @override
  Future<void> clearTokens() => _storage.deleteTokens();
  @override
  Future<String?> readRefreshToken() => _storage.readRefreshToken();

  T _envelope<T>(
    Map<String, dynamic>? response,
    T Function(Map<String, dynamic>) parse,
  ) {
    if (response == null) {
      throw const FormatException('The server returned an empty response.');
    }
    return ApiResponse<T>.fromJson(
      response,
      (value) => parse(_map(value)),
    ).data;
  }

  AuthTokens _tokens(Map<String, dynamic> json) => AuthTokens(
    accessToken: _string(json, 'access_token'),
    refreshToken: _string(json, 'refresh_token'),
  );
  Map<String, dynamic> _map(Object? value) {
    if (value is Map<String, dynamic>) return value;
    throw const FormatException('The server response is invalid.');
  }

  List<Object?> _list(Object? value) => value is List ? value : const [];

  AccountOnboarding _onboardingFromData(Map<String, dynamic> data) {
    final defaultRole = accountRoleFromApi(data['default_role']);
    return AccountOnboarding(
      roles: _list(data['roles'])
          .map(
            (item) => item is Map<String, dynamic>
                ? accountRoleFromApi(item['role'])
                : accountRoleFromApi(item),
          )
          .where((role) => role != AccountRole.unknown)
          .toList(growable: false),
      defaultRole: defaultRole == AccountRole.unknown ? null : defaultRole,
      status: accountOnboardingStatusFromApi(data['onboarding_status']),
      completed: data['onboarding_completed'] == true,
      nextStep: data['next_step'] is String ? data['next_step'] as String : '',
    );
  }

  String _string(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is String && value.isNotEmpty) return value;
    throw FormatException('Missing $key in server response.');
  }
}
