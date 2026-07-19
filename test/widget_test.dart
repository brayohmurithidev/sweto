import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/app/app.dart';
import 'package:sweto_app/core/config/app_config.dart';
import 'package:sweto_app/core/config/app_environment.dart';
import 'package:sweto_app/core/config/config_providers.dart';
import 'package:sweto_app/features/health/data/health_providers.dart';
import 'package:sweto_app/features/health/domain/health_status.dart';

void main() {
  testWidgets('SWETO displays API loading state', (tester) async {
    final completer = Completer<HealthStatus>();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appConfigProvider.overrideWithValue(
            const AppConfig(
              environment: AppEnvironment.local,
              apiBaseUrl: 'http://localhost:8000',
            ),
          ),
          healthCheckProvider.overrideWith(
                (ref) => completer.future,
          ),
        ],
        child: const SwetoApp(),
      ),
    );

    expect(
      find.text('Connecting to SWETO API…'),
      findsOneWidget,
    );

    completer.complete(
      const HealthStatus(status: 'healthy'),
    );

    await tester.pumpAndSettle();
  });
}