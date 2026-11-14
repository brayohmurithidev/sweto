import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/core/network/token_refresh_interceptor.dart';
import 'package:sweto_app/core/storage/token_storage.dart';

void main() {
  late _MemoryTokenStorage storage;
  late _ScriptedAdapter refreshAdapter;
  late Dio dio;
  late int expiredCalls;

  setUp(() {
    storage = _MemoryTokenStorage()
      ..access = 'old-access'
      ..refresh = 'old-refresh';
    refreshAdapter = _ScriptedAdapter();
    expiredCalls = 0;

    final refreshDio = Dio(BaseOptions(baseUrl: 'http://api.test'))
      ..httpClientAdapter = refreshAdapter;
    dio = Dio(BaseOptions(baseUrl: 'http://api.test'))
      // Every first attempt at the protected endpoint is unauthorised.
      ..httpClientAdapter = _ScriptedAdapter(
        responses: {'/protected': (_) => _json(401, {'error': 'expired'})},
      )
      ..interceptors.add(
        TokenRefreshInterceptor(
          storage,
          baseUrl: 'http://api.test',
          refreshDio: refreshDio,
          onSessionExpired: () {
            expiredCalls++;
          },
        ),
      );
  });

  Future<Response<dynamic>> callProtected() => dio.get<dynamic>(
    '/protected',
    options: Options(headers: {'Authorization': 'Bearer old-access'}),
  );

  test('refreshes, stores the new tokens and retries the request', () async {
    refreshAdapter.responses['/api/v1/auth/refresh'] = (_) => _json(200, {
      'data': {
        'tokens': {'access_token': 'new-access', 'refresh_token': 'new-refresh'},
      },
    });
    refreshAdapter.responses['/protected'] = (options) => _json(200, {
      'authorization': options.headers['Authorization'],
    });

    final response = await callProtected();

    expect(response.statusCode, 200);
    expect(response.data, {'authorization': 'Bearer new-access'});
    expect(storage.access, 'new-access');
    expect(storage.refresh, 'new-refresh');
    expect(expiredCalls, 0);
  });

  test('a rejected refresh clears tokens and expires the session', () async {
    refreshAdapter.responses['/api/v1/auth/refresh'] = (_) => _json(401, {
      'error': {'code': 'REFRESH_SESSION_REVOKED', 'message': 'Revoked'},
    });

    await expectLater(callProtected(), throwsA(isA<DioException>()));

    expect(expiredCalls, 1);
    expect(storage.access, isNull);
    expect(storage.refresh, isNull);
  });

  test('a missing refresh token expires the session', () async {
    storage.refresh = null;

    await expectLater(callProtected(), throwsA(isA<DioException>()));

    expect(expiredCalls, 1);
    expect(refreshAdapter.requestedPaths, isEmpty);
  });

  test('a network failure during refresh keeps the session', () async {
    refreshAdapter.responses['/api/v1/auth/refresh'] = (options) =>
        throw DioException(
          requestOptions: options,
          type: DioExceptionType.connectionError,
        );

    await expectLater(callProtected(), throwsA(isA<DioException>()));

    expect(expiredCalls, 0);
    expect(storage.access, 'old-access');
    expect(storage.refresh, 'old-refresh');
  });

  test('requests that opt out of refresh are passed through', () async {
    await expectLater(
      dio.get<dynamic>(
        '/protected',
        options: Options(extra: const {'skipRefresh': true}),
      ),
      throwsA(isA<DioException>()),
    );

    expect(refreshAdapter.requestedPaths, isEmpty);
    expect(expiredCalls, 0);
  });

  test('retries with a token another request already refreshed', () async {
    storage.access = 'already-refreshed-access';
    refreshAdapter.responses['/protected'] = (options) => _json(200, {
      'authorization': options.headers['Authorization'],
    });

    final response = await callProtected();

    expect(response.data, {
      'authorization': 'Bearer already-refreshed-access',
    });
    expect(refreshAdapter.requestedPaths, ['/protected']);
  });
}

typedef _Responder = ResponseBody Function(RequestOptions options);

ResponseBody _json(int status, Object body) => ResponseBody.fromString(
  jsonEncode(body),
  status,
  headers: {
    Headers.contentTypeHeader: [Headers.jsonContentType],
  },
);

class _ScriptedAdapter implements HttpClientAdapter {
  _ScriptedAdapter({Map<String, _Responder>? responses})
    : responses = responses ?? {};

  final Map<String, _Responder> responses;
  final List<String> requestedPaths = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requestedPaths.add(options.path);
    final responder = responses[options.path];
    if (responder == null) {
      return _json(404, {'error': 'not scripted: ${options.path}'});
    }
    return responder(options);
  }

  @override
  void close({bool force = false}) {}
}

class _MemoryTokenStorage implements TokenStorage {
  String? access;
  String? refresh;

  @override
  Future<String?> readAccessToken() async => access;

  @override
  Future<String?> readRefreshToken() async => refresh;

  @override
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    access = accessToken;
    refresh = refreshToken;
  }

  @override
  Future<void> deleteTokens() async {
    access = null;
    refresh = null;
  }
}
