import 'package:sweto_app/core/config/app_environment.dart';

class AppConfig {
  const AppConfig({required this.environment, required this.apiBaseUrl});

  final AppEnvironment environment;
  final String apiBaseUrl;

  bool get isLocal => environment == AppEnvironment.local;

  bool get isStaging => environment == AppEnvironment.staging;

  bool get isProduction => environment == AppEnvironment.production;

  factory AppConfig.fromEnvironment() {
    const environmentValue = String.fromEnvironment(
      'APP_ENV',
      defaultValue: 'local',
    );

    const apiBaseUrl = String.fromEnvironment('API_BASE_URL');

    if (apiBaseUrl.trim().isEmpty) {
      throw StateError(
        'API_BASE_URL is missing. '
        'Run the app with --dart-define=API_BASE_URL=<url>.',
      );
    }

    final parsedUri = Uri.tryParse(apiBaseUrl);

    if (parsedUri == null || !parsedUri.hasScheme || !parsedUri.hasAuthority) {
      throw StateError(
        'API_BASE_URL must be a valid absolute URL. '
        'Received: $apiBaseUrl',
      );
    }

    if (environmentValue == 'production' &&
        parsedUri.scheme.toLowerCase() != 'https') {
      throw StateError('Production API_BASE_URL must use HTTPS.');
    }

    return AppConfig(
      environment: AppEnvironment.fromValue(environmentValue),
      apiBaseUrl: apiBaseUrl.replaceFirst(RegExp(r'/$'), ''),
    );
  }
}
