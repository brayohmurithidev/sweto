import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/config/config_providers.dart';
import 'package:sweto_app/core/network/api_exception.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/features/health/data/health_providers.dart';
import 'package:dio/dio.dart';

class HealthCheckScreen extends ConsumerWidget {
  const HealthCheckScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = ref.watch(appConfigProvider);
    final healthState = ref.watch(healthCheckProvider);

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Center(
            child: healthState.when(
              loading: () => const _HealthLoading(),
              data: (health) => _HealthSuccess(
                environment: config.environment.name,
                apiBaseUrl: config.apiBaseUrl,
                status: health.status,
              ),
              error: (error, stackTrace) => _HealthFailure(
                message: _errorMessage(error),
                onRetry: () {
                  ref.invalidate(healthCheckProvider);
                },
              ),
            ),
          ),
        ),
      ),
    );
  }

  String _errorMessage(Object error) {
    if (error is DioException && error.error is ApiException) {
      return (error.error! as ApiException).message;
    }

    if (error is ApiException) {
      return error.message;
    }

    return 'Unable to connect to the SWETO API.';
  }
}

class _HealthLoading extends StatelessWidget {
  const _HealthLoading();

  @override
  Widget build(BuildContext context) {
    return const Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        CircularProgressIndicator(),
        SizedBox(height: AppSpacing.md),
        Text('Connecting to SWETO API…'),
      ],
    );
  }
}

class _HealthSuccess extends StatelessWidget {
  const _HealthSuccess({
    required this.environment,
    required this.apiBaseUrl,
    required this.status,
  });

  final String environment;
  final String apiBaseUrl;
  final String status;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.check_circle, size: 72, color: AppColors.success),
        const SizedBox(height: AppSpacing.md),
        Text('API Connected', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: AppSpacing.sm),
        Text('Status: $status'),
        const SizedBox(height: AppSpacing.sm),
        Text('Environment: $environment'),
        const SizedBox(height: AppSpacing.xs),
        Text(
          apiBaseUrl,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}

class _HealthFailure extends StatelessWidget {
  const _HealthFailure({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.cloud_off, size: 72, color: AppColors.error),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Connection Failed',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(message, textAlign: TextAlign.center),
        const SizedBox(height: AppSpacing.lg),
        FilledButton(onPressed: onRetry, child: const Text('Retry')),
      ],
    );
  }
}
