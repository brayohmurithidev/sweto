import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/network/api_exception.dart';
import 'package:sweto_app/core/network/dio_provider.dart';
import 'package:sweto_app/features/members/data/dio_members_repository.dart';
import 'package:sweto_app/features/members/domain/members_repository.dart';

final membersRepositoryProvider = Provider<MembersRepository>(
  (ref) => DioMembersRepository(ref.watch(dioProvider)),
);

/// A message safe to show: the API's own words, never a raw error.
String memberErrorMessage(Object error) {
  if (error is DioException) {
    final apiError = error.error;
    if (apiError is ApiException) return apiError.message;
  }
  return 'Something went wrong. Please try again.';
}
