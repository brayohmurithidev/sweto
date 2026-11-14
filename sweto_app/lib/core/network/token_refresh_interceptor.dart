import 'dart:async';

import 'package:dio/dio.dart';
import 'package:sweto_app/core/network/api_endpoints.dart';
import 'package:sweto_app/core/storage/token_storage.dart';

/// Called when the server has definitively rejected the session.
typedef SessionExpiredCallback = FutureOr<void> Function();

/// Refreshes the access token when an authenticated request returns 401,
/// then retries the request once.
///
/// If the refresh token is missing or the server rejects it, the stored tokens
/// are deleted and [onSessionExpired] is called so the app can end the session
/// centrally. Network failures during refresh do not end the session.
class TokenRefreshInterceptor extends QueuedInterceptor {
  TokenRefreshInterceptor(
    this._storage, {
    required String baseUrl,
    this.onSessionExpired,
    Dio? refreshDio,
  }) : _refreshDio =
           refreshDio ??
           Dio(
             BaseOptions(
               baseUrl: baseUrl,
               headers: const {'Accept': 'application/json'},
             ),
           );

  final TokenStorage _storage;
  final Dio _refreshDio;
  final SessionExpiredCallback? onSessionExpired;

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

    // Requests are queued, so an earlier request may already have refreshed
    // the session. Retry with the newer token instead of refreshing again.
    final storedAccessToken = await _storage.readAccessToken();
    final usedAuthorization = options.headers['Authorization'];
    if (storedAccessToken != null &&
        storedAccessToken.isNotEmpty &&
        usedAuthorization != 'Bearer $storedAccessToken') {
      return _retry(options, storedAccessToken, handler);
    }

    final result = await _refreshAccessToken();
    final refreshedToken = result.accessToken;
    if (refreshedToken != null) {
      return _retry(options, refreshedToken, handler);
    }
    if (result.rejected) {
      await _storage.deleteTokens();
      await onSessionExpired?.call();
    }
    return handler.next(err);
  }

  Future<void> _retry(
    RequestOptions options,
    String accessToken,
    ErrorInterceptorHandler handler,
  ) async {
    try {
      options.extra['retriedAfterRefresh'] = true;
      options.headers['Authorization'] = 'Bearer $accessToken';
      final response = await _refreshDio.fetch<dynamic>(options);
      handler.resolve(response);
    } on DioException catch (retryError) {
      handler.next(retryError);
    }
  }

  Future<_RefreshResult> _refreshAccessToken() async {
    final refreshToken = await _storage.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      return const _RefreshResult.rejected();
    }
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
        return const _RefreshResult.rejected();
      }
      final accessToken = tokens['access_token'] as String;
      await _storage.saveTokens(
        accessToken: accessToken,
        refreshToken: tokens['refresh_token'] as String,
      );
      return _RefreshResult.refreshed(accessToken);
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      final rejected =
          status == 400 || status == 401 || status == 403 || status == 422;
      return rejected
          ? const _RefreshResult.rejected()
          : const _RefreshResult.unavailable();
    }
  }
}

final class _RefreshResult {
  const _RefreshResult.refreshed(String this.accessToken) : rejected = false;
  const _RefreshResult.rejected() : accessToken = null, rejected = true;
  const _RefreshResult.unavailable() : accessToken = null, rejected = false;

  final String? accessToken;
  final bool rejected;
}
