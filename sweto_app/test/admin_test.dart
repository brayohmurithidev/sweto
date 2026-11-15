import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/network/api_exception.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/features/admin/domain/admin_entities.dart';
import 'package:sweto_app/features/admin/domain/admin_repository.dart';
import 'package:sweto_app/features/admin/presentation/admin_gym_review_screen.dart';
import 'package:sweto_app/features/admin/presentation/admin_home_screen.dart';
import 'package:sweto_app/features/admin/presentation/admin_providers.dart';
import 'package:sweto_app/features/admin/presentation/admin_sign_in_screen.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_repository.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';

import 'support/fake_auth_repository.dart';

const _first = AuthTokens(accessToken: 'first-access', refreshToken: 'first-r');
const _fresh = AuthTokens(accessToken: 'fresh-access', refreshToken: 'fresh-r');

class _FakeAdmin implements AdminRepository {
  bool mustChange = false;
  final signIns = <(String, String)>[];
  final changes = <(String, String, String)>[];
  final decisions = <String>[];
  final listCalls = <VerificationStatus>[];
  Object? signInError;

  final queue = <VerificationStatus, List<VerificationSummary>>{
    VerificationStatus.pending: [
      VerificationSummary(
        gymId: 'gym-1',
        gymName: 'Smart Gyms',
        status: VerificationStatus.pending,
        submittedAt: DateTime(2026, 11, 15, 16, 39),
        missingDocuments: const [],
      ),
    ],
  };

  @override
  Future<AdminSignIn> signIn({
    required String email,
    required String password,
  }) async {
    if (signInError != null) throw signInError!;
    signIns.add((email, password));
    final first = signIns.length == 1;
    return AdminSignIn(
      tokens: first ? _first : _fresh,
      mustChangePassword: first && mustChange,
    );
  }

  @override
  Future<void> changePassword({
    required String accessToken,
    required String currentPassword,
    required String newPassword,
  }) async => changes.add((accessToken, currentPassword, newPassword));

  @override
  Future<VerificationQueuePage> listVerifications(
    VerificationStatus status, {
    int limit = 50,
    int offset = 0,
  }) async {
    listCalls.add(status);
    final gyms = queue[status] ?? const [];
    return VerificationQueuePage(gyms: gyms, total: gyms.length);
  }

  @override
  Future<VerificationDetail> getVerification(String gymId) async =>
      VerificationDetail(
        gymId: gymId,
        status: VerificationStatus.pending,
        submittedAt: DateTime(2026, 11, 15, 16, 39),
        requiredDocuments: const ['business_registration', 'tax_certificate'],
        missingDocuments: const ['tax_certificate'],
        documents: [
          VerificationDocument(
            type: 'business_registration',
            name: 'certificate.pdf',
            mimeType: 'application/pdf',
            sizeBytes: 1000,
            uploadedAt: DateTime(2026, 11, 15, 16, 30),
          ),
        ],
        history: const [],
        gym: const ReviewedGym(
          name: 'Smart Gyms',
          legalBusinessName: 'Smart Gyms Limited',
          registrationNumber: 'PVT-123',
          contactPersonName: 'Brian Munene',
          addressLine: 'Kenyatta Avenue',
          city: 'Nairobi',
        ),
      );

  @override
  Future<Uri> documentDownloadUrl(String gymId, String documentType) async =>
      Uri.parse('https://files.example/$gymId/$documentType?signed=1');

  @override
  Future<VerificationDetail> approve(String gymId, {String? notes}) async {
    decisions.add('approve $gymId');
    return getVerification(gymId);
  }

  @override
  Future<VerificationDetail> reject(
    String gymId, {
    required String reason,
  }) async {
    decisions.add('reject $gymId: $reason');
    return getVerification(gymId);
  }
}

Future<(_FakeAdmin, FakeAuthRepository, List<Uri>)> _pump(
  WidgetTester tester, {
  required String location,
  _FakeAdmin? admin,
}) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final repo = admin ?? _FakeAdmin();
  final auth = FakeAuthRepository();
  final opened = <Uri>[];
  final router = GoRouter(
    initialLocation: location,
    routes: [
      GoRoute(
        path: AppRoutes.splashPath,
        name: AppRoutes.splashName,
        builder: (_, _) => const Text('splash'),
      ),
      GoRoute(
        path: AppRoutes.adminSignInPath,
        name: AppRoutes.adminSignInName,
        builder: (_, _) => const AdminSignInScreen(),
      ),
      GoRoute(
        path: AppRoutes.adminHomePath,
        name: AppRoutes.adminHomeName,
        builder: (_, _) => const AdminHomeScreen(),
      ),
      GoRoute(
        path: AppRoutes.adminGymReviewPath,
        name: AppRoutes.adminGymReviewName,
        builder: (_, s) =>
            AdminGymReviewScreen(gymId: s.pathParameters['gymId']!),
      ),
    ],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        adminRepositoryProvider.overrideWithValue(repo),
        authRepositoryProvider.overrideWithValue(auth),
        linkOpenerProvider.overrideWithValue((uri) async {
          opened.add(uri);
          return true;
        }),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
  return (repo, auth, opened);
}

Future<void> _signInWith(WidgetTester tester, String password) async {
  await tester.enterText(
    find.byKey(const Key('admin-email')),
    'murithibrianm@gmail.com',
  );
  await tester.enterText(find.byKey(const Key('admin-password')), password);
  await tester.tap(find.byKey(const Key('admin-sign-in-submit')));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('staff sign in and go to the start screen', (tester) async {
    final (admin, auth, _) = await _pump(
      tester,
      location: AppRoutes.adminSignInPath,
    );

    await _signInWith(tester, 'a-good-password');

    expect(admin.signIns, [('murithibrianm@gmail.com', 'a-good-password')]);
    expect(auth.accessToken, 'first-access');
    expect(find.text('splash'), findsOneWidget);
  });

  testWidgets('a generated password is replaced before anything is stored', (
    tester,
  ) async {
    final admin = _FakeAdmin()..mustChange = true;
    final (_, auth, _) = await _pump(
      tester,
      location: AppRoutes.adminSignInPath,
      admin: admin,
    );

    await _signInWith(tester, 'generated-pass');
    expect(find.text('Set a new password'), findsOneWidget);
    expect(auth.accessToken, isNull);

    Future<void> submit(String next, String again) async {
      await tester.enterText(find.byKey(const Key('admin-new-password')), next);
      await tester.enterText(
        find.byKey(const Key('admin-confirm-password')),
        again,
      );
      await tester.tap(find.byKey(const Key('admin-sign-in-submit')));
      await tester.pumpAndSettle();
    }

    await submit('short', 'short');
    expect(find.textContaining('at least 12 characters'), findsOneWidget);
    await submit('a-long-new-password', 'something-else-entirely');
    expect(find.text('The two new passwords don\'t match.'), findsOneWidget);
    expect(admin.changes, isEmpty);

    await submit('a-long-new-password', 'a-long-new-password');
    // Authorised by the first sign-in's token, then a fresh sign-in.
    expect(admin.changes, [
      ('first-access', 'generated-pass', 'a-long-new-password'),
    ]);
    expect(admin.signIns.last.$2, 'a-long-new-password');
    expect(auth.accessToken, 'fresh-access');
    expect(find.text('splash'), findsOneWidget);
  });

  testWidgets('a wrong password shows the server\'s reason', (tester) async {
    final admin = _FakeAdmin()
      ..signInError = DioException(
        requestOptions: RequestOptions(),
        error: const ApiException(
          message: 'Invalid email or password.',
          statusCode: 401,
        ),
      );
    await _pump(tester, location: AppRoutes.adminSignInPath, admin: admin);

    await _signInWith(tester, 'nope');

    expect(find.text('Invalid email or password.'), findsOneWidget);
    expect(find.text('splash'), findsNothing);
  });

  testWidgets('the queue opens a gym with its details and documents', (
    tester,
  ) async {
    final (admin, _, opened) = await _pump(
      tester,
      location: AppRoutes.adminHomePath,
    );

    expect(admin.listCalls, [VerificationStatus.pending]);
    expect(find.text('Smart Gyms'), findsOneWidget);
    await tester.tap(find.text('Smart Gyms'));
    await tester.pumpAndSettle();

    expect(find.text('Waiting for review'), findsOneWidget);
    expect(find.text('Smart Gyms Limited'), findsOneWidget);
    expect(find.text('PVT-123'), findsOneWidget);
    expect(find.text('Kenyatta Avenue, Nairobi'), findsOneWidget);
    expect(find.text('KRA PIN Certificate'), findsOneWidget);
    expect(find.text('Missing'), findsOneWidget);

    await tester.tap(
      find.byKey(const Key('admin-document-business_registration')),
    );
    await tester.pumpAndSettle();
    expect(opened.single.toString(), contains('gym-1/business_registration'));
  });

  testWidgets('approving asks first, then returns to a refreshed queue', (
    tester,
  ) async {
    final (admin, _, _) = await _pump(
      tester,
      location: AppRoutes.adminHomePath,
    );
    await tester.tap(find.text('Smart Gyms'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('admin-approve')));
    await tester.pumpAndSettle();
    expect(find.text('Approve Smart Gyms?'), findsOneWidget);
    await tester.tap(find.text('Approve').last);
    await tester.pumpAndSettle();

    expect(admin.decisions, ['approve gym-1']);
    expect(find.byType(AdminHomeScreen), findsOneWidget);
    expect(admin.listCalls.length, 2);
  });

  testWidgets('rejecting needs a reason the owner can act on', (tester) async {
    final (admin, _, _) = await _pump(
      tester,
      location: AppRoutes.adminHomePath,
    );
    await tester.tap(find.text('Smart Gyms'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('admin-reject')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('admin-reject-confirm')));
    await tester.pumpAndSettle();
    expect(find.text('Tell the owner what to fix.'), findsOneWidget);
    expect(admin.decisions, isEmpty);

    await tester.enterText(
      find.byKey(const Key('admin-reject-reason')),
      'The KRA PIN certificate is missing.',
    );
    await tester.tap(find.byKey(const Key('admin-reject-confirm')));
    await tester.pumpAndSettle();
    expect(admin.decisions, [
      'reject gym-1: The KRA PIN certificate is missing.',
    ]);
  });

  testWidgets('other tabs list decided gyms or say nothing is there', (
    tester,
  ) async {
    final (admin, _, _) = await _pump(
      tester,
      location: AppRoutes.adminHomePath,
    );
    await tester.tap(find.text('Approved'));
    await tester.pumpAndSettle();
    expect(admin.listCalls.last, VerificationStatus.approved);
    expect(find.text('Nothing here yet.'), findsOneWidget);
  });

  test('staff go to the review queue when the app starts', () async {
    final coordinator = OnboardingCoordinator(_ReviewerAuth(), _NoGyms());
    expect(await coordinator.resolve(), OnboardingDestination.admin);
  });
}

class _ReviewerAuth extends FakeAuthRepository {
  @override
  Future<AuthUser> getMe() async => const AuthUser(
    id: 'admin',
    mustChangePassword: false,
    role: 'super_admin',
  );
}

class _NoGyms extends Fake implements GymOwnerRepository {}
