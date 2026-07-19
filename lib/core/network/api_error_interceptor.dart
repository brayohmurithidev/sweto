import 'package:dio/dio.dart';
import 'package:sweto_app/core/network/api_exception.dart';

class ApiErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final response = err.response;
    final data = response?.data;

    String message = 'Something went wrong. Please try again.';
    String? code;
    Object? details;

    if (data is Map<String, dynamic>) {
      final errorData = data['error'];

      if (errorData is Map<String, dynamic>) {
        message = _readString(errorData['message']) ?? message;
        code = _readString(errorData['code']);
        details = errorData['details'];
      } else {
        message =
            _readString(data['message']) ??
            _readString(data['detail']) ??
            message;

        code = _readString(data['code']);
        details = data['details'];
      }
    } else if (data is String && data.trim().isNotEmpty) {
      message = data;
    } else {
      message = _messageForDioError(err);
    }

    final apiException = ApiException(
      message: message,
      statusCode: response?.statusCode,
      code: code,
      details: details,
    );

    handler.reject(err.copyWith(error: apiException));
  }

  String? _readString(Object? value) {
    if (value is String && value.trim().isNotEmpty) {
      return value;
    }

    return null;
  }

  String _messageForDioError(DioException error) {
    return switch (error.type) {
      DioExceptionType.connectionTimeout =>
        'The connection timed out. Please try again.',
      DioExceptionType.sendTimeout => 'The request took too long to send.',
      DioExceptionType.receiveTimeout => 'The server took too long to respond.',
      DioExceptionType.connectionError =>
        'Unable to connect. Check your internet connection.',
      DioExceptionType.badCertificate =>
        'A secure connection could not be established.',
      DioExceptionType.cancel => 'The request was cancelled.',
      _ => 'Something went wrong. Please try again.',
    };
  }
}
