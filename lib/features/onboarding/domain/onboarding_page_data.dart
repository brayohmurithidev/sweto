import 'package:flutter/material.dart';

class OnboardingPageData {
  const OnboardingPageData({
    required this.imagePath,
    required this.icon,
    required this.title,
    required this.description,
  });

  final String imagePath;
  final IconData icon;
  final String title;
  final String description;
}
