enum AppEnvironment {
  local,
  staging,
  production;

  static AppEnvironment fromValue(String value) {
    return switch (value.toLowerCase()) {
      'local' => AppEnvironment.local,
      'staging' => AppEnvironment.staging,
      'production' => AppEnvironment.production,
      _ => throw ArgumentError(
        'Unsupported APP_ENV "$value". '
        'Use local, staging, or production.',
      ),
    };
  }
}
