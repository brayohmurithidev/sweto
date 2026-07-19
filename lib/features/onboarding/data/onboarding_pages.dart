import 'package:flutter/material.dart';
import 'package:sweto_app/features/onboarding/domain/onboarding_page_data.dart';

const onboardingPages = [
  OnboardingPageData(
    imagePath: 'assets/images/onboarding/find_gyms.jpg',
    icon: Icons.location_on_outlined,
    title: 'Find Gyms Near You',
    description:
        'Discover the best gyms in Nairobi, Mombasa, Kampala and beyond — '
        'with real prices in KES.',
    buttonLabel: 'Next',
  ),
  OnboardingPageData(
    imagePath: 'assets/images/onboarding/book_and_pay.jpg',
    icon: Icons.receipt_long_outlined,
    title: 'Book & Pay\nwith M-Pesa',
    description:
        'Reserve your spot and pay instantly with M-Pesa. '
        'No cash, no queues, no hassle.',
    buttonLabel: 'Next',
  ),
  OnboardingPageData(
    imagePath: 'assets/images/onboarding/find_buddy.jpg',
    icon: Icons.group_outlined,
    title: 'Find Your\nSweto Buddy',
    description:
        'Match with workout partners near you who share your goals. '
        'Sweat together, grow together.',
    buttonLabel: 'Get Started',
  ),
];
