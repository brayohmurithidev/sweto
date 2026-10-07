import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';

class AppBottomPanel extends StatelessWidget {
  const AppBottomPanel({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.vertical(top: Radius.circular(36)),
      ),
      child: child,
    );
  }
}
