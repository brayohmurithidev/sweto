import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/network/dio_provider.dart';
import 'package:sweto_app/features/auth/domain/entities/auth_entities.dart';
import 'package:sweto_app/features/auth/domain/repositories/auth_repository.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/gym_owner/data/dio_gym_owner_repository.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_repository.dart';

enum OnboardingDestination {
  accountType,
  gymRegistration,
  location,
  businessDetails,
  amenities,
  operatingHours,
  pricing,
  verification,
  verificationPending,
  home,
  memberComingSoon,
  unsupported,
}

final gymOwnerRepositoryProvider = Provider<GymOwnerRepository>(
  (ref) => DioGymOwnerRepository(ref.watch(dioProvider)),
);

final onboardingCoordinatorProvider = Provider<OnboardingCoordinator>(
  (ref) => OnboardingCoordinator(
    ref.watch(authRepositoryProvider),
    ref.watch(gymOwnerRepositoryProvider),
  ),
);

class OnboardingCoordinator {
  const OnboardingCoordinator(this._auth, this._gyms);

  final AuthRepository _auth;
  final GymOwnerRepository _gyms;

  Future<OnboardingDestination> resolve() async {
    final account = await _auth.getOnboarding();
    final destination = await resolveAccount(account);
    _logAccount(account, destination);
    return destination;
  }

  Future<OnboardingDestination> resolveAccount(
    AccountOnboarding account,
  ) async {
    switch (account.nextStep) {
      case 'choose_account':
        return OnboardingDestination.accountType;
      case 'gym_setup':
        return _resolveGym();
      case 'verification_pending':
        return OnboardingDestination.home;
      case 'dashboard':
        return OnboardingDestination.home;
      case 'member_profile_setup':
        return OnboardingDestination.memberComingSoon;
      default:
        return OnboardingDestination.unsupported;
    }
  }

  Future<OnboardingDestination> _resolveGym() async {
    try {
      final gym = await _gyms.getCurrentGym();
      final state = await _gyms.getGymOnboarding(gym.id);
      final destination = _destinationForGym(state);
      _logGym(state, destination);
      return destination;
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return OnboardingDestination.gymRegistration;
      }
      rethrow;
    }
  }

  Future<OnboardingDestination> selectGymOwner() async {
    final account = await _auth.selectGymOwnerRole();
    final destination = await resolveAccount(account);
    _logAccount(account, destination);
    return destination;
  }

  Future<OnboardingDestination> createdGym(Gym gym) async {
    final state = await _gyms.getGymOnboarding(gym.id);
    final destination = _destinationForGym(state);
    _logGym(state, destination);
    return destination;
  }

  OnboardingDestination _destinationForGym(GymOnboarding state) {
    if (state.verificationStatus == GymVerificationStatus.pending ||
        state.nextStep == GymOnboardingStep.waitingForVerification) {
      return OnboardingDestination.home;
    }

    return switch (state.nextStep) {
      GymOnboardingStep.basicInformation =>
        OnboardingDestination.gymRegistration,
      GymOnboardingStep.location => OnboardingDestination.location,
      GymOnboardingStep.verification => OnboardingDestination.verification,
      GymOnboardingStep.businessDetails =>
        OnboardingDestination.businessDetails,
      GymOnboardingStep.amenities => OnboardingDestination.amenities,
      GymOnboardingStep.pricing => OnboardingDestination.pricing,
      GymOnboardingStep.operatingHours => OnboardingDestination.operatingHours,
      GymOnboardingStep.completed => OnboardingDestination.home,
      GymOnboardingStep.unknown => OnboardingDestination.unsupported,
      _ => OnboardingDestination.unsupported,
    };
  }

  void _logAccount(
    AccountOnboarding account,
    OnboardingDestination destination,
  ) {
    if (!kDebugMode) return;
    debugPrint('''
--------------------------------
ONBOARDING RESPONSE

roles: ${account.roles}
default_role: ${account.defaultRole}
onboarding_status: ${account.status}
onboarding_completed: ${account.completed}
next_step: ${account.nextStep}

gym_id: -

resolved_route: $destination
--------------------------------''');
  }

  void _logGym(GymOnboarding state, OnboardingDestination destination) {
    if (!kDebugMode) return;
    debugPrint('''
--------------------------------
ONBOARDING RESPONSE

roles: gym_owner
default_role: gym_owner
onboarding_status: gym_setup_pending
onboarding_completed: ${state.completed}
next_step: ${state.nextStep}

gym_id: ${state.gymId}

resolved_route: $destination
--------------------------------''');
  }
}
