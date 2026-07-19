import 'dart:async';

import 'package:dio/dio.dart';
import 'package:sweto_app/core/network/api_endpoints.dart';
import 'package:sweto_app/core/storage/token_storage.dart';

class TokenRefreshInterceptor extends QueuedInterceptor {
  TokenRefreshInterceptor(this._storage, {required String baseUrl})
    : _refreshDio = Dio(
        BaseOptions(
          baseUrl: baseUrl,
          headers: const {'Accept': 'application/json'},
        ),
      );

  final TokenStorage _storage;
  final Dio _refreshDio;
  Future<String?>? _refreshing;

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final options = err.requestOptions;
    final eligible =
        err.response?.statusCode == 401 &&
        options.extra['requiresAuthentication'] != false &&
        options.extra['retriedAfterRefresh'] != true &&
        options.extra['skipRefresh'] != true;
    if (!eligible) return handler.next(err);
    final accessToken = await (_refreshing ??= _refreshAccessToken());
    _refreshing = null;
    if (accessToken == null) return handler.next(err);
    try {
      options.extra['retriedAfterRefresh'] = true;
      options.headers['Authorization'] = 'Bearer $accessToken';
      final response = await _refreshDio.fetch<dynamic>(options);
      handler.resolve(response);
    } on DioException catch (retryError) {
      handler.next(retryError);
    }
  }

  Future<String?> _refreshAccessToken() async {
    final refreshToken = await _storage.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) return null;
    try {
      final response = await _refreshDio.post<Map<String, dynamic>>(
        ApiEndpoints.refreshToken,
        data: {'refresh_token': refreshToken, 'platform': 'flutter'},
      );
      final data = response.data?['data'];
      final tokens = data is Map<String, dynamic> ? data['tokens'] : null;
      if (tokens is! Map<String, dynamic> ||
          tokens['access_token'] is! String ||
          tokens['refresh_token'] is! String) {
        return null;
      }
      await _storage.saveTokens(
        accessToken: tokens['access_token'] as String,
        refreshToken: tokens['refresh_token'] as String,
      );
      return tokens['access_token'] as String;
    } catch (_) {
      await _storage.deleteTokens();
      return null;
    }
  }
}
