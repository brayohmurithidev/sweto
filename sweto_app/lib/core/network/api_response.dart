class ApiResponse<T> {
  const ApiResponse({required this.success, required this.data});

  final bool success;
  final T data;

  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Object? value) parseData,
  ) {
    final success = json['success'];

    if (success is! bool) {
      throw const FormatException(
        'API response is missing a valid success field.',
      );
    }

    return ApiResponse(success: success, data: parseData(json['data']));
  }
}
