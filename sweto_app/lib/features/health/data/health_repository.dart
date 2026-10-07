import 'package:dio/dio.dart';
import 'package:sweto_app/core/network/api_endpoints.dart';
import 'package:sweto_app/core/network/api_response.dart';
import 'package:sweto_app/features/health/domain/health_status.dart';

class HealthRepository {
  HealthRepository(this._dio);

  final Dio _dio;

  Future<HealthStatus> checkHealth() async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.health,
      options: Options(extra: const {'requiresAuthentication': false}),
    );

    final responseData = response.data;

    if (responseData == null) {
      throw const FormatException(
        'The health endpoint returned an empty response.',
      );
    }

    final envelope = ApiResponse<HealthStatus>.fromJson(responseData, (value) {
      if (value is! Map<String, dynamic>) {
        throw const FormatException('The health response data is invalid.');
      }

      return HealthStatus.fromJson(value);
    });

    return envelope.data;
  }
}
