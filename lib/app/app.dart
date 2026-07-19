import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/app_theme.dart';
import 'package:sweto_app/features/health/presentation/health_check_screen.dart';

class SwetoApp extends StatelessWidget {
  const SwetoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SWETO',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.dark(),
      home: const HealthCheckScreen(),
    );
  }
}
