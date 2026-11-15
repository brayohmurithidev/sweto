import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:sweto_app/core/maps/maps_availability.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_repository.dart';
import 'package:sweto_app/features/gym_owner/presentation/gym_owner_screens.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';

const _channel = MethodChannel('sweto/maps');

class _Gyms extends Fake implements GymOwnerRepository {
  @override
  Future<Gym> getCurrentGym() async => const Gym(
    id: 'gym-1',
    name: 'RDF Fitness Center',
    location: GymLocation(
      latitude: -1.2676,
      longitude: 36.8108,
      addressLine: 'ABC Place, Waiyaki Way',
      neighbourhood: 'Westlands',
      city: 'Nairobi',
      countryCode: 'KE',
    ),
  );
}

void _answer(Object? Function(MethodCall call)? handler) {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(
        _channel,
        handler == null ? null : (call) async => handler(call),
      );
}

Future<bool> _available() async {
  final container = ProviderContainer();
  addTearDown(container.dispose);
  return container.read(mapsAvailableProvider.future);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  tearDown(() => _answer(null));

  test('a map is shown only when the native side says it has a key', () async {
    _answer((call) => call.method == 'isConfigured');
    expect(await _available(), isTrue);

    _answer((_) => false);
    expect(await _available(), isFalse);
  });

  test('no native answer or an error means no map, never a crash', () async {
    _answer(null);
    expect(await _available(), isFalse);

    _answer((_) => throw PlatformException(code: 'boom'));
    expect(await _available(), isFalse);
  });

  testWidgets('without a key the Location step works with no map', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1170, 2532);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          gymOwnerRepositoryProvider.overrideWithValue(_Gyms()),
          mapsAvailableProvider.overrideWith((ref) async => false),
        ],
        child: const MaterialApp(home: GymLocationScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(GoogleMap), findsNothing);
    expect(find.byKey(const Key('location-map-unavailable')), findsOneWidget);
    expect(find.text('Drag the map to position your gym'), findsNothing);
    expect(find.text('Use my current location'), findsOneWidget);
    expect(find.text('ABC Place, Waiyaki Way'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
