import 'package:flutter/material.dart';

class AppImageOverlay extends StatelessWidget {
  const AppImageOverlay({super.key});

  @override
  Widget build(BuildContext context) {
    return const IgnorePointer(
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0x22000000),
              Color(0x00000000),
              Color(0x33000000),
              Color(0xF0050505),
            ],
            stops: [0, 0.35, 0.58, 1],
          ),
        ),
      ),
    );
  }
}
