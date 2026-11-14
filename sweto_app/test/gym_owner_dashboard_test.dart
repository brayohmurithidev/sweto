import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_repository.dart';
import 'package:sweto_app/features/gym_owner/presentation/gym_owner_dashboard.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';

import 'support/fake_auth_repository.dart';

void main() {
  Future<void> pumpDashboard(WidgetTester tester, String status) async {
    // Tall enough that the lazily built task list is on screen.
    tester.view.physicalSize = const Size(1200, 4000);
    tester.view.devicePixelRatio = 2;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
          gymOwnerRepositoryProvider.overrideWithValue(_Gyms(status)),
        ],
        child: const MaterialApp(home: GymOwnerDashboardScreen()),
      ),
    );
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }

  Finder documentsChevron() => find.descendant(
    of: find.widgetWithText(ListTile, 'Business Documents'),
    matching: find.byIcon(Icons.arrow_forward_ios),
  );

  testWidgets('pending verification offers no way back to the documents step', (
    tester,
  ) async {
    await pumpDashboard(tester, 'pending');

    expect(find.text('Business Documents'), findsOneWidget);
    expect(find.text('Continue Verification'), findsNothing);
    expect(documentsChevron(), findsNothing);
  });

  testWidgets('unsubmitted verification still offers Continue Verification', (
    tester,
  ) async {
    await pumpDashboard(tester, 'not_submitted');

    expect(find.text('Continue Verification'), findsWidgets);
    expect(documentsChevron(), findsOneWidget);
  });

  testWidgets('rejected verification offers Review and Resubmit', (
    tester,
  ) async {
    await pumpDashboard(tester, 'rejected');

    expect(find.text('Review and Resubmit'), findsOneWidget);
    expect(documentsChevron(), findsOneWidget);
  });
}

/// Only what the dashboard reads is implemented; anything else throws.
class _Gyms extends Fake implements GymOwnerRepository {
  _Gyms(this.status);

  final String status;

  @override
  Future<Gym> getCurrentGym() async => const Gym(id: 'gym-id', name: 'FlexFit');

  @override
  Future<GymOnboarding> getGymOnboarding(String gymId) async => GymOnboarding(
    gymId: gymId,
    nextStep: GymOnboardingStep.waitingForVerification,
    completed: false,
    verificationStatus: GymVerificationStatus.pending,
  );

  @override
  Future<GymVerificationData> getGymVerification(String gymId) async =>
      GymVerificationData(
        status: status,
        requiredTypes: const [],
        missingTypes: const [],
        documents: const [],
      );
}
