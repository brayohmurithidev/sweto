import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/config/config_providers.dart';
import 'package:sweto_app/core/network/api_error_interceptor.dart';
import 'package:sweto_app/core/network/auth_interceptor.dart';
import 'package:sweto_app/core/network/token_refresh_interceptor.dart';
import 'package:sweto_app/core/storage/storage_providers.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';

final dioProvider = Provider<Dio>((ref) {
  final config = ref.watch(appConfigProvider);
  final tokenStorage = ref.watch(tokenStorageProvider);

  final dio = Dio(
    BaseOptions(
      baseUrl: config.apiBaseUrl,
      connectTimeout: const Duration(seconds: 15),
      sendTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      headers: const {'Accept': 'application/json'},
    ),
  );

  dio.interceptors.addAll([
    AuthInterceptor(tokenStorage),
    TokenRefreshInterceptor(
      tokenStorage,
      baseUrl: config.apiBaseUrl,
      // Session expiry is handled once, centrally: the session controller
      // clears local state and the router returns the user to sign-in.
      onSessionExpired: () =>
          ref.read(sessionControllerProvider.notifier).expire(),
    ),
    ApiErrorInterceptor(),
  ]);

  return dio;
});
