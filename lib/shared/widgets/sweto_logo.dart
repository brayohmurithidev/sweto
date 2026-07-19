import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';

class SwetoLogo extends StatelessWidget {
  const SwetoLogo({super.key, this.width = 220, this.showTagline = true});

  final double width;
  final bool showTagline;

  @override
  Widget build(BuildContext context) {
    final logoFontSize = width * 0.22;
    final taglineFontSize = width * 0.045;

    return SizedBox(
      width: width,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'SW',
                  style: AppTextStyles.displayLarge.copyWith(
                    fontSize: logoFontSize,
                    fontStyle: FontStyle.italic,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -2,
                  ),
                ),
                _SpeedMark(height: logoFontSize * 0.72),
                Text(
                  'TO',
                  style: AppTextStyles.displayLarge.copyWith(
                    fontSize: logoFontSize,
                    fontStyle: FontStyle.italic,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -2,
                  ),
                ),
              ],
            ),
          ),
          if (showTagline) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(
              'S W E A T   T O G E T H E R',
              textAlign: TextAlign.center,
              style: AppTextStyles.caption.copyWith(
                fontSize: taglineFontSize,
                color: AppColors.white,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.7,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SpeedMark extends StatelessWidget {
  const _SpeedMark({required this.height});

  final double height;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: height * 0.78,
      height: height,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _OrangeBar(widthFactor: 0.78, height: height * 0.22),
          _OrangeBar(widthFactor: 1, height: height * 0.22),
          _OrangeBar(widthFactor: 0.82, height: height * 0.22),
        ],
      ),
    );
  }
}

class _OrangeBar extends StatelessWidget {
  const _OrangeBar({required this.widthFactor, required this.height});

  final double widthFactor;
  final double height;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: FractionallySizedBox(
        widthFactor: widthFactor,
        child: Transform(
          alignment: Alignment.center,
          transform: Matrix4.skewX(-0.25),
          child: Container(
            height: height,
            decoration: BoxDecoration(
              color: AppColors.primary,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
      ),
    );
  }
}
