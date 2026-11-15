import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/finance_tab.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/owner_shell.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/features/members/presentation/members_screen.dart';

import 'members_screens_test.dart' show FakeMembers;

final _now = DateTime(2026, 11, 14, 14, 0);

DashboardSummary _summary({
  double? change = 333.3,
  List<ActivityItem>? activity,
}) => DashboardSummary(
  gymName: 'RDF Fitness Center',
  ownerFirstName: 'Brian',
  activeMembers: 248,
  expiringMembers: 12,
  checkInsToday: 46,
  revenueThisMonth: 254800,
  currency: 'KES',
  revenueChangePercent: change,
  dailyRevenue: const [0, 1500, 0, 5000, 2000],
  recentActivity:
      activity ??
      [
        ActivityItem(
          kind: 'check_in',
          at: _now.subtract(const Duration(minutes: 10)),
          detail: 'Checked in',
          ok: true,
          memberId: 'm1',
          memberName: 'James Mwangi',
        ),
        ActivityItem(
          kind: 'payment',
          at: _now.subtract(const Duration(hours: 2)),
          detail: 'Paid KES 5,000 (M-Pesa), Monthly',
          ok: true,
          memberId: 'm2',
          memberName: 'Grace Wanjiku',
        ),
      ],
);

Future<List<String>> _pump(WidgetTester tester, FakeMembers repo) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final logouts = <String>[];
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, _) => OwnerShell(
          gymId: 'gym-1',
          gymName: 'RDF Fitness Center',
          onLogout: () => logouts.add('logout'),
          now: () => _now,
        ),
      ),
      GoRoute(
        path: AppRoutes.memberDetailPath,
        name: AppRoutes.memberDetailName,
        builder: (_, s) => Text('member ${s.pathParameters['memberId']}'),
      ),
      GoRoute(
        path: AppRoutes.checkInPath,
        name: AppRoutes.checkInName,
        builder: (_, _) => const Text('check-in screen'),
      ),
      GoRoute(
        path: AppRoutes.addMemberPath,
        name: AppRoutes.addMemberName,
        builder: (_, _) => const Text('add member screen'),
      ),
    ],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [membersRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
  return logouts;
}

void main() {
  testWidgets('Home shows today\'s numbers, revenue and activity', (
    tester,
  ) async {
    final repo = FakeMembers()..dashboard = _summary();
    await _pump(tester, repo);

    expect(find.text('Good afternoon, Brian 👋'), findsOneWidget);
    expect(find.text('RDF Fitness Center'), findsOneWidget);
    expect(find.text('248'), findsOneWidget);
    expect(find.text('12'), findsOneWidget);
    expect(find.text('46'), findsOneWidget);
    expect(find.text('KES 254,800'), findsOneWidget);
    expect(find.text('↑ 333.3% vs last month'), findsOneWidget);
    expect(find.text('James Mwangi'), findsOneWidget);
    expect(find.text('10 min ago'), findsOneWidget);
    expect(find.text('2 h ago'), findsOneWidget);
    expect(tester.takeException(), isNull);

    await tester.tap(find.text('James Mwangi'));
    await tester.pumpAndSettle();
    expect(find.text('member m1'), findsOneWidget);
  });

  testWidgets('a first month and a quiet gym read sensibly', (tester) async {
    final repo = FakeMembers()
      ..dashboard = _summary(change: null, activity: const []);
    await _pump(tester, repo);

    expect(find.text('Nothing last month to compare with'), findsOneWidget);
    expect(find.textContaining('Nothing yet.'), findsOneWidget);
  });

  testWidgets('a falling month shows the drop', (tester) async {
    final repo = FakeMembers()..dashboard = _summary(change: -8.25);
    await _pump(tester, repo);

    expect(find.text('↓ 8.3% vs last month'), findsOneWidget);
  });

  testWidgets('quick actions open check-in and add member', (tester) async {
    final repo = FakeMembers()..dashboard = _summary();
    await _pump(tester, repo);

    await tester.tap(find.byKey(const Key('home-scan')));
    await tester.pumpAndSettle();
    expect(find.text('check-in screen'), findsOneWidget);
  });

  testWidgets('tabs switch between Home, Members, Finance and More', (
    tester,
  ) async {
    final repo = FakeMembers()
      ..dashboard = _summary()
      ..finance['2026-11'] = FinanceSummary(
        currency: 'KES',
        month: DateTime(2026, 11),
        through: DateTime(2026, 11, 14),
        isCurrentMonth: true,
        total: 1500,
        paymentsCount: 1,
        previousMonthTotal: 0,
        cashAmount: 1500,
        cashCount: 1,
        mpesaAmount: 0,
        mpesaCount: 0,
        byPlan: const [],
        trend: const [],
      );
    final logouts = await _pump(tester, repo);
    final loadsAtStart = repo.dashboardLoads;

    await tester.tap(find.text('Members').last);
    await tester.pumpAndSettle();
    expect(find.byType(MembersScreen), findsOneWidget);
    expect(find.byKey(const Key('add-member-button')), findsOneWidget);

    await tester.tap(find.text('Finance'));
    await tester.pumpAndSettle();
    expect(find.byType(FinanceTab), findsOneWidget);
    expect(find.text('KES 1,500'), findsWidgets);

    await tester.tap(find.text('More'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('more-logout')));
    expect(logouts, ['logout']);

    // Coming back to Home refreshes the numbers.
    await tester.tap(find.text('Home'));
    await tester.pumpAndSettle();
    expect(repo.dashboardLoads, greaterThan(loadsAtStart));
  });

  testWidgets('a failed load can be retried', (tester) async {
    final repo = FakeMembers()
      ..dashboardError = DioException(requestOptions: RequestOptions());
    await _pump(tester, repo);
    expect(find.byKey(const Key('home-error')), findsOneWidget);

    repo
      ..dashboardError = null
      ..dashboard = _summary();
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.text('KES 254,800'), findsOneWidget);
  });
}
