import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/network/api_exception.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_repository.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/domain/members_repository.dart';
import 'package:sweto_app/features/members/presentation/add_member_screen.dart';
import 'package:sweto_app/features/members/presentation/member_detail_screen.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/features/members/presentation/members_screen.dart';

const _gymId = 'gym-1';
final _today = DateTime(2026, 11, 14);

GymMember _member(
  String id,
  String name, {
  MemberStanding standing = MemberStanding.active,
  DateTime? paidUntil,
  MemberStatus status = MemberStatus.active,
}) => GymMember(
  id: id,
  fullName: name,
  phoneNumber: '+2547110000${id.padLeft(2, '0')}',
  status: status,
  standing: standing,
  paidUntil: standing == MemberStanding.noMembership
      ? null
      : paidUntil ?? DateTime(2026, 12, 13),
);

DioException _apiError(String message) => DioException(
  requestOptions: RequestOptions(),
  error: ApiException(message: message, statusCode: 422),
);

class _FakeMembers implements MembersRepository {
  final members = <GymMember>[];
  final listCalls = <(MemberStanding?, String?)>[];
  final added = <(String, String)>[];
  final payments = <(String, CashPaymentInput)>[];
  Object? addError;
  Object? paymentError;
  Object? listError;

  @override
  Future<MemberPage> listMembers(
    String gymId, {
    MemberStanding? standing,
    String? search,
    bool archived = false,
    int limit = 30,
    int offset = 0,
  }) async {
    listCalls.add((standing, search));
    if (listError != null) throw listError!;
    final found = members
        .where((m) => standing == null || m.standing == standing)
        .where(
          (m) =>
              search == null ||
              search.isEmpty ||
              m.fullName.toLowerCase().contains(search.toLowerCase()),
        )
        .toList();
    return MemberPage(members: found, total: found.length);
  }

  @override
  Future<GymMember> addMember(
    String gymId, {
    required String fullName,
    required String phoneNumber,
  }) async {
    if (addError != null) throw addError!;
    added.add((fullName, phoneNumber));
    final member = _member(
      'm-new',
      fullName,
      standing: MemberStanding.noMembership,
    );
    members.add(member);
    return member;
  }

  @override
  Future<MemberDetail> getMember(String gymId, String memberId) async =>
      MemberDetail(
        member: members.firstWhere((m) => m.id == memberId),
        memberships: [
          for (final (id, input) in payments)
            if (id == memberId)
              GymMembership(
                id: 'ms-${payments.length}',
                planName: 'Monthly',
                amount: (input.amount ?? 5000).toDouble(),
                currency: 'KES',
                startsOn: _today,
                endsOn: DateTime(2026, 12, 13),
                status: 'active',
              ),
        ],
      );

  @override
  Future<GymMember> setArchived(
    String gymId,
    String memberId, {
    required bool archived,
  }) async => throw UnimplementedError();

  @override
  Future<MemberDetail> recordCashPayment(
    String gymId,
    String memberId,
    CashPaymentInput input,
  ) async {
    if (paymentError != null) throw paymentError!;
    payments.add((memberId, input));
    final index = members.indexWhere((m) => m.id == memberId);
    members[index] = _member(memberId, members[index].fullName);
    return getMember(gymId, memberId);
  }
}

class _FakePricing extends Fake implements GymOwnerRepository {
  @override
  Future<GymPricing> getGymPricing(String gymId) async => const GymPricing(
    membershipPlans: [
      GymPricingPlan(
        id: 'plan-monthly',
        name: 'Monthly',
        amount: 5000,
        billingPeriod: 'monthly',
        isActive: true,
      ),
      GymPricingPlan(
        id: 'plan-weekly',
        name: 'Weekly',
        amount: 1500,
        billingPeriod: 'weekly',
        isActive: true,
      ),
      GymPricingPlan(
        id: 'plan-off',
        name: 'Annual',
        amount: 50000,
        billingPeriod: 'annual',
        isActive: false,
      ),
    ],
  );
}

Future<void> _pump(
  WidgetTester tester,
  _FakeMembers members, {
  required String location,
}) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final router = GoRouter(
    initialLocation: location,
    routes: [
      GoRoute(
        path: AppRoutes.membersPath,
        name: AppRoutes.membersName,
        builder: (_, s) => MembersScreen(gymId: s.pathParameters['gymId']!),
      ),
      GoRoute(
        path: AppRoutes.addMemberPath,
        name: AppRoutes.addMemberName,
        builder: (_, s) =>
            AddMemberScreen(gymId: s.pathParameters['gymId']!, today: _today),
      ),
      GoRoute(
        path: AppRoutes.memberDetailPath,
        name: AppRoutes.memberDetailName,
        builder: (_, s) => MemberDetailScreen(
          gymId: s.pathParameters['gymId']!,
          memberId: s.pathParameters['memberId']!,
        ),
      ),
    ],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        membersRepositoryProvider.overrideWithValue(members),
        gymOwnerRepositoryProvider.overrideWithValue(_FakePricing()),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  group('member list', () {
    testWidgets('tabs filter by standing and search narrows the list', (
      tester,
    ) async {
      final repo = _FakeMembers()
        ..members.addAll([
          _member('1', 'Achieng Otieno'),
          _member(
            '2',
            'Brian Kiprop',
            standing: MemberStanding.expiring,
            paidUntil: DateTime(2026, 11, 18),
          ),
          _member(
            '3',
            'Chebet Wanjiku',
            standing: MemberStanding.expired,
            paidUntil: DateTime(2026, 11, 1),
          ),
          _member('4', 'Daudi Mwangi', standing: MemberStanding.noMembership),
        ]);
      await _pump(tester, repo, location: '/gyms/$_gymId/members');

      expect(find.text('Achieng Otieno'), findsOneWidget);
      expect(find.text('Until 13 Dec 2026'), findsOneWidget);
      expect(find.text('Brian Kiprop'), findsNothing);

      await tester.tap(find.byKey(const Key('members-tab-expiring')));
      await tester.pumpAndSettle();
      expect(repo.listCalls.last.$1, MemberStanding.expiring);
      expect(find.text('Brian Kiprop'), findsOneWidget);
      expect(find.text('Ends 18 Nov 2026'), findsOneWidget);

      await tester.tap(find.byKey(const Key('members-tab-expired')));
      await tester.pumpAndSettle();
      expect(find.text('Expired 1 Nov 2026'), findsOneWidget);

      await tester.tap(find.byKey(const Key('members-tab-neverPaid')));
      await tester.pumpAndSettle();
      expect(find.text('Daudi Mwangi'), findsOneWidget);
      expect(
        find.descendant(
          of: find.byKey(const Key('member-row-4')),
          matching: find.text('Never paid'),
        ),
        findsOneWidget,
      );

      await tester.enterText(find.byKey(const Key('members-search')), 'zz');
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pumpAndSettle();
      expect(repo.listCalls.last, (MemberStanding.noMembership, 'zz'));
      expect(find.text('No members match "zz".'), findsOneWidget);
    });

    testWidgets('a very long name fits on one line without overflow', (
      tester,
    ) async {
      final repo = _FakeMembers()..members.add(_member('1', 'Wanjiru ' * 12));
      await _pump(tester, repo, location: '/gyms/$_gymId/members');

      expect(tester.takeException(), isNull);
      final name = tester.widget<Text>(find.textContaining('Wanjiru'));
      expect(name.maxLines, 1);
      expect(name.overflow, TextOverflow.ellipsis);
    });

    testWidgets('a failed load shows a friendly error and retries', (
      tester,
    ) async {
      final repo = _FakeMembers()
        ..listError = DioException(requestOptions: RequestOptions());
      await _pump(tester, repo, location: '/gyms/$_gymId/members');

      expect(find.byKey(const Key('members-error')), findsOneWidget);
      expect(find.text('Something went wrong. Please try again.'), findsOne);

      repo
        ..listError = null
        ..members.add(_member('1', 'Achieng Otieno'));
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(find.text('Achieng Otieno'), findsOneWidget);
    });
  });

  group('add member', () {
    testWidgets('name and phone are required and the phone must be valid', (
      tester,
    ) async {
      final repo = _FakeMembers();
      await _pump(tester, repo, location: '/gyms/$_gymId/members/new');

      await tester.tap(find.byKey(const Key('add-member-submit')));
      await tester.pumpAndSettle();
      expect(find.text('Enter the member\'s name.'), findsOneWidget);
      expect(find.text('Enter the member\'s phone number.'), findsOneWidget);

      await tester.enterText(
        find.byKey(const Key('member-name-field')),
        'Achieng',
      );
      await tester.enterText(
        find.byKey(const Key('member-phone-input')),
        '12345',
      );
      await tester.tap(find.byKey(const Key('add-member-submit')));
      await tester.pumpAndSettle();
      expect(find.text('Enter a valid mobile number for Kenya.'), findsOne);
      expect(repo.added, isEmpty);
    });

    testWidgets('adds the member and records the first cash payment', (
      tester,
    ) async {
      final repo = _FakeMembers();
      await _pump(tester, repo, location: '/gyms/$_gymId/members');
      expect(find.byKey(const Key('members-empty')), findsOneWidget);
      await tester.tap(find.byKey(const Key('add-member-button')));
      await tester.pumpAndSettle();

      // Only active plans are offered; the first is preselected.
      await tester.tap(find.byKey(const Key('cash-plan-field')));
      await tester.pumpAndSettle();
      expect(find.text('Annual · KES 50000'), findsNothing);
      await tester.tap(find.text('Weekly · KES 1500').last);
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<TextField>(find.byKey(const Key('cash-amount-field')))
            .controller!
            .text,
        '1500',
      );

      await tester.enterText(
        find.byKey(const Key('member-name-field')),
        ' Achieng Otieno ',
      );
      await tester.enterText(
        find.byKey(const Key('member-phone-input')),
        '0711000001',
      );
      await tester.tap(find.byKey(const Key('add-member-submit')));
      await tester.pumpAndSettle();

      expect(repo.added, [('Achieng Otieno', '+254711000001')]);
      expect(repo.payments.single.$2.planId, 'plan-weekly');
      expect(repo.payments.single.$2.amount, 1500);
      expect(repo.payments.single.$2.startsOn, isNull);
      // Lands on the new member's page...
      expect(find.byType(MemberDetailScreen), findsOneWidget);
      expect(find.text('Achieng Otieno'), findsWidgets);

      // ...and back on the list, which now shows them as paid.
      await tester.pageBack();
      await tester.pumpAndSettle();
      expect(find.byType(MembersScreen), findsOneWidget);
      expect(find.byKey(const Key('member-row-m-new')), findsOneWidget);
    });

    testWidgets('a duplicate phone keeps the form open with the reason', (
      tester,
    ) async {
      final repo = _FakeMembers()
        ..addError = _apiError(
          'Another member of this gym already uses this phone number.',
        );
      await _pump(tester, repo, location: '/gyms/$_gymId/members/new');

      await tester.enterText(
        find.byKey(const Key('member-name-field')),
        'Achieng',
      );
      await tester.enterText(
        find.byKey(const Key('member-phone-input')),
        '0711000001',
      );
      await tester.tap(find.byKey(const Key('add-member-submit')));
      await tester.pumpAndSettle();

      expect(
        find.text('Another member of this gym already uses this phone number.'),
        findsOneWidget,
      );
      expect(find.byType(AddMemberScreen), findsOneWidget);
      expect(repo.payments, isEmpty);
    });
  });

  group('record cash payment', () {
    testWidgets('success updates the member to paid', (tester) async {
      final repo = _FakeMembers()
        ..members.add(
          _member(
            '1',
            'Achieng Otieno',
            standing: MemberStanding.expired,
            paidUntil: DateTime(2026, 11, 1),
          ),
        );
      await _pump(tester, repo, location: '/gyms/$_gymId/members/1');
      expect(find.text('Expired 1 Nov 2026'), findsOneWidget);

      await tester.tap(find.byKey(const Key('record-cash-button')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('cash-amount-field')),
        '4500',
      );
      await tester.tap(find.byKey(const Key('cash-payment-submit')));
      await tester.pumpAndSettle();

      expect(repo.payments.single.$2.planId, 'plan-monthly');
      expect(repo.payments.single.$2.amount, 4500);
      expect(find.byKey(const Key('cash-payment-submit')), findsNothing);
      expect(
        find.descendant(
          of: find.byKey(const Key('member-detail-standing')),
          matching: find.text('Paid until 13 Dec 2026'),
        ),
        findsOneWidget,
      );
      expect(find.text('KES 4,500'), findsOneWidget);
    });

    testWidgets('failure keeps the sheet open with the reason', (tester) async {
      final repo = _FakeMembers()
        ..members.add(_member('1', 'Achieng Otieno'))
        ..paymentError = _apiError(
          'That membership plan isn\'t available. Choose an active plan.',
        );
      await _pump(tester, repo, location: '/gyms/$_gymId/members/1');

      await tester.tap(find.byKey(const Key('record-cash-button')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('cash-payment-submit')));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'That membership plan isn\'t available. Choose an active plan.',
        ),
        findsOneWidget,
      );
      expect(find.byKey(const Key('cash-payment-submit')), findsOneWidget);
      expect(repo.payments, isEmpty);
    });
  });
}
