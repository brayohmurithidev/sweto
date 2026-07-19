import 'package:shared_preferences/shared_preferences.dart';

class OnboardingStorage {
  static const _key = 'onboarding_completed';
  Future<bool> isCompleted() async =>
      (await SharedPreferences.getInstance()).getBool(_key) ?? false;
  Future<void> markCompleted() async =>
      (await SharedPreferences.getInstance()).setBool(_key, true);
}
