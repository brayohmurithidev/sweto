class ApiException implements Exception {
  const ApiException({
    required this.message,
    this.statusCode,
    this.code,
    this.details,
  });

  final String message;
  final int? statusCode;
  final String? code;
  final Object? details;

  @override
  String toString() {
    return 'ApiException('
        'statusCode: $statusCode, '
        'code: $code, '
        'message: $message'
        ')';
  }
}
