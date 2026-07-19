import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/config/app_config.dart';

final appConfigProvider = Provider<AppConfig>((ref) {
  throw UnimplementedError(
    'appConfigProvider must be overridden during application bootstrap.',
  );
});
