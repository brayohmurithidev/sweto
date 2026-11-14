import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/network/dio_provider.dart';
import 'package:sweto_app/core/storage/storage_providers.dart';
import 'package:sweto_app/features/auth/data/repositories/dio_auth_repository.dart';
import 'package:sweto_app/features/auth/data/repositories/dio_otp_delivery_repository.dart';
import 'package:sweto_app/features/auth/domain/repositories/auth_repository.dart';
import 'package:sweto_app/features/auth/domain/repositories/otp_delivery_repository.dart';

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => DioAuthRepository(
    ref.watch(dioProvider),
    ref.watch(tokenStorageProvider),
  ),
);

final otpDeliveryRepositoryProvider = Provider<OtpDeliveryRepository>(
  (ref) => DioOtpDeliveryRepository(ref.watch(dioProvider)),
);
