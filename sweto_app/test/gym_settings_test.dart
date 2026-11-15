import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_repository.dart';
import 'package:sweto_app/features/gym_owner/presentation/gym_owner_screens.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/more_tab.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';

import 'support/fake_auth_repository.dart';

class _Gyms extends Fake implements GymOwnerRepository {
  GymPricing pricing = const GymPricing(
    dayPasses: [
      GymPricingPlan(
        name: 'Day Pass',
        amount: 500,
        billingPeriod: 'day_pass',
        isActive: true,
      ),
    ],
    membershipPlans: [
      GymPricingPlan(
        name: 'Monthly',
        amount: 5000,
        billingPeriod: 'monthly',
        isActive: true,
      ),
      // Made outside the app: the screen has no card for it.
      GymPricingPlan(
        name: 'Weekly',
        amount: 1500,
        billingPeriod: 'weekly',
        isActive: true,
      ),
    ],
  );
  GymPricing? savedPricing;
  CreateGymInput? savedBasics;
  Set<String>? savedAmenities;

  @override
  Future<Gym> getCurrentGym() async => const Gym(
    id: 'gym-1',
    name: 'RDF Fitness Center',
    phoneNumber: '+254712345678',
    description: 'Open early.',
  );

  @override
  Future<GymPricing> getGymPricing(String gymId) async => pricing;

  @override
  Future<void> updateGymPricing(String gymId, GymPricing pricing) async =>
      savedPricing = pricing;

  @override
  Future<List<GymPhoto>> getGymPhotos(String gymId) async => const [];

  @override
  Future<Gym> updateBasicInformation(String gymId, CreateGymInput input) async {
    savedBasics = input;
    return Gym(id: gymId, name: input.name);
  }

  @override
  Future<List<GymAmenity>> getAmenities() async => const [
    GymAmenity(id: 'a1', name: 'Showers', slug: 'showers', displayOrder: 1),
    GymAmenity(id: 'a2', name: 'Parking', slug: 'parking', displayOrder: 2),
  ];

  @override
  Future<List<GymAmenity>> getGymAmenities(String gymId) async => const [
    GymAmenity(id: 'a1', name: 'Showers', slug: 'showers', displayOrder: 1),
  ];

  @override
  Future<void> updateGymAmenities(String gymId, Set<String> amenityIds) async =>
      savedAmenities = amenityIds;
}

Future<_Gyms> _pump(WidgetTester tester, String route) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final gyms = _Gyms();
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, _) => Scaffold(
          body: MoreTab(gymId: 'gym-1', gymName: 'RDF', onLogout: () {}),
        ),
      ),
      GoRoute(
        path: AppRoutes.gymProfileSettingsPath,
        name: AppRoutes.gymProfileSettingsName,
        builder: (_, _) => const GymRegistrationScreen(inSettings: true),
      ),
      GoRoute(
        path: AppRoutes.gymPlansSettingsPath,
        name: AppRoutes.gymPlansSettingsName,
        builder: (_, _) => const GymPricingScreen(inSettings: true),
      ),
      GoRoute(
        path: AppRoutes.gymAmenitiesSettingsPath,
        name: AppRoutes.gymAmenitiesSettingsName,
        builder: (_, _) => const GymAmenitiesScreen(inSettings: true),
      ),
      for (final (path, name) in [
        (AppRoutes.gymHoursSettingsPath, AppRoutes.gymHoursSettingsName),
        (AppRoutes.gymLocationSettingsPath, AppRoutes.gymLocationSettingsName),
      ])
        GoRoute(path: path, name: name, builder: (_, _) => Text('open $name')),
    ],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        gymOwnerRepositoryProvider.overrideWithValue(gyms),
        authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(Key(route)));
  await tester.pumpAndSettle();
  return gyms;
}

Future<void> _save(WidgetTester tester, Key button) async {
  await tester.ensureVisible(find.byKey(button));
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(button));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('More lists the gym\'s details and opens each', (tester) async {
    await _pump(tester, 'more-gym-hours');
    expect(find.text('open ${AppRoutes.gymHoursSettingsName}'), findsOneWidget);
  });

  testWidgets('plans save from More without leaving the gym', (tester) async {
    final gyms = await _pump(tester, 'more-gym-plans');

    expect(find.text('Plans & prices'), findsOneWidget);
    expect(find.textContaining('Step'), findsNothing);
    expect(find.text('Save changes'), findsOneWidget);

    await _save(tester, const Key('gym-pricing-continue'));

    final saved = gyms.savedPricing!;
    expect(saved.dayPasses.map((p) => (p.name, p.amount)), [('Day Pass', 500)]);
    // Weekly has no card here but is kept, not deleted.
    expect(saved.membershipPlans.map((p) => (p.name, p.amount)), [
      ('Monthly', 5000),
      ('Weekly', 1500),
    ]);
    expect(find.text('Changes saved.'), findsOneWidget);
    expect(find.byKey(const Key('more-gym-plans')), findsOneWidget);
  });

  testWidgets('the gym profile saves its new name and comes back', (
    tester,
  ) async {
    final gyms = await _pump(tester, 'more-gym-profile');

    expect(find.text('Gym profile'), findsOneWidget);
    expect(find.text('Register Your Gym'), findsNothing);
    await tester.enterText(
      find.byKey(const Key('gym-name-field')),
      'RDF Fitness Westlands',
    );
    await _save(tester, const Key('create-gym-button'));

    expect(gyms.savedBasics!.name, 'RDF Fitness Westlands');
    expect(gyms.savedBasics!.description, 'Open early.');
    expect(find.text('Changes saved.'), findsOneWidget);
    expect(find.byKey(const Key('more-gym-profile')), findsOneWidget);
  });

  testWidgets('amenities save and back goes back without saving', (
    tester,
  ) async {
    var gyms = await _pump(tester, 'more-gym-amenities');
    await tester.tap(find.byKey(const Key('settings-back')));
    await tester.pumpAndSettle();
    expect(gyms.savedAmenities, isNull);
    expect(find.byKey(const Key('more-gym-amenities')), findsOneWidget);

    gyms = await _pump(tester, 'more-gym-amenities');
    await tester.tap(find.text('Parking'));
    await tester.pump();
    await _save(tester, const Key('gym-amenities-continue'));
    expect(gyms.savedAmenities, {'a1', 'a2'});
    expect(find.text('Changes saved.'), findsOneWidget);
  });
}
