import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';

class OnboardingIcon extends StatelessWidget {
  const OnboardingIcon({super.key, required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 54,
      height: 54,
      decoration: BoxDecoration(
        color: AppColors.background,
        shape: BoxShape.circle,
        border: Border.all(color: AppColors.primary, width: 1.8),
      ),
      child: Icon(icon, color: AppColors.primary, size: 27),
    );
  }
}
