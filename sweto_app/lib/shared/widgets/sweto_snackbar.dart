import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';

enum SwetoSnackBarType { success, error, warning, info }

void showSwetoSnackBar(
  BuildContext context, {
  required String message,
  SwetoSnackBarType type = SwetoSnackBarType.info,
  String? actionLabel,
  VoidCallback? onAction,
  Duration duration = const Duration(seconds: 3),
}) {
  final color = switch (type) {
    SwetoSnackBarType.success => AppColors.secondary,
    SwetoSnackBarType.error => AppColors.error,
    SwetoSnackBarType.warning => AppColors.primary,
    SwetoSnackBarType.info => AppColors.primary,
  };
  final icon = switch (type) {
    SwetoSnackBarType.success => Icons.check_circle_outline,
    SwetoSnackBarType.error => Icons.error_outline,
    SwetoSnackBarType.warning => Icons.warning_amber_outlined,
    SwetoSnackBarType.info => Icons.info_outline,
  };
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(
        duration: duration,
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.fromLTRB(16, 0, 16, 20),
        backgroundColor: AppColors.surface,
        elevation: 6,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          side: BorderSide(color: color.withValues(alpha: .55)),
        ),
        content: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                message,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: AppColors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  height: 1.25,
                ),
              ),
            ),
          ],
        ),
        action: actionLabel == null
            ? null
            : SnackBarAction(label: actionLabel, onPressed: onAction ?? () {}),
      ),
    );
}
