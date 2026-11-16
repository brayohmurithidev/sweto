import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/network/dio_provider.dart';
import 'package:sweto_app/features/staff/data/dio_staff_repository.dart';
import 'package:sweto_app/features/staff/domain/staff_entities.dart';
import 'package:sweto_app/features/staff/domain/staff_repository.dart';

final staffRepositoryProvider = Provider<StaffRepository>(
  (ref) => DioStaffRepository(ref.watch(dioProvider)),
);

/// The signed-in person's role at their gym. The gym's home screen sets it
/// once loaded; tabs and buttons read it. The API enforces the same rules.
final gymAccessProvider = NotifierProvider<GymAccessNotifier, GymAccess>(
  GymAccessNotifier.new,
);

class GymAccessNotifier extends Notifier<GymAccess> {
  @override
  GymAccess build() => GymAccess.owner;

  void set(GymAccess access) => state = access;
}
