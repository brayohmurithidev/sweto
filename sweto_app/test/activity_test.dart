import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/theme/app_theme.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/activity_screen.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/features/staff/domain/staff_entities.dart';
import 'package:sweto_app/features/staff/presentation/staff_providers.dart';
import 'package:sweto_app/features/staff/presentation/staff_screen.dart';

import 'members_screens_test.dart' show FakeMembers;
import 'support/fake_staff_repository.dart';

final _now = DateTime(2026, 11, 16, 18);

ActivityItem _item(String member, String kind, String? by, int minutesAgo) =>
    ActivityItem(
      kind: kind,
      at: _now.subtract(Duration(minutes: minutesAgo)),
      detail: kind == 'payment'
          ? 'Paid KES 5,000 (cash), Monthly'
          : 'Checked in',
      ok: true,
      memberId: 'm-$member',
      memberName: member,
      byUserId: by == null ? null : 'u-$by',
      byName: by == null ? null : '$by Kamau',
    );

Future<void> _pump(
  WidgetTester tester,
  Widget child, {
  FakeMembers? members,
  FakeStaffRepository? staff,
}) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, _) => child),
      GoRoute(
        path: '/gyms/:gymId/activity',
        name: 'activity',
        builder: (_, s) => Text('activity ${s.uri.queryParameters['by']}'),
      ),
      GoRoute(
        path: '/gyms/:gymId/members/:memberId',
        name: 'member-detail',
        builder: (_, s) => Text('member ${s.pathParameters['memberId']}'),
      ),
    ],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        membersRepositoryProvider.overrideWithValue(members ?? FakeMembers()),
        staffRepositoryProvider.overrideWithValue(
          staff ?? FakeStaffRepository(),
        ),
      ],
      child: MaterialApp.router(theme: AppTheme.dark(), routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('the log says who did each thing and pages', (tester) async {
    final members = FakeMembers()
      ..activity.addAll([
        for (var i = 0; i < 35; i++)
          _item('Member $i', i.isEven ? 'payment' : 'check_in', 'Wanjiku', i),
      ]);
    await _pump(
      tester,
      ActivityScreen(gymId: 'gym-1', now: () => _now),
      members: members,
    );

    expect(find.text('Activity'), findsOneWidget);
    expect(
      find.text('Paid KES 5,000 (cash), Monthly\nby Wanjiku'),
      findsWidgets,
    );
    expect(find.text('just now'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.byKey(const Key('activity-load-more')),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.ensureVisible(find.byKey(const Key('activity-load-more')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('activity-load-more')));
    await tester.pumpAndSettle();
    expect(members.activityCalls, [(null, 0), (null, 30)]);
    expect(find.byKey(const Key('activity-load-more')), findsNothing);
  });

  testWidgets('one person\'s log asks only for theirs', (tester) async {
    final members = FakeMembers()
      ..activity.addAll([
        _item('Achieng', 'payment', 'Wanjiku', 5),
        _item('Otieno', 'payment', 'Brian', 6),
      ]);
    await _pump(
      tester,
      ActivityScreen(
        gymId: 'gym-1',
        byUserId: 'u-Wanjiku',
        byName: 'Wanjiku Kamau',
        now: () => _now,
      ),
      members: members,
    );

    expect(find.text("Wanjiku's activity"), findsOneWidget);
    expect(find.text('Achieng'), findsOneWidget);
    expect(find.text('Otieno'), findsNothing);
    // Their own list doesn't repeat their name on every row.
    expect(find.textContaining('by Wanjiku'), findsNothing);
    expect(members.activityCalls, [('u-Wanjiku', 0)]);
  });

  testWidgets('the staff list shows each person\'s day and opens their log', (
    tester,
  ) async {
    final staff = FakeStaffRepository(
      staff: [
        const StaffMember(
          id: 'owner-row',
          userId: 'u-owner',
          fullName: 'Brian Owner',
          role: StaffRole.owner,
          status: 'active',
          isPrimaryOwner: true,
          hasSignedIn: true,
          today: StaffDay(payments: 0, cash: 0, mpesa: 0, checkIns: 0),
        ),
        const StaffMember(
          id: 'desk-row',
          userId: 'u-Wanjiku',
          fullName: 'Wanjiku Kamau',
          role: StaffRole.receptionist,
          status: 'active',
          isPrimaryOwner: false,
          hasSignedIn: true,
          today: StaffDay(payments: 3, cash: 15000, mpesa: 0, checkIns: 12),
        ),
      ],
    );
    await _pump(tester, const StaffScreen(gymId: 'gym-1'), staff: staff);

    expect(
      find.text('Today: 3 payments · KES 15,000 cash · 12 check-ins'),
      findsOneWidget,
    );
    // An owner who did nothing today shows no line.
    expect(find.byKey(const Key('staff-today-owner-row')), findsNothing);

    await tester.tap(find.byKey(const Key('staff-desk-row')));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('staff-activity')));
    await tester.tap(find.byKey(const Key('staff-activity')));
    await tester.pumpAndSettle();
    expect(find.text('activity u-Wanjiku'), findsOneWidget);
  });
}
