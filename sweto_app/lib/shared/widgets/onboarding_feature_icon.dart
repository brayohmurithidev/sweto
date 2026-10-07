import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';

class OnboardingFeatureIcon extends StatelessWidget {
  const OnboardingFeatureIcon({super.key, required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 58,
      height: 58,
      decoration: BoxDecoration(
        color: AppColors.backgroundSoft,
        shape: BoxShape.circle,
        border: Border.all(color: AppColors.primary, width: 1.8),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: 0.18),
            blurRadius: 18,
          ),
        ],
      ),
      child: Icon(icon, size: 28, color: AppColors.primary),
    );
  }
}
