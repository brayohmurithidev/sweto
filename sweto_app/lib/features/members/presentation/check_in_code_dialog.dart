import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';

/// Shows a newly issued code once: the server keeps only a hash of it.
Future<void> showCheckInCodeDialog(
  BuildContext context, {
  required String memberName,
  required CheckInCode code,
}) => showDialog<void>(
  context: context,
  builder: (context) => Dialog(
    backgroundColor: AppColors.surface,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(AppRadius.xl),
    ),
    child: Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            memberName,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: AppTextStyles.titleLarge,
          ),
          const SizedBox(height: AppSpacing.md),
          Container(
            padding: const EdgeInsets.all(AppSpacing.sm),
            decoration: BoxDecoration(
              color: AppColors.white,
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: QrImageView(
              key: const Key('check-in-qr'),
              data: code.qrPayload,
              size: 200,
              backgroundColor: AppColors.white,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          SelectableText(
            code.code,
            key: const Key('check-in-code'),
            style: AppTextStyles.headingLarge.copyWith(letterSpacing: 4),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Let the member photograph this now, or note the code. '
            'It won\'t be shown again; issuing a new code replaces it.',
            textAlign: TextAlign.center,
            style: AppTextStyles.bodySmall,
          ),
          const SizedBox(height: AppSpacing.md),
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Done'),
          ),
        ],
      ),
    ),
  ),
);
