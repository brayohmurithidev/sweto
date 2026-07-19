import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/app/app.dart';
import 'package:sweto_app/core/config/app_config.dart';
import 'package:sweto_app/core/config/app_environment.dart';
import 'package:sweto_app/core/config/config_providers.dart';
import 'package:sweto_app/features/health/data/health_providers.dart';
import 'package:sweto_app/features/health/domain/health_status.dart';
import 'package:sweto_app/shared/widgets/sweto_logo.dart';

void main() {
  ProviderScope createTestApp() {
    return ProviderScope(
      overrides: [
        appConfigProvider.overrideWithValue(
          const AppConfig(
            environment: AppEnvironment.local,
            apiBaseUrl: 'http://localhost:8000',
          ),
        ),
        healthCheckProvider.overrideWith((ref) async {
          return const HealthStatus(status: 'healthy');
        }),
      ],
      child: const SwetoApp(),
    );
  }

  testWidgets('SWETO starts on the splash screen', (tester) async {
    await tester.pumpWidget(createTestApp());

    expect(find.byType(SwetoLogo), findsOneWidget);
    expect(find.text('Karibu!'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });

  testWidgets('splash navigates to onboarding screen', (tester) async {
    await tester.pumpWidget(createTestApp());

    expect(find.byType(SwetoLogo), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 2600));

    await tester.pumpAndSettle();

    expect(find.text('Find Gyms Near You'), findsOneWidget);

    expect(find.text('Next'), findsOneWidget);

    expect(find.text('Skip'), findsOneWidget);
  });

  testWidgets('onboarding next button changes pages', (tester) async {
    await tester.pumpWidget(createTestApp());

    await tester.pump(const Duration(milliseconds: 2600));

    await tester.pumpAndSettle();

    expect(find.text('Find Gyms Near You'), findsOneWidget);

    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();

    expect(find.text('Book & Pay\nwith M-Pesa'), findsOneWidget);

    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();

    expect(find.text('Find Your\nSweto Buddy'), findsOneWidget);

    expect(find.text('Get Started'), findsOneWidget);

    expect(find.text('I already have an account'), findsOneWidget);
  });
}
