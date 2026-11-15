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

GymMember fakeMember(
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

DioException fakeApiError(String message) => DioException(
  requestOptions: RequestOptions(),
  error: ApiException(message: message, statusCode: 422),
);

class FakeMembers implements MembersRepository {
  final members = <GymMember>[];
  final listCalls = <(MemberStanding?, String?)>[];
  final added = <(String, String)>[];
  final consents = <bool>[];
  final smsChanges = <(String, bool)>[];
  String? paymentSms;
  String? codeSms;
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
    bool smsConsent = false,
  }) async {
    if (addError != null) throw addError!;
    added.add((fullName, phoneNumber));
    consents.add(smsConsent);
    final member = fakeMember(
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

  final issuedCodes = <String>[];
  CheckInOutcome Function(String code)? checkInResult;
  final checkInCodes = <String>[];
  Object? checkInError;
  var today = const CheckInDay(visits: 0, refused: 0, entries: []);

  final mpesaRequests = <(String, String, int?)>[];
  final paymentUpdates = <MpesaPayment>[];
  Object? mpesaError;

  @override
  Future<MpesaPayment> requestMpesaPayment(
    String gymId,
    String memberId, {
    required String planId,
    int? amount,
  }) async {
    if (mpesaError != null) throw mpesaError!;
    mpesaRequests.add((memberId, planId, amount));
    return const MpesaPayment(
      paymentId: 'pay-1',
      state: PaymentState.pending,
      message: 'Waiting for the member to enter their M-Pesa PIN.',
    );
  }

  @override
  Future<MpesaPayment> getPayment(String gymId, String paymentId) async {
    if (paymentUpdates.length > 1) return paymentUpdates.removeAt(0);
    return paymentUpdates.single;
  }

  @override
  Future<CheckInCode> issueCheckInCode(String gymId, String memberId) async {
    issuedCodes.add(memberId);
    final index = members.indexWhere((m) => m.id == memberId);
    final m = members[index];
    members[index] = GymMember(
      id: m.id,
      fullName: m.fullName,
      phoneNumber: m.phoneNumber,
      status: m.status,
      standing: m.standing,
      paidUntil: m.paidUntil,
      hasCheckInCode: true,
    );
    return CheckInCode(
      code: '7KQ2-M9XD',
      qrPayload: 'sweto:checkin:7KQ2M9XD',
      smsStatus: codeSms,
    );
  }

  @override
  Future<CheckInOutcome> checkIn(String gymId, String code) async {
    if (checkInError != null) throw checkInError!;
    checkInCodes.add(code);
    return checkInResult!(code);
  }

  @override
  Future<CheckInDay> checkInsToday(String gymId) async => today;

  MpesaTill till = const MpesaTill(configured: false, mode: 'simulated');
  final tillSaves = <Map<String, Object?>>[];
  Object? tillError;

  @override
  Future<MpesaTill> getMpesaTill(String gymId) async => till;

  @override
  Future<MpesaTill> saveMpesaTill(
    String gymId, {
    required bool isTill,
    required String shortcode,
    String? tillNumber,
    String? passkey,
  }) async {
    if (tillError != null) throw tillError!;
    tillSaves.add({
      'isTill': isTill,
      'shortcode': shortcode,
      'tillNumber': tillNumber,
      'passkey': passkey,
    });
    return till = MpesaTill(
      configured: true,
      mode: till.mode,
      isTill: isTill,
      shortcode: shortcode,
      tillNumber: tillNumber,
      passkeySaved: true,
    );
  }

  /// Keyed by "year-month"; a missing month throws.
  final finance = <String, FinanceSummary>{};
  final financePayments = <FinanceTransaction>[];
  final financeCalls = <(DateTime?, bool?, int)>[];
  Object? financeError;

  @override
  Future<FinanceSummary> getFinance(String gymId, {DateTime? month}) async {
    if (financeError != null) throw financeError!;
    final key = month == null
        ? finance.keys.last
        : '${month.year}-${month.month}';
    return finance[key]!;
  }

  @override
  Future<FinanceTransactionPage> getFinanceTransactions(
    String gymId, {
    DateTime? month,
    bool? mpesa,
    int limit = 30,
    int offset = 0,
  }) async {
    financeCalls.add((month, mpesa, offset));
    if (financeError != null) throw financeError!;
    // No month means this month: the latest one set up.
    final wanted =
        month ?? (finance.isEmpty ? null : finance[finance.keys.last]!.month);
    final found = financePayments
        .where((t) => wanted == null || t.at.month == wanted.month)
        .where((t) => mpesa == null || t.isMpesa == mpesa)
        .toList();
    return FinanceTransactionPage(
      transactions: found.skip(offset).take(limit).toList(),
      total: found.length,
    );
  }

  DashboardSummary? dashboard;
  Object? dashboardError;
  int dashboardLoads = 0;

  @override
  Future<DashboardSummary> getDashboard(String gymId) async {
    dashboardLoads += 1;
    if (dashboardError != null) throw dashboardError!;
    return dashboard!;
  }

  @override
  Future<GymMember> setSms(
    String gymId,
    String memberId, {
    required bool enabled,
  }) async {
    smsChanges.add((memberId, enabled));
    final index = members.indexWhere((m) => m.id == memberId);
    final m = members[index];
    members[index] = GymMember(
      id: m.id,
      fullName: m.fullName,
      phoneNumber: m.phoneNumber,
      status: m.status,
      standing: m.standing,
      paidUntil: m.paidUntil,
      hasCheckInCode: m.hasCheckInCode,
      smsEnabled: enabled,
    );
    return members[index];
  }

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
    members[index] = fakeMember(memberId, members[index].fullName);
    final detail = await getMember(gymId, memberId);
    return MemberDetail(
      member: detail.member,
      memberships: detail.memberships,
      smsStatus: paymentSms,
    );
  }
}

class FakePricing extends Fake implements GymOwnerRepository {
  @override
  Future<Gym> getCurrentGym() async =>
      const Gym(id: _gymId, name: 'FlexFit Westlands');

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
  FakeMembers members, {
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
        gymOwnerRepositoryProvider.overrideWithValue(FakePricing()),
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
      final repo = FakeMembers()
        ..members.addAll([
          fakeMember('1', 'Achieng Otieno'),
          fakeMember(
            '2',
            'Brian Kiprop',
            standing: MemberStanding.expiring,
            paidUntil: DateTime(2026, 11, 18),
          ),
          fakeMember(
            '3',
            'Chebet Wanjiku',
            standing: MemberStanding.expired,
            paidUntil: DateTime(2026, 11, 1),
          ),
          fakeMember(
            '4',
            'Daudi Mwangi',
            standing: MemberStanding.noMembership,
          ),
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
      final repo = FakeMembers()..members.add(fakeMember('1', 'Wanjiru ' * 12));
      await _pump(tester, repo, location: '/gyms/$_gymId/members');

      expect(tester.takeException(), isNull);
      final name = tester.widget<Text>(find.textContaining('Wanjiru'));
      expect(name.maxLines, 1);
      expect(name.overflow, TextOverflow.ellipsis);
    });

    testWidgets('a failed load shows a friendly error and retries', (
      tester,
    ) async {
      final repo = FakeMembers()
        ..listError = DioException(requestOptions: RequestOptions());
      await _pump(tester, repo, location: '/gyms/$_gymId/members');

      expect(find.byKey(const Key('members-error')), findsOneWidget);
      expect(find.text('Something went wrong. Please try again.'), findsOne);

      repo
        ..listError = null
        ..members.add(fakeMember('1', 'Achieng Otieno'));
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(find.text('Achieng Otieno'), findsOneWidget);
    });
  });

  group('add member', () {
    testWidgets('name and phone are required and the phone must be valid', (
      tester,
    ) async {
      final repo = FakeMembers();
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
      final repo = FakeMembers();
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
      final repo = FakeMembers()
        ..addError = fakeApiError(
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
      final repo = FakeMembers()
        ..members.add(
          fakeMember(
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
      final repo = FakeMembers()
        ..members.add(fakeMember('1', 'Achieng Otieno'))
        ..paymentError = fakeApiError(
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

  group('check-in code', () {
    testWidgets('shows the new code and QR once, confirming a replacement', (
      tester,
    ) async {
      final repo = FakeMembers()
        ..members.add(fakeMember('1', 'Achieng Otieno'));
      await _pump(tester, repo, location: '/gyms/$_gymId/members/1');

      await tester.tap(find.byKey(const Key('issue-check-in-code')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('check-in-qr')), findsOneWidget);
      expect(find.text('7KQ2-M9XD'), findsOneWidget);
      await tester.tap(find.text('Done'));
      await tester.pumpAndSettle();
      expect(repo.issuedCodes, ['1']);

      // Now issued: a new code needs a confirmation first.
      expect(find.text('New code'), findsOneWidget);
      await tester.tap(find.byKey(const Key('issue-check-in-code')));
      await tester.pumpAndSettle();
      expect(find.text('Issue a new code?'), findsOneWidget);
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(repo.issuedCodes, ['1']);
    });
  });

  group('member SMS', () {
    testWidgets('consent is unticked by default and sent when ticked', (
      tester,
    ) async {
      final repo = FakeMembers()..paymentSms = 'sent';
      await _pump(tester, repo, location: '/gyms/$_gymId/members');
      await tester.tap(find.byKey(const Key('add-member-button')));
      await tester.pumpAndSettle();

      final consent = find.byKey(const Key('member-sms-consent'));
      expect(tester.widget<CheckboxListTile>(consent).value, isFalse);
      expect(
        find.text('Member agreed to receive SMS from FlexFit Westlands'),
        findsOneWidget,
      );

      await tester.enterText(
        find.byKey(const Key('member-name-field')),
        'Achieng Otieno',
      );
      await tester.enterText(
        find.byKey(const Key('member-phone-input')),
        '0711000001',
      );
      await tester.tap(consent);
      await tester.pump();
      await tester.tap(find.byKey(const Key('add-member-submit')));
      await tester.pump();

      expect(repo.consents, [true]);
      // Shown while the add screen closes and the member opens.
      expect(
        find.text('Achieng Otieno added. Welcome SMS sent.'),
        findsWidgets,
      );
    });

    testWidgets('turning SMS on needs confirmation; off does not', (
      tester,
    ) async {
      final repo = FakeMembers()
        ..members.add(fakeMember('1', 'Achieng Otieno'));
      await _pump(tester, repo, location: '/gyms/$_gymId/members/1');
      expect(
        find.text('No consent recorded. No SMS are sent.'),
        findsOneWidget,
      );

      await tester.tap(find.byKey(const Key('member-sms-switch')));
      await tester.pumpAndSettle();
      expect(find.text('Turn on SMS?'), findsOneWidget);
      await tester.tap(find.text('They agreed'));
      await tester.pumpAndSettle();
      expect(repo.smsChanges, [('1', true)]);
      expect(
        find.text('Code, receipts and expiry reminders by SMS.'),
        findsOneWidget,
      );

      await tester.tap(find.byKey(const Key('member-sms-switch')));
      await tester.pumpAndSettle();
      expect(find.text('Turn on SMS?'), findsNothing);
      expect(repo.smsChanges.last, ('1', false));
    });

    testWidgets('the code dialog says when the code was texted', (
      tester,
    ) async {
      final repo = FakeMembers()
        ..codeSms = 'sent'
        ..members.add(fakeMember('1', 'Achieng Otieno'));
      await _pump(tester, repo, location: '/gyms/$_gymId/members/1');

      await tester.tap(find.byKey(const Key('issue-check-in-code')));
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Also sent to the member by SMS.'),
        findsOneWidget,
      );
    });

    testWidgets('a failed receipt SMS is reported after a payment', (
      tester,
    ) async {
      final repo = FakeMembers()
        ..paymentSms = 'failed'
        ..members.add(fakeMember('1', 'Achieng Otieno'));
      await _pump(tester, repo, location: '/gyms/$_gymId/members/1');

      await tester.tap(find.byKey(const Key('record-cash-button')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('cash-payment-submit')));
      await tester.pump();

      expect(
        find.textContaining("The SMS receipt couldn't be sent."),
        findsOneWidget,
      );
    });
  });
}
