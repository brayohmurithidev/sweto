import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';

class SwetoLoadingBar extends StatelessWidget {
  const SwetoLoadingBar({super.key, required this.progress});

  final double progress;

  @override
  Widget build(BuildContext context) {
    final normalizedProgress = progress.clamp(0.0, 1.0);

    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.pill),
      child: SizedBox(
        height: 4,
        child: Stack(
          children: [
            const Positioned.fill(
              child: ColoredBox(color: AppColors.surfaceElevated),
            ),
            FractionallySizedBox(
              widthFactor: normalizedProgress,
              child: const ColoredBox(color: AppColors.primary),
            ),
          ],
        ),
      ),
    );
  }
}
