import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';

/// Everything else: the gym's details, check-in, the M-Pesa till, log out.
class MoreTab extends StatelessWidget {
  const MoreTab({
    required this.gymId,
    required this.gymName,
    required this.onLogout,
    super.key,
  });

  final String gymId;
  final String gymName;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
    children: [
      Text('More', style: AppTextStyles.headingMedium),
      const SizedBox(height: AppSpacing.md),
      _tile(
        icon: Icons.verified_outlined,
        title: gymName,
        subtitle: 'Verified gym',
      ),
      const SizedBox(height: AppSpacing.lg),
      Text('Your gym', style: AppTextStyles.titleLarge),
      const SizedBox(height: AppSpacing.xs),
      for (final (key, icon, title, subtitle, route) in _gymSettings) ...[
        _tile(
          key: Key(key),
          icon: icon,
          title: title,
          subtitle: subtitle,
          onTap: () =>
              context.pushNamed(route, pathParameters: {'gymId': gymId}),
        ),
        const SizedBox(height: AppSpacing.sm),
      ],
      const SizedBox(height: AppSpacing.md),
      Text('Payments and door', style: AppTextStyles.titleLarge),
      const SizedBox(height: AppSpacing.xs),
      _tile(
        key: const Key('more-check-in'),
        icon: Icons.qr_code_scanner,
        title: 'Check in',
        subtitle: 'Scan a member\'s QR or type their code',
        onTap: () => context.pushNamed(
          AppRoutes.checkInName,
          pathParameters: {'gymId': gymId},
        ),
      ),
      const SizedBox(height: AppSpacing.sm),
      _tile(
        key: const Key('more-mpesa-till'),
        icon: Icons.account_balance_outlined,
        title: 'M-Pesa till',
        subtitle: 'Where members\' M-Pesa payments go',
        onTap: () => context.pushNamed(
          AppRoutes.mpesaTillName,
          pathParameters: {'gymId': gymId},
        ),
      ),
      const SizedBox(height: AppSpacing.lg),
      _tile(
        key: const Key('more-logout'),
        icon: Icons.logout_rounded,
        title: 'Log out',
        onTap: onLogout,
      ),
    ],
  );

  static const _gymSettings = [
    (
      'more-gym-profile',
      Icons.storefront_outlined,
      'Gym profile',
      'Name, contacts, description and photos',
      AppRoutes.gymProfileSettingsName,
    ),
    (
      'more-gym-plans',
      Icons.sell_outlined,
      'Plans & prices',
      'Day pass and membership prices',
      AppRoutes.gymPlansSettingsName,
    ),
    (
      'more-gym-hours',
      Icons.schedule,
      'Opening hours',
      'When members can come in',
      AppRoutes.gymHoursSettingsName,
    ),
    (
      'more-gym-amenities',
      Icons.fitness_center,
      'Amenities',
      'What your gym offers',
      AppRoutes.gymAmenitiesSettingsName,
    ),
    (
      'more-gym-location',
      Icons.place_outlined,
      'Location',
      'Address and map pin',
      AppRoutes.gymLocationSettingsName,
    ),
  ];

  Widget _tile({
    required IconData icon,
    required String title,
    String? subtitle,
    VoidCallback? onTap,
    Key? key,
  }) => Material(
    color: AppColors.surface,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(AppRadius.lg),
      side: const BorderSide(color: AppColors.border),
    ),
    clipBehavior: Clip.antiAlias,
    child: ListTile(
      key: key,
      leading: Icon(icon, color: AppColors.primary),
      title: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: subtitle == null
          ? null
          : Text(subtitle, style: AppTextStyles.bodySmall),
      trailing: onTap == null
          ? null
          : const Icon(Icons.arrow_forward_ios, size: 16),
      onTap: onTap,
    ),
  );
}
