import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/network/dio_provider.dart';
import 'package:sweto_app/core/storage/storage_providers.dart';
import 'package:sweto_app/features/auth/data/repositories/dio_auth_repository.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/repositories/auth_repository.dart';

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => DioAuthRepository(
    ref.watch(dioProvider),
    ref.watch(tokenStorageProvider),
  ),
);
final authBootstrapProvider = FutureProvider<AccountOnboarding?>((ref) async {
  final repo = ref.watch(authRepositoryProvider);
  final refresh = await repo.readRefreshToken();
  if (refresh == null || refresh.isEmpty) return null;
  try {
    await repo.saveTokens(await repo.refresh(refresh));
    await repo.getMe();
    return repo.getOnboarding();
  } catch (_) {
    await repo.clearTokens();
    return null;
  }
});
