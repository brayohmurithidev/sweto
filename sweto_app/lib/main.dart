import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/app/app.dart';
import 'package:sweto_app/core/config/app_config.dart';
import 'package:sweto_app/core/config/config_providers.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  final config = AppConfig.fromEnvironment();

  runApp(
    ProviderScope(
      overrides: [appConfigProvider.overrideWithValue(config)],
      child: const SwetoApp(),
    ),
  );
}
