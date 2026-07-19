import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/text_styles.dart';

enum SwetoDialogType { confirmation, destructive, success, info }

Future<bool> showSwetoConfirmationDialog(
  BuildContext context, {
  required String title,
  required String message,
  required String confirmLabel,
  String cancelLabel = 'Cancel',
  SwetoDialogType type = SwetoDialogType.confirmation,
  bool barrierDismissible = true,
}) async {
  final accent = type == SwetoDialogType.destructive
      ? AppColors.error
      : AppColors.primary;
  return await showDialog<bool>(
        context: context,
        barrierDismissible: barrierDismissible,
        builder: (context) => Dialog(
          backgroundColor: AppColors.surface,
          insetPadding: const EdgeInsets.symmetric(
            horizontal: 28,
            vertical: 24,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.xl),
            side: const BorderSide(color: AppColors.border),
          ),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 360),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (type == SwetoDialogType.confirmation)
                        const Padding(
                          padding: EdgeInsets.only(right: 10, top: 2),
                          child: Icon(
                            Icons.shield_outlined,
                            color: AppColors.primary,
                            size: 24,
                          ),
                        ),
                      Expanded(
                        child: Text(
                          title,
                          style: const TextStyle(
                            color: AppColors.white,
                            fontSize: 22,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxHeight: 160),
                    child: SingleChildScrollView(
                      child: Text(message, style: AppTextStyles.bodyMedium),
                    ),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(false),
                        child: Text(cancelLabel),
                      ),
                      const SizedBox(width: 8),
                      FilledButton(
                        style: FilledButton.styleFrom(
                          backgroundColor: accent,
                          minimumSize: const Size(96, 44),
                        ),
                        onPressed: () => Navigator.of(context).pop(true),
                        child: Text(confirmLabel),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ) ??
      false;
}
