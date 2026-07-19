import 'package:flutter/material.dart';

class SwetoLogo extends StatelessWidget {
  const SwetoLogo({this.width = 180, super.key});

  final double width;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      'assets/images/branding/sweto_logo.png',
      width: width,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
      errorBuilder: (context, error, stackTrace) {
        return const Text(
          'SWETO',
          style: TextStyle(
            color: Colors.white,
            fontSize: 32,
            fontWeight: FontWeight.w900,
          ),
        );
      },
    );
  }
}
