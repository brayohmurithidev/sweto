import 'package:dio/dio.dart';
import 'package:sweto_app/core/network/api_endpoints.dart';
import 'package:sweto_app/core/network/api_response.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/repositories/otp_delivery_repository.dart';

class DioOtpDeliveryRepository implements OtpDeliveryRepository {
  DioOtpDeliveryRepository(this._dio);

  final Dio _dio;

  static Options get _public =>
      Options(extra: const {'requiresAuthentication': false});

  @override
  Future<List<SignInCountry>> getSignInCountries() async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.phoneCountries,
      options: _public,
    );
    final data = _data(response.data);
    final countries = data['countries'];
    if (countries is! List) {
      throw const FormatException('The server response is invalid.');
    }
    return [
      for (final item in countries)
        if (item is Map<String, dynamic> && item['region'] is String)
          SignInCountry(
            isoCode: item['region'] as String,
            channel: OtpDeliveryChannel.fromApi(item['delivery_channel']),
          ),
    ];
  }

  @override
  Future<OtpDeliveryStatus> getDeliveryStatus(String challengeId) async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.otpDelivery(challengeId),
      options: _public,
    );
    return OtpDeliveryStatus.fromApi(_data(response.data)['delivery_status']);
  }

  Map<String, dynamic> _data(Map<String, dynamic>? response) {
    if (response == null) {
      throw const FormatException('The server returned an empty response.');
    }
    final data = ApiResponse<Object?>.fromJson(response, (value) => value).data;
    if (data is Map<String, dynamic>) return data;
    throw const FormatException('The server response is invalid.');
  }
}
