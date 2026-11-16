import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/theme/app_theme.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_repository.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/more_tab.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';
import 'package:sweto_app/features/staff/domain/staff_entities.dart';
import 'package:sweto_app/features/staff/presentation/staff_providers.dart';
import 'package:sweto_app/features/staff/presentation/staff_screen.dart';

import 'support/fake_auth_repository.dart';
import 'support/fake_staff_repository.dart';

const _owner = StaffMember(
  id: 'owner-row',
  fullName: 'Brian Owner',
  phoneNumber: '+254700000001',
  role: StaffRole.owner,
  status: 'active',
  isPrimaryOwner: true,
  hasSignedIn: true,
);

const _desk = StaffMember(
  id: 'desk-row',
  fullName: 'Wanjiku Kamau',
  phoneNumber: '+254744000000',
  role: StaffRole.receptionist,
  status: 'active',
  isPrimaryOwner: false,
  hasSignedIn: false,
);

void main() {
  Widget app(Widget child, FakeStaffRepository staff) => ProviderScope(
    overrides: [
      staffRepositoryProvider.overrideWithValue(staff),
      gymAccessProvider.overrideWith(() => _FixedAccess(staff.access)),
    ],
    child: MaterialApp.router(
      theme: AppTheme.dark(),
      routerConfig: GoRouter(
        routes: [
          GoRoute(
            path: '/',
            builder: (_, _) => Scaffold(body: child),
          ),
          GoRoute(
            path: '/gyms/:gymId/:page',
            name: 'any',
            builder: (_, _) => const SizedBox(),
          ),
        ],
      ),
    ),
  );

  Widget more() => MoreTab(gymId: 'gym-1', gymName: 'FlexFit', onLogout: () {});

  group('More tab by role', () {
    testWidgets('the owner sees settings, staff and the M-Pesa till', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(800, 2400);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(app(more(), FakeStaffRepository()));
      for (final key in [
        'more-gym-profile',
        'more-staff',
        'more-check-in',
        'more-mpesa-till',
      ]) {
        expect(find.byKey(Key(key)), findsOneWidget, reason: key);
      }
    });

    testWidgets('a receptionist sees only the door and their role', (
      tester,
    ) async {
      final staff = FakeStaffRepository(
        access: FakeStaffRepository.accessFor(StaffRole.receptionist),
      );
      await tester.pumpWidget(app(more(), staff));

      expect(find.text("You're receptionist here"), findsOneWidget);
      expect(find.byKey(const Key('more-check-in')), findsOneWidget);
      for (final key in ['more-gym-profile', 'more-staff', 'more-mpesa-till']) {
        expect(find.byKey(Key(key)), findsNothing, reason: key);
      }
    });

    testWidgets('a manager edits the gym but not staff or the till', (
      tester,
    ) async {
      final staff = FakeStaffRepository(
        access: FakeStaffRepository.accessFor(StaffRole.manager),
      );
      await tester.pumpWidget(app(more(), staff));

      expect(find.byKey(const Key('more-gym-profile')), findsOneWidget);
      expect(find.byKey(const Key('more-staff')), findsNothing);
      expect(find.byKey(const Key('more-mpesa-till')), findsNothing);
    });
  });

  group('Staff screen', () {
    testWidgets('lists the team, marking invites', (tester) async {
      final staff = FakeStaffRepository(staff: [_owner, _desk]);
      await tester.pumpWidget(app(const StaffScreen(gymId: 'gym-1'), staff));
      await tester.pumpAndSettle();

      expect(find.text('Brian Owner'), findsOneWidget);
      expect(find.text('You'), findsOneWidget);
      expect(find.text('Wanjiku Kamau'), findsOneWidget);
      expect(find.text('Invited'), findsOneWidget);
    });

    testWidgets('adds someone with a role and says the invite went', (
      tester,
    ) async {
      final staff = FakeStaffRepository(staff: [_owner]);
      await tester.pumpWidget(app(const StaffScreen(gymId: 'gym-1'), staff));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('staff-empty')), findsOneWidget);

      await tester.tap(find.byKey(const Key('add-staff-button')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('staff-name-field')),
        'Otieno Trainer',
      );
      await tester.enterText(
        find.byKey(const Key('staff-phone-field')),
        '0755 000 000',
      );
      await tester.tap(find.byKey(const Key('staff-role-trainer')));
      await tester.pump();
      await tester.ensureVisible(find.byKey(const Key('add-staff-submit')));
      await tester.tap(find.byKey(const Key('add-staff-submit')));
      await tester.pumpAndSettle();

      expect(staff.added, [
        ('Otieno Trainer', '0755 000 000', StaffRole.trainer),
      ]);
      expect(find.textContaining('We texted them'), findsOneWidget);
      expect(find.text('Otieno Trainer'), findsOneWidget);
    });

    testWidgets('a missing name is caught before sending', (tester) async {
      final staff = FakeStaffRepository(staff: [_owner]);
      await tester.pumpWidget(app(const StaffScreen(gymId: 'gym-1'), staff));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('add-staff-button')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('add-staff-submit')));
      await tester.tap(find.byKey(const Key('add-staff-submit')));
      await tester.pump();

      expect(find.text('Enter their name.'), findsOneWidget);
      expect(staff.added, isEmpty);
    });

    testWidgets('changes a role, pauses and removes', (tester) async {
      final staff = FakeStaffRepository(staff: [_owner, _desk]);
      await tester.pumpWidget(app(const StaffScreen(gymId: 'gym-1'), staff));
      await tester.pumpAndSettle();

      // The owner's own row cannot be changed.
      await tester.tap(find.byKey(const Key('staff-owner-row')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('save-staff-role')), findsNothing);

      await tester.tap(find.byKey(const Key('staff-desk-row')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('staff-role-manager')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('save-staff-role')));
      await tester.pumpAndSettle();
      expect(staff.updates.last, ('desk-row', StaffRole.manager, null));

      await tester.tap(find.byKey(const Key('staff-desk-row')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('pause-staff')));
      await tester.tap(find.byKey(const Key('pause-staff')));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Pause access'));
      await tester.pumpAndSettle();
      expect(staff.updates.last, ('desk-row', null, true));
      expect(find.text('Paused'), findsOneWidget);

      await tester.tap(find.byKey(const Key('staff-desk-row')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('remove-staff')));
      await tester.tap(find.byKey(const Key('remove-staff')));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Remove'));
      await tester.pumpAndSettle();
      expect(staff.removed, ['desk-row']);
      expect(find.text('Wanjiku Kamau'), findsNothing);
    });
  });

  group('sign-in routing', () {
    test('staff go straight to their gym', () async {
      final coordinator = OnboardingCoordinator(
        _StaffAuth('gym_staff'),
        _NoGyms(),
      );
      expect(await coordinator.resolve(), OnboardingDestination.home);
    });

    test('paused staff see that their access is paused', () async {
      final coordinator = OnboardingCoordinator(
        _StaffAuth('staff_suspended'),
        _NoGyms(),
      );
      expect(await coordinator.resolve(), OnboardingDestination.staffSuspended);
    });
  });
}

class _StaffAuth extends FakeAuthRepository {
  _StaffAuth(this.step);
  final String step;

  @override
  Future<AccountOnboarding> getOnboarding() async => AccountOnboarding(
    roles: const [],
    defaultRole: null,
    status: AccountOnboardingStatus.completed,
    completed: true,
    nextStep: step,
  );
}

class _NoGyms extends Fake implements GymOwnerRepository {}

class _FixedAccess extends GymAccessNotifier {
  _FixedAccess(this.access);
  final GymAccess access;

  @override
  GymAccess build() => access;
}
