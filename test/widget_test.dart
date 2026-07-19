import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sweto_app/app/app.dart';
import 'package:sweto_app/core/config/app_config.dart';
import 'package:sweto_app/core/config/app_environment.dart';
import 'package:sweto_app/core/config/config_providers.dart';
import 'package:sweto_app/core/storage/storage_providers.dart';
import 'package:sweto_app/core/storage/token_storage.dart';
import 'package:sweto_app/features/health/data/health_providers.dart';
import 'package:sweto_app/features/health/domain/health_status.dart';
import 'package:sweto_app/shared/widgets/sweto_logo.dart';
import 'package:sweto_app/features/onboarding/presentation/onboarding_screen.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));
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
        tokenStorageProvider.overrideWithValue(_MemoryTokenStorage()),
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

    await tester.pump(const Duration(milliseconds: 2700));

    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('Find Gyms Near You'), findsOneWidget);

    expect(find.text('Next'), findsOneWidget);

    expect(find.text('Skip'), findsOneWidget);
  });

  testWidgets('onboarding next button changes pages', (tester) async {
    await tester.pumpWidget(createTestApp());

    await tester.pump(const Duration(milliseconds: 2700));

    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('Find Gyms Near You'), findsOneWidget);

    await tester.tap(find.text('Next'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('Book & Pay\nwith M-Pesa'), findsOneWidget);

    await tester.tap(find.text('Next'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('Find Your\nSweto Buddy'), findsOneWidget);

    expect(find.text('Get Started'), findsOneWidget);

    expect(find.text('I already have an account'), findsOneWidget);
  });

  testWidgets('onboarding displays first page', (tester) async {
    await tester.pumpWidget(createTestApp());

    await tester.pump(const Duration(milliseconds: 2700));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byType(OnboardingScreen), findsOneWidget);
    expect(find.text('Find Gyms Near You'), findsOneWidget);
    expect(find.text('Next'), findsOneWidget);
    expect(find.text('Skip'), findsOneWidget);
  });

  testWidgets('onboarding advances through all pages', (tester) async {
    await tester.pumpWidget(createTestApp());

    await tester.pump(const Duration(milliseconds: 2700));
    await tester.pump(const Duration(milliseconds: 500));

    await tester.tap(find.byKey(const Key('onboarding-primary-button')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('Book & Pay\nwith M-Pesa'), findsOneWidget);

    await tester.tap(find.byKey(const Key('onboarding-primary-button')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('Find Your\nSweto Buddy'), findsOneWidget);
    expect(find.text('Get Started'), findsOneWidget);
    expect(find.text('I already have an account'), findsOneWidget);
  });
}

class _MemoryTokenStorage implements TokenStorage {
  String? access;
  String? refresh;
  @override
  Future<void> deleteTokens() async {
    access = null;
    refresh = null;
  }

  @override
  Future<String?> readAccessToken() async => access;
  @override
  Future<String?> readRefreshToken() async => refresh;
  @override
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    access = accessToken;
    refresh = refreshToken;
  }
}
