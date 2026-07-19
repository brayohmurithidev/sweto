import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/network/dio_provider.dart';
import 'package:sweto_app/features/health/data/health_repository.dart';
import 'package:sweto_app/features/health/domain/health_status.dart';

final healthRepositoryProvider = Provider<HealthRepository>((ref) {
  return HealthRepository(ref.watch(dioProvider));
});

final healthCheckProvider = FutureProvider<HealthStatus>((ref) {
  return ref.watch(healthRepositoryProvider).checkHealth();
});
