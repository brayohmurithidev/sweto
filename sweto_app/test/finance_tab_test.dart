import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/finance_tab.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/export_share.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';

import 'members_screens_test.dart' show FakeMembers;

List<MonthRevenue> _trend(DateTime last, List<double> amounts) => [
  for (var i = 0; i < amounts.length; i++)
    MonthRevenue(
      month: DateTime(last.year, last.month - amounts.length + 1 + i),
      amount: amounts[i],
    ),
];

final _november = FinanceSummary(
  currency: 'KES',
  month: DateTime(2026, 11),
  through: DateTime(2026, 11, 14),
  isCurrentMonth: true,
  total: 254800,
  paymentsCount: 61,
  previousMonthTotal: 230000,
  changePercent: 10.8,
  cashAmount: 54800,
  cashCount: 21,
  mpesaAmount: 200000,
  mpesaCount: 40,
  byPlan: const [
    PlanRevenue(planName: 'Monthly', amount: 200000, count: 40),
    PlanRevenue(planName: 'Weekly', amount: 54800, count: 21),
  ],
  trend: _trend(DateTime(2026, 11), [0, 0, 120000, 180000, 230000, 254800]),
  failedMpesaCount: 2,
  pendingMpesaCount: 1,
);

final _october = FinanceSummary(
  currency: 'KES',
  month: DateTime(2026, 10),
  through: DateTime(2026, 10, 31),
  isCurrentMonth: false,
  total: 230000,
  paymentsCount: 50,
  previousMonthTotal: 0,
  cashAmount: 30000,
  cashCount: 10,
  mpesaAmount: 200000,
  mpesaCount: 40,
  byPlan: const [PlanRevenue(planName: 'Monthly', amount: 230000, count: 50)],
  trend: _trend(DateTime(2026, 10), [0, 0, 0, 120000, 180000, 230000]),
);

FinanceTransaction _payment(
  String id,
  String name, {
  bool mpesa = true,
  PaymentState state = PaymentState.completed,
  int month = 11,
}) => FinanceTransaction(
  paymentId: id,
  memberId: 'member-$id',
  memberName: name,
  planName: 'Monthly',
  amount: 5000,
  currency: 'KES',
  isMpesa: mpesa,
  state: state,
  at: DateTime(2026, month, 14, 9, 5),
  receipt: mpesa && state == PaymentState.completed ? 'TKE1ABC2DE' : null,
);

FakeMembers _repo() => FakeMembers()
  ..finance['2026-10'] = _october
  ..finance['2026-11'] = _november
  ..financePayments.addAll([
    _payment('p1', 'Grace Wanjiku'),
    _payment('p2', 'James Mwangi', mpesa: false),
    _payment('p3', 'Cancelled Prompt', state: PaymentState.failed),
    _payment('p4', 'October Member', month: 10),
  ]);

Future<void> _pump(WidgetTester tester, FakeMembers repo) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, _) => const Scaffold(body: FinanceTab(gymId: 'gym-1')),
      ),
      GoRoute(
        path: AppRoutes.memberDetailPath,
        name: AppRoutes.memberDetailName,
        builder: (_, s) => Text('member ${s.pathParameters['memberId']}'),
      ),
    ],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        membersRepositoryProvider.overrideWithValue(repo),
        exportSharerProvider.overrideWithValue(
          (file, {origin}) async => repo.sharedExports.add(file.fileName),
        ),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _scrollTo(WidgetTester tester, Finder finder) =>
    tester.scrollUntilVisible(
      finder,
      200,
      scrollable: find.descendant(
        of: find.byKey(const Key('finance-list')),
        matching: find.byType(Scrollable),
      ),
    );

void main() {
  testWidgets('this month: total, split, trend, plans and payments', (
    tester,
  ) async {
    await _pump(tester, _repo());

    expect(find.text('November 2026'), findsOneWidget);
    expect(find.text('Revenue, 1–14 Nov'), findsOneWidget);
    expect(find.text('KES 254,800'), findsOneWidget);
    expect(find.text('61 payments'), findsOneWidget);
    expect(find.text('↑ 10.8% vs the same days last month'), findsOneWidget);
    expect(find.text('KES 200,000'), findsWidgets);
    expect(find.text('KES 54,800'), findsWidgets);
    expect(
      find.text(
        '2 M-Pesa prompts failed or cancelled, 1 still waiting. '
        'Not counted in revenue.',
      ),
      findsOneWidget,
    );
    expect(find.text('255k'), findsOneWidget);
    // This month can't go forward.
    final next = tester.widget<IconButton>(
      find.byKey(const Key('finance-next-month')),
    );
    expect(next.onPressed, isNull);

    await _scrollTo(tester, find.text('Grace Wanjiku'));
    expect(
      find.text('14 Nov, 09:05 · Monthly · M-Pesa · TKE1ABC2DE'),
      findsOneWidget,
    );
    await _scrollTo(tester, find.text('Cancelled Prompt'));
    expect(find.text('Failed'), findsOneWidget);
    expect(find.text('October Member'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('filters and opening a member', (tester) async {
    final repo = _repo();
    await _pump(tester, repo);

    await _scrollTo(tester, find.byKey(const Key('finance-filter-Cash')));
    await tester.tap(find.byKey(const Key('finance-filter-Cash')));
    await tester.pumpAndSettle();
    expect(repo.financeCalls.last.$2, isFalse);
    await _scrollTo(tester, find.text('James Mwangi'));
    expect(find.text('Grace Wanjiku'), findsNothing);

    await tester.tap(find.text('James Mwangi'));
    await tester.pumpAndSettle();
    expect(find.text('member member-p2'), findsOneWidget);
  });

  testWidgets('going back a month, by arrow or by bar', (tester) async {
    final repo = _repo();
    await _pump(tester, repo);

    await tester.tap(find.byKey(const Key('finance-previous-month')));
    await tester.pumpAndSettle();
    expect(find.text('October 2026'), findsOneWidget);
    expect(find.text('Revenue, October 2026'), findsOneWidget);
    expect(
      find.text('Nothing in the month before to compare with'),
      findsOneWidget,
    );
    expect(find.byKey(const Key('finance-mpesa-notice')), findsNothing);
    expect(repo.financeCalls.last.$1, DateTime(2026, 10));

    await tester.tap(find.byKey(const Key('finance-next-month')));
    await tester.pumpAndSettle();
    expect(find.text('November 2026'), findsOneWidget);

    await tester.tap(find.byKey(const Key('finance-trend-2026-10')));
    await tester.pumpAndSettle();
    expect(find.text('October 2026'), findsOneWidget);
  });

  testWidgets('many payments load in pages', (tester) async {
    final repo = FakeMembers()..finance['2026-11'] = _november;
    for (var i = 0; i < 35; i++) {
      repo.financePayments.add(_payment('x$i', 'Member $i'));
    }
    await _pump(tester, repo);

    await _scrollTo(tester, find.byKey(const Key('finance-load-more')));
    expect(find.text('Show more (5)'), findsOneWidget);
    await tester.tap(find.byKey(const Key('finance-load-more')));
    await tester.pumpAndSettle();
    expect(repo.financeCalls.last.$3, 30);
    await _scrollTo(tester, find.text('Member 34'));
    expect(find.byKey(const Key('finance-load-more')), findsNothing);
  });

  testWidgets('a failed load can be retried', (tester) async {
    final repo = _repo()
      ..financeError = DioException(requestOptions: RequestOptions());
    await _pump(tester, repo);
    expect(find.byKey(const Key('finance-error')), findsOneWidget);

    repo.financeError = null;
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.text('KES 254,800'), findsOneWidget);
  });

  testWidgets('exports the month on screen as a CSV', (tester) async {
    final repo = _repo();
    await _pump(tester, repo);

    await tester.tap(find.byKey(const Key('finance-export')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('finance-previous-month')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('finance-export')));
    await tester.pumpAndSettle();

    expect(repo.exports, ['payments this', 'payments 10']);
    expect(repo.sharedExports, hasLength(2));
  });
}
