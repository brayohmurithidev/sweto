import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';

class AppTextStyles {
  AppTextStyles._();

  static const String fontFamily = 'PlusJakartaSans';

  static const displayLarge = TextStyle(
    fontFamily: fontFamily,
    fontSize: 36,
    height: 1.1,
    fontWeight: FontWeight.w800,
    color: AppColors.textPrimary,
  );

  static const displayMedium = TextStyle(
    fontFamily: fontFamily,
    fontSize: 30,
    height: 1.15,
    fontWeight: FontWeight.w800,
    color: AppColors.textPrimary,
  );

  static const headingLarge = TextStyle(
    fontFamily: fontFamily,
    fontSize: 26,
    height: 1.2,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
  );

  static const headingMedium = TextStyle(
    fontFamily: fontFamily,
    fontSize: 22,
    height: 1.25,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
  );

  static const titleLarge = TextStyle(
    fontFamily: fontFamily,
    fontSize: 18,
    height: 1.3,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
  );

  static const bodyLarge = TextStyle(
    fontFamily: fontFamily,
    fontSize: 16,
    height: 1.5,
    fontWeight: FontWeight.w400,
    color: AppColors.textPrimary,
  );

  static const bodyMedium = TextStyle(
    fontFamily: fontFamily,
    fontSize: 14,
    height: 1.5,
    fontWeight: FontWeight.w400,
    color: AppColors.textSecondary,
  );

  static const bodySmall = TextStyle(
    fontFamily: fontFamily,
    fontSize: 12,
    height: 1.45,
    fontWeight: FontWeight.w400,
    color: AppColors.textSecondary,
  );

  static const labelLarge = TextStyle(
    fontFamily: fontFamily,
    fontSize: 16,
    height: 1.2,
    fontWeight: FontWeight.w700,
    color: AppColors.white,
  );

  static const labelMedium = TextStyle(
    fontFamily: fontFamily,
    fontSize: 14,
    height: 1.2,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );

  static const caption = TextStyle(
    fontFamily: fontFamily,
    fontSize: 12,
    height: 1.4,
    fontWeight: FontWeight.w400,
    color: AppColors.textSecondary,
  );
}
