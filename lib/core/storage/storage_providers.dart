import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sweto_app/core/storage/secure_token_storage.dart';
import 'package:sweto_app/core/storage/token_storage.dart';

final flutterSecureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage();
});

final tokenStorageProvider = Provider<TokenStorage>((ref) {
  final secureStorage = ref.watch(flutterSecureStorageProvider);

  return SecureTokenStorage(secureStorage);
});
