import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/check_in_code_share.dart';

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
            switch (code.smsStatus) {
              'sent' =>
                'Also sent to the member by SMS. Share it on WhatsApp too if '
                    'they like. It won\'t be shown here again; issuing a new '
                    'code replaces it.',
              'failed' =>
                'The SMS couldn\'t be sent, so share it or let the member '
                    'photograph this now. It won\'t be shown again.',
              _ =>
                'Share it with the member now, or let them photograph it. '
                    'It won\'t be shown again; issuing a new code replaces it.',
            },
            key: const Key('check-in-code-note'),
            textAlign: TextAlign.center,
            style: AppTextStyles.bodySmall,
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(
                child: _ShareButton(memberName: memberName, code: code),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Done'),
                ),
              ),
            ],
          ),
        ],
      ),
    ),
  ),
);

/// Shares the QR image and the code through the phone's share sheet.
class _ShareButton extends ConsumerStatefulWidget {
  const _ShareButton({required this.memberName, required this.code});

  final String memberName;
  final CheckInCode code;

  @override
  ConsumerState<_ShareButton> createState() => _ShareButtonState();
}

class _ShareButtonState extends ConsumerState<_ShareButton> {
  bool _busy = false;

  Future<void> _share() async {
    setState(() => _busy = true);
    // Where the share sheet points from on iPad.
    final box = context.findRenderObject() as RenderBox?;
    final origin = box == null
        ? null
        : box.localToGlobal(Offset.zero) & box.size;
    final share = ref.read(checkInCodeSharerProvider);
    try {
      final png = await checkInQrPng(widget.code.qrPayload);
      await share(
        png: png,
        fileName: checkInQrFileName(widget.memberName),
        text: checkInCodeShareText(widget.memberName, widget.code),
        origin: origin,
      );
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(
          const SnackBar(content: Text('Couldn\'t open sharing. Try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => FilledButton.icon(
    key: const Key('check-in-share'),
    onPressed: _busy ? null : _share,
    style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
    // The label stays "Share" so it never wraps; a spinner shows the wait.
    icon: _busy
        ? const SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: AppColors.white,
            ),
          )
        : const Icon(Icons.ios_share, size: 18),
    label: const Text('Share', maxLines: 1),
  );
}
