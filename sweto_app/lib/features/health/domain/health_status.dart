class HealthStatus {
  const HealthStatus({required this.status});

  final String status;

  factory HealthStatus.fromJson(Map<String, dynamic> json) {
    final status = json['status'];

    if (status is! String || status.trim().isEmpty) {
      throw const FormatException(
        'Health response does not contain a valid status.',
      );
    }

    return HealthStatus(status: status);
  }
}
