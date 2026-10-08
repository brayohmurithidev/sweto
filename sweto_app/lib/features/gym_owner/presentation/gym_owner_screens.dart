import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_selector/file_selector.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/network/api_exception.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/auth/presentation/auth_providers.dart';
import 'package:sweto_app/features/auth/presentation/session_controller.dart';
import 'package:sweto_app/features/auth/presentation/widgets/kenya_phone_field.dart';
import 'package:sweto_app/features/auth/utils/kenya_phone_formatter.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_owner_entities.dart';
import 'package:sweto_app/features/gym_owner/domain/gym_location_service.dart';
import 'package:sweto_app/features/gym_owner/domain/onboarding_progress.dart';
import 'package:sweto_app/features/gym_owner/presentation/onboarding_coordinator.dart';
import 'package:sweto_app/shared/widgets/app_primary_button.dart';
import 'package:sweto_app/shared/widgets/sweto_logo.dart';
import 'package:sweto_app/shared/widgets/sweto_snackbar.dart';
import 'package:sweto_app/shared/widgets/sweto_dialog.dart';

void goToDestination(BuildContext context, OnboardingDestination destination) {
  final route = switch (destination) {
    OnboardingDestination.accountType => AppRoutes.accountTypeName,
    OnboardingDestination.gymRegistration => AppRoutes.gymRegistrationName,
    OnboardingDestination.location => AppRoutes.gymLocationName,
    OnboardingDestination.businessDetails => AppRoutes.gymBusinessDetailsName,
    OnboardingDestination.amenities => AppRoutes.gymAmenitiesName,
    OnboardingDestination.operatingHours => AppRoutes.gymOperatingHoursName,
    OnboardingDestination.pricing => AppRoutes.gymPricingName,
    OnboardingDestination.verification => AppRoutes.gymVerificationName,
    OnboardingDestination.verificationPending =>
      AppRoutes.verificationPendingName,
    OnboardingDestination.home => AppRoutes.homeName,
    OnboardingDestination.memberComingSoon => AppRoutes.memberComingSoonName,
    OnboardingDestination.unsupported => AppRoutes.unsupportedOnboardingName,
  };
  context.goNamed(route);
}

class AccountTypeScreen extends ConsumerStatefulWidget {
  const AccountTypeScreen({super.key});
  @override
  ConsumerState<AccountTypeScreen> createState() => _AccountTypeScreenState();
}

class _AccountTypeScreenState extends ConsumerState<AccountTypeScreen> {
  bool _ownerSelected = false;
  bool _loading = false;
  String? _error;

  Future<void> _continue() async {
    if (!_ownerSelected) {
      await showModalBottomSheet<void>(
        context: context,
        backgroundColor: AppColors.surfaceElevated,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppRadius.xl),
          ),
        ),
        showDragHandle: true,
        builder: (_) => const _MemberComingSoonSheet(),
      );
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final destination = await ref
          .read(onboardingCoordinatorProvider)
          .selectGymOwner();
      if (mounted) goToDestination(context, destination);
    } on DioException catch (error) {
      if (mounted) setState(() => _error = _apiMessage(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    child: Column(
      children: [
        const SwetoLogo(width: 135),
        const SizedBox(height: AppSpacing.sm),
        const SizedBox(height: 22),
        Text(
          'SWEAT TOGETHER',
          style: AppTextStyles.labelMedium.copyWith(
            color: AppColors.textMuted,
            letterSpacing: 2,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Welcome to SWETO 👋',
          style: AppTextStyles.headingLarge.copyWith(color: AppColors.white),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'How will you use SWETO?\nYou can change this anytime in settings.',
          textAlign: TextAlign.center,
          style: AppTextStyles.bodyMedium,
        ),
        const SizedBox(height: AppSpacing.md),
        _RoleCard(
          key: const Key('member-role-card'),
          title: 'I’m looking for a Gym',
          bullets: const [
            'Discover gyms near you',
            'Book with M-Pesa instantly',
            'Find workout buddies',
            'Join fitness communities',
            'Track your progress',
          ],
          imageAsset: 'assets/images/onboarding/role_member.png',
          accent: AppColors.primary,
          icon: Icons.groups_outlined,
          selected: !_ownerSelected,
          badge: 'Coming Soon',
          onTap: () => setState(() => _ownerSelected = false),
        ),
        const SizedBox(height: AppSpacing.md),
        _RoleCard(
          key: const Key('gym-owner-role-card'),
          title: 'I own or manage a Gym',
          bullets: const [
            'Accept bookings',
            'Scan member QR codes',
            'Manage memberships',
            'Track revenue & analytics',
            'Receive M-Pesa payouts',
          ],
          imageAsset: 'assets/images/onboarding/role_gym_owner.png',
          accent: AppColors.secondary,
          icon: Icons.business_outlined,
          selected: _ownerSelected,
          onTap: () => setState(() => _ownerSelected = true),
        ),
        if (_error != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            _error!,
            key: const Key('account-type-error'),
            style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
        AppPrimaryButton(
          key: const Key('account-type-continue'),
          label: _loading ? 'Continuing...' : 'Continue',
          onPressed: _loading ? null : _continue,
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Your data is secure with us.',
          textAlign: TextAlign.center,
          style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted),
        ),
        const SizedBox(height: AppSpacing.xs),
        Text.rich(
          TextSpan(
            text: 'By continuing you agree to our ',
            children: [
              TextSpan(
                text: 'Terms & Conditions',
                style: TextStyle(color: AppColors.primary),
              ),
              const TextSpan(text: ' and '),
              TextSpan(
                text: 'Privacy Policy',
                style: TextStyle(color: AppColors.primary),
              ),
              const TextSpan(text: '.'),
            ],
          ),
          textAlign: TextAlign.center,
          style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          '👋 Karibu! Let\'s build a stronger fitness community together.',
          textAlign: TextAlign.center,
          style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted),
        ),
      ],
    ),
  );
}

class GymRegistrationScreen extends ConsumerStatefulWidget {
  const GymRegistrationScreen({super.key});
  @override
  ConsumerState<GymRegistrationScreen> createState() =>
      _GymRegistrationScreenState();
}

class _GymRegistrationScreenState extends ConsumerState<GymRegistrationScreen> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _phoneFocus = FocusNode();
  final _email = TextEditingController();
  final _description = TextEditingController();
  bool _loading = false;
  String? _error;
  String? _phoneError;
  String? _emailError;
  String? _gymId;
  bool _editing = false;
  final _picker = ImagePicker();
  final List<_PendingPhoto> _pendingPhotos = [];
  List<GymPhoto> _uploadedPhotos = [];
  bool _photosLoading = false;

  @override
  void initState() {
    super.initState();
    ref
        .read(authRepositoryProvider)
        .getMe()
        .then((user) {
          if (!mounted) return;
          _phone.text = KenyaPhoneFormatter.formatForField(
            user.phoneNumber ?? '',
          );
          _email.text = user.email ?? '';
        })
        .catchError((_) {});
    try {
      ref
          .read(gymOwnerRepositoryProvider)
          .getCurrentGym()
          .then((gym) {
            if (!mounted) return;
            setState(() {
              _gymId = gym.id;
              _editing = true;
              _name.text = gym.name;
              _phone.text = KenyaPhoneFormatter.formatForField(
                gym.phoneNumber ?? '',
              );
              _email.text = gym.email ?? '';
              _description.text = gym.description ?? '';
            });
            _loadPhotos(gym.id);
          })
          .catchError((_) {});
    } catch (_) {
      // The repository may be unavailable on an unauthenticated create route.
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _phoneFocus.dispose();
    _email.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final name = _name.text.trim();
    final email = _email.text.trim();
    final phone = _phone.text.trim();
    if (name.length < 2) {
      setState(() => _error = 'Enter your gym name.');
      return;
    }
    if (phone.isNotEmpty && !KenyaPhoneFormatter.isValid(phone)) {
      setState(() => _phoneError = 'Enter a valid Kenyan mobile number.');
      return;
    }
    if (email.isNotEmpty &&
        !RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)) {
      setState(() => _emailError = 'Enter a valid email address.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final input = CreateGymInput(
        name: name,
        phoneNumber: phone.isEmpty
            ? null
            : KenyaPhoneFormatter.toInternational(phone),
        email: email.isEmpty ? null : email.toLowerCase(),
        description: _description.text.trim().isEmpty
            ? null
            : _description.text.trim(),
      );
      final repository = ref.read(gymOwnerRepositoryProvider);
      final gym = _gymId == null
          ? await repository.createGym(input)
          : await repository.updateBasicInformation(_gymId!, input);
      _gymId = gym.id;
      await _uploadPendingPhotos(gym.id);
      if (_pendingPhotos.any((photo) => photo.status == _PhotoStatus.failed)) {
        if (mounted)
          setState(
            () => _error =
                'Some photos could not be uploaded. Retry them to continue.',
          );
        return;
      }
      final destination = await ref
          .read(onboardingCoordinatorProvider)
          .createdGym(gym);
      if (mounted) goToDestination(context, destination);
    } on DioException catch (error) {
      final apiError = error.error;
      if (apiError is ApiException &&
          (apiError.statusCode == 409 ||
              apiError.code == 'GYM_ALREADY_EXISTS')) {
        try {
          final current = await ref
              .read(gymOwnerRepositoryProvider)
              .getCurrentGym();
          final destination = await ref
              .read(onboardingCoordinatorProvider)
              .createdGym(current);
          if (mounted) goToDestination(context, destination);
          return;
        } catch (_) {}
      }
      if (mounted) setState(() => _error = _apiMessage(error));
    } on FormatException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _pickPhotos() async {
    final remaining = 5 - _uploadedPhotos.length - _pendingPhotos.length;
    if (remaining <= 0) return;
    List<XFile> selected;
    try {
      selected = await _picker.pickMultiImage();
    } on PlatformException {
      try {
        final single = await _picker.pickImage(source: ImageSource.gallery);
        selected = single == null ? <XFile>[] : <XFile>[single];
      } on PlatformException {
        if (mounted)
          _showPhotoMessage('Photo access is unavailable right now.');
        return;
      }
    }
    if (selected.isEmpty) return;
    for (final file in selected.take(remaining)) {
      final mime = _mimeFor(file.name);
      final size = await file.length();
      if (mime == null || size <= 0 || size > 10 * 1024 * 1024) continue;
      if (mounted) {
        setState(
          () => _pendingPhotos.add(
            _PendingPhoto(file: file, mimeType: mime, size: size),
          ),
        );
      }
    }
  }

  void _showPhotoMessage(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: const Color(0xFF1A1A1A),
          behavior: SnackBarBehavior.floating,
          margin: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          duration: const Duration(seconds: 2),
        ),
      );
  }

  String? _mimeFor(String name) {
    final extension = name.split('.').last.toLowerCase();
    return switch (extension) {
      'jpg' || 'jpeg' => 'image/jpeg',
      'png' => 'image/png',
      'webp' => 'image/webp',
      _ => null,
    };
  }

  Future<void> _loadPhotos(String gymId) async {
    if (mounted) setState(() => _photosLoading = true);
    try {
      final photos = await ref
          .read(gymOwnerRepositoryProvider)
          .getGymPhotos(gymId);
      if (mounted) setState(() => _uploadedPhotos = photos);
    } catch (_) {
      // The form remains usable; a later refresh can load the signed URLs.
    } finally {
      if (mounted) setState(() => _photosLoading = false);
    }
  }

  Future<void> _uploadPendingPhotos(String gymId) async {
    final repository = ref.read(gymOwnerRepositoryProvider);
    for (final photo in _pendingPhotos) {
      if (photo.status == _PhotoStatus.uploaded) continue;
      try {
        if (mounted) setState(() => photo.status = _PhotoStatus.preparing);
        final intent = await repository.initiateGymPhotoUpload(
          gymId,
          filename: photo.file.name,
          mimeType: photo.mimeType,
          fileSize: photo.size,
        );
        photo.uploadId = intent.uploadId;
        if (mounted) setState(() => photo.status = _PhotoStatus.uploading);
        final bytes = await photo.file.readAsBytes();
        await repository.uploadGymPhotoToPresignedUrl(
          intent,
          bytes,
          mimeType: photo.mimeType,
          onProgress: (sent, total) {
            if (mounted && total > 0)
              setState(() => photo.progress = sent / total);
          },
        );
        if (mounted) setState(() => photo.status = _PhotoStatus.completing);
        await repository.completeGymPhotoUpload(gymId, intent.uploadId);
        if (mounted)
          setState(() {
            photo.status = _PhotoStatus.uploaded;
            photo.progress = 1;
          });
      } catch (_) {
        if (mounted) setState(() => photo.status = _PhotoStatus.failed);
      }
    }
    await _loadPhotos(gymId);
  }

  void _removePending(_PendingPhoto photo) =>
      setState(() => _pendingPhotos.remove(photo));

  Future<void> _deleteUploaded(GymPhoto photo) async {
    if (_gymId == null) return;
    try {
      await ref
          .read(gymOwnerRepositoryProvider)
          .deleteGymPhoto(_gymId!, photo.id);
      await _loadPhotos(_gymId!);
    } catch (_) {
      if (mounted)
        setState(
          () => _error = 'Unable to delete this photo. Please try again.',
        );
    }
  }

  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            IconButton(
              key: const Key('gym-registration-back'),
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.goNamed(AppRoutes.splashName),
            ),
            Expanded(
              child: Text(
                'Step 1 of ${GymOwnerProgress.ordered.length}',
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(width: 48),
          ],
        ),
        ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.pill),
          child: const LinearProgressIndicator(
            key: Key('gym-registration-progress'),
            value: 1 / 6,
            minHeight: 4,
            backgroundColor: AppColors.border,
            valueColor: AlwaysStoppedAnimation(AppColors.primary),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Register Your Gym',
          style: AppTextStyles.headingLarge.copyWith(color: AppColors.white),
        ),
        const SizedBox(height: AppSpacing.sm),
        const Text(
          'Let\'s get your gym set up on SWETO.',
          style: AppTextStyles.bodyMedium,
        ),
        const SizedBox(height: AppSpacing.sm),
        _GymPhotoSection(
          uploaded: _uploadedPhotos,
          pending: _pendingPhotos,
          loading: _photosLoading,
          onAdd: _loading ? null : _pickPhotos,
          onRemovePending: _removePending,
          onRetry: _gymId == null ? null : () => _uploadPendingPhotos(_gymId!),
          onDeleteUploaded: _deleteUploaded,
        ),
        const SizedBox(height: AppSpacing.sm),
        _field(_name, 'Gym name *', key: 'gym-name-field'),
        KenyaPhoneField(
          key: const Key('gym-phone-field'),
          fieldKey: const Key('gym-phone-input'),
          compact: true,
          controller: _phone,
          focusNode: _phoneFocus,
          errorText: _phoneError,
          onChanged: (_) => setState(() => _phoneError = null),
        ),
        const SizedBox(height: AppSpacing.sm),
        _field(
          _email,
          'Gym email',
          key: 'gym-email-field',
          keyboardType: TextInputType.emailAddress,
          errorText: _emailError,
          onChanged: (_) => setState(() => _emailError = null),
        ),
        _field(
          _description,
          'Description',
          key: 'gym-description-field',
          maxLines: 4,
          showCounter: true,
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.sm),
            child: Text(
              _error!,
              key: const Key('gym-registration-error'),
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
            ),
          ),
        const SizedBox(height: AppSpacing.md),
        AppPrimaryButton(
          key: const Key('create-gym-button'),
          label: _loading
              ? (_editing ? 'Saving changes...' : 'Creating gym...')
              : (_editing ? 'Save & Continue' : 'Continue'),
          onPressed: _loading ? null : _submit,
        ),
      ],
    ),
  );

  Widget _field(
    TextEditingController controller,
    String label, {
    required String key,
    TextInputType? keyboardType,
    int maxLines = 1,
    String? errorText,
    ValueChanged<String>? onChanged,
    bool showCounter = false,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: TextField(
      key: Key(key),
      controller: controller,
      keyboardType: keyboardType,
      maxLines: maxLines,
      maxLength: label == 'Description' ? 3000 : null,
      onChanged: onChanged,
      decoration: InputDecoration(
        labelText: label,
        errorText: errorText,
        filled: true,
        fillColor: AppColors.surface,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: 11,
        ),
        counterText: showCounter ? null : '',
      ),
    ),
  );
}

enum _PhotoStatus {
  selected,
  preparing,
  uploading,
  completing,
  uploaded,
  failed,
}

class _PendingPhoto {
  _PendingPhoto({
    required this.file,
    required this.mimeType,
    required this.size,
  });
  final XFile file;
  final String mimeType;
  final int size;
  _PhotoStatus status = _PhotoStatus.selected;
  double progress = 0;
  String? uploadId;
}

class _GymPhotoSection extends StatelessWidget {
  const _GymPhotoSection({
    required this.uploaded,
    required this.pending,
    required this.loading,
    required this.onAdd,
    required this.onRemovePending,
    required this.onRetry,
    required this.onDeleteUploaded,
  });
  final List<GymPhoto> uploaded;
  final List<_PendingPhoto> pending;
  final bool loading;
  final VoidCallback? onAdd;
  final ValueChanged<_PendingPhoto> onRemovePending;
  final VoidCallback? onRetry;
  final ValueChanged<GymPhoto> onDeleteUploaded;

  @override
  Widget build(BuildContext context) {
    final total = uploaded.length + pending.length;
    return Container(
      key: const Key('gym-photos-section'),
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Gym Photos', style: AppTextStyles.labelLarge),
          const SizedBox(height: 3),
          const Text(
            'Add up to 5 clear photos of your gym. The first uploaded photo will be the cover.',
          ),
          const SizedBox(height: AppSpacing.sm),
          if (loading) const LinearProgressIndicator(minHeight: 2),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              ...uploaded.map(
                (photo) => _RemotePhotoTile(
                  photo: photo,
                  onDelete: () => onDeleteUploaded(photo),
                ),
              ),
              ...pending.map(
                (photo) => _PendingPhotoTile(
                  photo: photo,
                  onRemove: () => onRemovePending(photo),
                  onRetry: onRetry,
                ),
              ),
              if (total < 5) _AddPhotoTile(onTap: onAdd),
            ],
          ),
        ],
      ),
    );
  }
}

class _RemotePhotoTile extends StatelessWidget {
  const _RemotePhotoTile({required this.photo, required this.onDelete});
  final GymPhoto photo;
  final VoidCallback onDelete;
  @override
  Widget build(BuildContext context) => _PhotoTileFrame(
    child: Stack(
      fit: StackFit.expand,
      children: [
        Image.network(
          photo.url,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) =>
              const Icon(Icons.image_not_supported_outlined),
        ),
        if (photo.isCover)
          const Positioned(left: 5, bottom: 5, child: _CoverBadge()),
        Positioned(
          top: 0,
          right: 0,
          child: IconButton(
            icon: const Icon(Icons.close, size: 16),
            onPressed: onDelete,
            color: Colors.white,
            style: IconButton.styleFrom(backgroundColor: Colors.black54),
          ),
        ),
      ],
    ),
  );
}

class _PendingPhotoTile extends StatelessWidget {
  const _PendingPhotoTile({
    required this.photo,
    required this.onRemove,
    required this.onRetry,
  });
  final _PendingPhoto photo;
  final VoidCallback onRemove;
  final VoidCallback? onRetry;
  @override
  Widget build(BuildContext context) => _PhotoTileFrame(
    child: Stack(
      fit: StackFit.expand,
      children: [
        Image.file(File(photo.file.path), fit: BoxFit.cover),
        if (photo.status == _PhotoStatus.uploading ||
            photo.status == _PhotoStatus.completing)
          Center(
            child: CircularProgressIndicator(
              value: photo.status == _PhotoStatus.uploading
                  ? photo.progress
                  : null,
            ),
          ),
        if (photo.status == _PhotoStatus.failed)
          Center(
            child: IconButton(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh, color: Colors.white),
              style: IconButton.styleFrom(backgroundColor: AppColors.error),
            ),
          ),
        Positioned(
          top: 0,
          right: 0,
          child: IconButton(
            icon: const Icon(Icons.close, size: 16),
            onPressed: onRemove,
            color: Colors.white,
            style: IconButton.styleFrom(backgroundColor: Colors.black54),
          ),
        ),
      ],
    ),
  );
}

class _PhotoTileFrame extends StatelessWidget {
  const _PhotoTileFrame({required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: 82,
    height: 82,
    child: ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: child,
    ),
  );
}

class _AddPhotoTile extends StatelessWidget {
  const _AddPhotoTile({required this.onTap});
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => _PhotoTileFrame(
    child: InkWell(
      onTap: onTap,
      child: const DecoratedBox(
        decoration: BoxDecoration(color: AppColors.surfaceElevated),
        child: Icon(
          Icons.add_photo_alternate_outlined,
          color: AppColors.primary,
        ),
      ),
    ),
  );
}

class _CoverBadge extends StatelessWidget {
  const _CoverBadge();
  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: const BoxDecoration(
      color: AppColors.secondary,
      borderRadius: BorderRadius.all(Radius.circular(6)),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
      child: Text(
        'Cover',
        style: TextStyle(
          color: Colors.black,
          fontSize: 9,
          fontWeight: FontWeight.w700,
        ),
      ),
    ),
  );
}

class GymPricingScreen extends ConsumerStatefulWidget {
  const GymPricingScreen({super.key});
  @override
  ConsumerState<GymPricingScreen> createState() => _GymPricingScreenState();
}

class _PlanDraft {
  _PlanDraft(this.name, this.period, {int? amount})
    : controller = TextEditingController(text: amount?.toString() ?? '');
  final String name;
  final String period;
  final TextEditingController controller;
  bool active = true;
}

class _GymPricingScreenState extends ConsumerState<GymPricingScreen> {
  final _dayPass = _PlanDraft('Day Pass', 'day_pass');
  final _plans = <_PlanDraft>[
    _PlanDraft('Monthly', 'monthly'),
    _PlanDraft('Quarterly', 'quarterly'),
    _PlanDraft('Annual', 'annual'),
  ];
  String? _gymId;
  String? _error;
  bool _loading = true;
  bool _saving = false;
  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _dayPass.controller.dispose();
    for (final plan in _plans) {
      plan.controller.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final repo = ref.read(gymOwnerRepositoryProvider);
      final gym = await repo.getCurrentGym();
      final pricing = await repo.getGymPricing(gym.id);
      if (!mounted) return;
      final all = [...pricing.dayPasses, ...pricing.membershipPlans];
      if (all.isNotEmpty) {
        _dayPass.active = false;
        for (final plan in _plans) {
          plan.active = false;
        }
      }
      for (final saved in all) {
        final target = saved.billingPeriod == 'day_pass'
            ? _dayPass
            : _plans.where((p) => p.period == saved.billingPeriod).firstOrNull;
        if (target == null) continue;
        target.controller.text = saved.amount.toString();
        target.active = saved.isActive;
      }
      setState(() {
        _gymId = gym.id;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'We couldn’t load pricing right now.';
      });
    }
  }

  String _clean(String value) => value.replaceAll(',', '').trim();
  Future<void> _editPlan(_PlanDraft plan) async {
    final editor = TextEditingController(text: plan.controller.text);
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Padding(
        padding: EdgeInsets.fromLTRB(
          20,
          20,
          20,
          MediaQuery.viewInsetsOf(context).bottom + 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(plan.name, style: AppTextStyles.headingMedium),
            const SizedBox(height: 6),
            Text('Price', style: AppTextStyles.bodyMedium),
            const SizedBox(height: 8),
            TextField(
              controller: editor,
              autofocus: true,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              decoration: const InputDecoration(
                prefixText: 'KES ',
                hintText: '3,500',
              ),
            ),
            const SizedBox(height: 18),
            AppPrimaryButton(
              label: 'Save price',
              onPressed: () {
                plan.controller.text = editor.text;
                Navigator.pop(context, true);
              },
            ),
          ],
        ),
      ),
    );
    // The bottom-sheet reverse animation may still be rebuilding its
    // TextField when showModalBottomSheet completes. Dispose after that
    // animation has released its listeners.
    await Future<void>.delayed(const Duration(milliseconds: 300));
    editor.dispose();
    if (saved == true && mounted) setState(() {});
  }

  Future<void> _save() async {
    if (_saving || _gymId == null) return;
    final drafts = [_dayPass, ..._plans];
    final active = drafts.where((p) => p.active).toList();
    if (active.isEmpty) {
      setState(() => _error = 'Enable at least one pricing option.');
      return;
    }
    for (final plan in active) {
      if (int.tryParse(_clean(plan.controller.text)) == null ||
          int.parse(_clean(plan.controller.text)) <= 0) {
        setState(() => _error = 'Enter a valid price for ${plan.name}.');
        return;
      }
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref
          .read(gymOwnerRepositoryProvider)
          .updateGymPricing(
            _gymId!,
            GymPricing(
              dayPasses: [_dayPass]
                  .map(
                    (p) => GymPricingPlan(
                      name: p.name,
                      amount: int.parse(_clean(p.controller.text)),
                      billingPeriod: p.period,
                      isActive: p.active,
                    ),
                  )
                  .toList(),
              membershipPlans: _plans
                  .map(
                    (p) => GymPricingPlan(
                      name: p.name,
                      amount: int.tryParse(_clean(p.controller.text)) ?? 0,
                      billingPeriod: p.period,
                      isActive: p.active,
                    ),
                  )
                  .toList(),
            ),
          );
      final destination = await ref
          .read(onboardingCoordinatorProvider)
          .resolve();
      if (!mounted) return;
      goToDestination(context, destination);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = 'Unable to save pricing. Please try again.';
      });
    }
  }

  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            IconButton(
              tooltip: 'Back',
              onPressed: () => context.canPop()
                  ? context.pop()
                  : context.goNamed(AppRoutes.gymOperatingHoursName),
              icon: const Icon(Icons.arrow_back),
            ),
            Expanded(
              child: Text(
                'Step 6 of 7',
                textAlign: TextAlign.center,
                style: AppTextStyles.bodyMedium,
              ),
            ),
            const SizedBox(width: 48),
          ],
        ),
        const SizedBox(height: 8),
        const LinearProgressIndicator(value: 6 / 7, minHeight: 3),
        const SizedBox(height: 24),
        Text('Membership Plans', style: AppTextStyles.headingLarge),
        const SizedBox(height: 8),
        Text('Set your membership pricing.', style: AppTextStyles.bodyMedium),
        const SizedBox(height: 6),
        Text(
          'Members will see these plans when booking your gym.',
          style: AppTextStyles.bodySmall,
        ),
        const SizedBox(height: 24),
        if (_loading)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(36),
              child: CircularProgressIndicator(),
            ),
          )
        else if (_error != null && _gymId == null) ...[
          Text(
            _error!,
            style: AppTextStyles.bodyMedium,
            textAlign: TextAlign.center,
          ),
          OutlinedButton(onPressed: _load, child: const Text('Retry')),
        ] else ...[
          _PricingCard(
            plan: _dayPass,
            onChanged: () => setState(() {}),
            onEdit: () => _editPlan(_dayPass),
          ),
          const SizedBox(height: 10),
          ..._plans.map(
            (p) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _PricingCard(
                plan: p,
                onChanged: () => setState(() {}),
                onEdit: () => _editPlan(p),
              ),
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_error!, style: TextStyle(color: AppColors.error)),
            ),
          const SizedBox(height: 28),
          AppPrimaryButton(
            key: const Key('gym-pricing-continue'),
            label: _saving ? 'Saving…' : 'Continue',
            onPressed: _saving ? null : _save,
          ),
        ],
      ],
    ),
  );
}

class _PricingCard extends StatelessWidget {
  const _PricingCard({
    required this.plan,
    required this.onChanged,
    required this.onEdit,
  });
  final _PlanDraft plan;
  final VoidCallback onChanged;
  final VoidCallback onEdit;
  IconData get _icon => switch (plan.period) {
    'day_pass' => Icons.confirmation_number_outlined,
    'weekly' => Icons.calendar_view_week_outlined,
    'monthly' => Icons.calendar_month_outlined,
    'quarterly' => Icons.date_range_outlined,
    'annual' => Icons.workspace_premium_outlined,
    _ => Icons.sell_outlined,
  };
  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    label: '${plan.name}, ${plan.active ? 'enabled' : 'disabled'}',
    child: InkWell(
      onTap: onEdit,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: Container(
        height: 76,
        padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(
            color: plan.active
                ? AppColors.primary.withValues(alpha: 0.35)
                : AppColors.border,
          ),
        ),
        child: Row(
          children: [
            Icon(
              _icon,
              color: plan.active ? AppColors.primary : AppColors.textMuted,
              size: 23,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(plan.name, style: AppTextStyles.labelMedium),
                  const SizedBox(height: 3),
                  Text(
                    _price(plan.controller.text),
                    style: AppTextStyles.bodySmall,
                  ),
                ],
              ),
            ),
            Switch(
              value: plan.active,
              onChanged: (value) {
                plan.active = value;
                onChanged();
              },
            ),
          ],
        ),
      ),
    ),
  );

  String _price(String raw) {
    final value = int.tryParse(raw.replaceAll(',', '').trim());
    if (value == null) return 'Price not set';
    return 'KES ${value.toString().replaceAllMapped(RegExp(r'(?<=\d)(?=(\d{3})+(?!\d))'), (m) => ',')}';
  }
}

class GymOperatingHoursScreen extends ConsumerStatefulWidget {
  const GymOperatingHoursScreen({super.key});
  @override
  ConsumerState<GymOperatingHoursScreen> createState() =>
      _GymOperatingHoursScreenState();
}

class _OperatingDraft {
  _OperatingDraft(
    this.day, {
    this.isClosed = true,
    this.is24Hours = false,
    this.open,
    this.close,
  });
  final int day;
  bool isClosed;
  bool is24Hours;
  TimeOfDay? open;
  TimeOfDay? close;
}

class _GymOperatingHoursScreenState
    extends ConsumerState<GymOperatingHoursScreen> {
  static const _names = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ];
  final _days = List.generate(7, (index) => _OperatingDraft(index));
  String? _gymId;
  String? _error;
  bool _loading = true;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  TimeOfDay? _parse(String? value) {
    if (value == null || value.isEmpty) return null;
    final parts = value.split(':');
    if (parts.length < 2) return null;
    return TimeOfDay(
      hour: int.tryParse(parts[0]) ?? 0,
      minute: int.tryParse(parts[1]) ?? 0,
    );
  }

  String? _format(TimeOfDay? value) => value == null
      ? null
      : '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';

  Future<void> _load() async {
    try {
      final repository = ref.read(gymOwnerRepositoryProvider);
      final gym = await repository.getCurrentGym();
      final saved = await repository.getOperatingHours(gym.id);
      if (!mounted) return;
      for (final item in saved) {
        if (item.dayOfWeek < 0 || item.dayOfWeek > 6) continue;
        final draft = _days[item.dayOfWeek];
        draft.isClosed = item.isClosed;
        draft.is24Hours = item.is24Hours;
        draft.open = _parse(item.opensAt);
        draft.close = _parse(item.closesAt);
      }
      setState(() {
        _gymId = gym.id;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'We couldn’t load operating hours right now.';
      });
    }
  }

  Future<void> _pickTime(_OperatingDraft day, bool opening) async {
    final value = await showTimePicker(
      context: context,
      initialTime:
          (opening ? day.open : day.close) ??
          const TimeOfDay(hour: 6, minute: 0),
    );
    if (!mounted || value == null) return;
    setState(() {
      if (opening) {
        day.open = value;
      } else {
        day.close = value;
      }
    });
  }

  void _copy(bool all) {
    final source = _days.first;
    final targets = all ? _days.skip(1) : _days.skip(1).take(4);
    setState(() {
      for (final target in targets) {
        target.isClosed = source.isClosed;
        target.is24Hours = source.is24Hours;
        target.open = source.open;
        target.close = source.close;
      }
    });
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Hours copied')));
  }

  Future<void> _save() async {
    if (_saving || _gymId == null) return;
    final openDays = _days.where((day) => !day.isClosed).toList();
    if (openDays.isEmpty) {
      setState(() => _error = 'Open at least one day to continue.');
      return;
    }
    for (final day in openDays) {
      if (!day.is24Hours && (day.open == null || day.close == null)) {
        setState(
          () =>
              _error = 'Set opening and closing hours for ${_names[day.day]}.',
        );
        return;
      }
      if (!day.is24Hours &&
          day.open!.hour * 60 + day.open!.minute >=
              day.close!.hour * 60 + day.close!.minute) {
        setState(
          () => _error =
              'Closing time must be later than opening time for ${_names[day.day]}.',
        );
        return;
      }
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref
          .read(gymOwnerRepositoryProvider)
          .updateOperatingHours(
            _gymId!,
            _days
                .map(
                  (day) => OperatingDay(
                    dayOfWeek: day.day,
                    isClosed: day.isClosed,
                    is24Hours: day.is24Hours,
                    opensAt: day.isClosed || day.is24Hours
                        ? null
                        : _format(day.open),
                    closesAt: day.isClosed || day.is24Hours
                        ? null
                        : _format(day.close),
                  ),
                )
                .toList(),
          );
      final destination = await ref
          .read(onboardingCoordinatorProvider)
          .resolve();
      if (!mounted) return;
      goToDestination(context, destination);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = 'Unable to save operating hours. Please try again.';
      });
    }
  }

  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            IconButton(
              tooltip: 'Back',
              onPressed: () => context.goNamed(AppRoutes.gymAmenitiesName),
              icon: const Icon(Icons.arrow_back),
            ),
            Expanded(
              child: Text(
                'Step 5 of 7',
                textAlign: TextAlign.center,
                style: AppTextStyles.bodyMedium,
              ),
            ),
            const SizedBox(width: 48),
          ],
        ),
        const SizedBox(height: 8),
        const LinearProgressIndicator(value: 5 / 7, minHeight: 3),
        const SizedBox(height: 24),
        Text('Operating Hours', style: AppTextStyles.headingLarge),
        const SizedBox(height: 8),
        Text(
          'Set when members can access your gym.',
          style: AppTextStyles.bodyMedium,
        ),
        const SizedBox(height: 24),
        if (_loading)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(36),
              child: CircularProgressIndicator(),
            ),
          )
        else if (_error != null && _days.every((day) => day.isClosed)) ...[
          Text(
            _error!,
            style: AppTextStyles.bodyMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: _load, child: const Text('Retry')),
        ] else ...[
          const SizedBox(height: 2),
          ..._days.map(
            (day) => _OperatingDayCard(
              day: day,
              name: _names[day.day],
              onChanged: () => setState(() {}),
              onPick: (opening) => _pickTime(day, opening),
            ),
          ),
          const SizedBox(height: 4),
          Wrap(
            spacing: 8,
            children: [
              TextButton(
                onPressed: _saving ? null : () => _copy(false),
                child: const Text('Apply Monday to Weekdays'),
              ),
              TextButton(
                onPressed: _saving ? null : () => _copy(true),
                child: const Text('Apply Monday to All Days'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            height: 48,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                const Icon(Icons.add, size: 18, color: AppColors.textSecondary),
                const SizedBox(width: 8),
                Text(
                  'Special Hours (Optional)',
                  style: AppTextStyles.bodySmall,
                ),
                const Spacer(),
                Text('Coming soon', style: AppTextStyles.caption),
              ],
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_error!, style: TextStyle(color: AppColors.error)),
            ),
          const SizedBox(height: 28),
          AppPrimaryButton(
            key: const Key('gym-operating-hours-continue'),
            label: _saving ? 'Saving…' : 'Continue',
            onPressed: _saving ? null : _save,
          ),
        ],
      ],
    ),
  );
}

class _OperatingDayCard extends StatelessWidget {
  const _OperatingDayCard({
    required this.day,
    required this.name,
    required this.onChanged,
    required this.onPick,
  });
  final _OperatingDraft day;
  final String name;
  final VoidCallback onChanged;
  final ValueChanged<bool> onPick;
  String _time(BuildContext context, TimeOfDay? value) => value == null
      ? 'Select time'
      : MaterialLocalizations.of(context).formatTimeOfDay(value);
  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 10),
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      border: Border.all(
        color: day.isClosed
            ? AppColors.border
            : AppColors.primary.withValues(alpha: 0.28),
      ),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(child: Text(name, style: AppTextStyles.titleLarge)),
            Text(
              day.isClosed ? 'Closed' : 'Open',
              style: AppTextStyles.bodySmall,
            ),
            Switch(
              value: !day.isClosed,
              onChanged: (value) {
                day.isClosed = !value;
                onChanged();
              },
            ),
          ],
        ),
        AnimatedSize(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          child: !day.isClosed
              ? Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: day.is24Hours
                                ? null
                                : () => onPick(true),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.schedule, size: 16),
                                const SizedBox(width: 5),
                                Flexible(
                                  child: Text(
                                    _time(context, day.open),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 8),
                          child: Text('to'),
                        ),
                        Expanded(
                          child: OutlinedButton(
                            onPressed: day.is24Hours
                                ? null
                                : () => onPick(false),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.schedule, size: 16),
                                const SizedBox(width: 5),
                                Flexible(
                                  child: Text(
                                    _time(context, day.close),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    SizedBox(
                      height: 32,
                      child: Row(
                        children: [
                          Checkbox(
                            materialTapTargetSize:
                                MaterialTapTargetSize.shrinkWrap,
                            visualDensity: VisualDensity.compact,
                            value: day.is24Hours,
                            onChanged: (value) {
                              day.is24Hours = value ?? false;
                              onChanged();
                            },
                          ),
                          Text('Open 24 hours', style: AppTextStyles.bodySmall),
                        ],
                      ),
                    ),
                  ],
                )
              : const SizedBox.shrink(),
        ),
      ],
    ),
  );
}

class GymAmenitiesScreen extends ConsumerStatefulWidget {
  const GymAmenitiesScreen({super.key});

  @override
  ConsumerState<GymAmenitiesScreen> createState() => _GymAmenitiesScreenState();
}

class _GymAmenitiesScreenState extends ConsumerState<GymAmenitiesScreen> {
  List<GymAmenity> _amenities = const [];
  final _selected = <String>{};
  String? _gymId;
  String? _error;
  bool _loading = true;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final repository = ref.read(gymOwnerRepositoryProvider);
      final gym = await repository.getCurrentGym();
      final amenities = await repository.getAmenities();
      final selectedAmenities = await repository.getGymAmenities(gym.id);
      if (!mounted) return;
      setState(() {
        _gymId = gym.id;
        _amenities = amenities;
        _selected
          ..clear()
          ..addAll(selectedAmenities.map((amenity) => amenity.id));
        _loading = false;
        _error = null;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'We couldn’t load the amenities right now.';
      });
    }
  }

  Future<void> _save() async {
    if (_saving || _gymId == null) return;
    setState(() => _saving = true);
    try {
      await ref
          .read(gymOwnerRepositoryProvider)
          .updateGymAmenities(_gymId!, _selected);
      final destination = await ref
          .read(onboardingCoordinatorProvider)
          .resolve();
      if (!mounted) return;
      goToDestination(context, destination);
    } catch (_) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Unable to save amenities. Please try again.'),
        ),
      );
    }
  }

  IconData _iconFor(GymAmenity amenity) {
    final value = '${amenity.slug} ${amenity.name}'.toLowerCase();
    if (value.contains('pool')) return Icons.pool;
    if (value.contains('boxing')) return Icons.sports_mma;
    if (value.contains('yoga') || value.contains('pilates')) {
      return Icons.self_improvement;
    }
    if (value.contains('cardio')) return Icons.monitor_heart;
    if (value.contains('crossfit') || value.contains('functional')) {
      return Icons.fitness_center;
    }
    if (value.contains('shower')) return Icons.shower;
    if (value.contains('locker')) return Icons.inventory_2;
    if (value.contains('parking')) return Icons.local_parking;
    if (value.contains('wifi')) return Icons.wifi;
    if (value.contains('personal')) return Icons.person;
    if (value.contains('group')) return Icons.groups;
    if (value.contains('sauna') || value.contains('steam')) return Icons.spa;
    return Icons.fitness_center;
  }

  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            IconButton(
              tooltip: 'Back',
              onPressed: () => context.canPop()
                  ? context.pop()
                  : context.goNamed(AppRoutes.gymBusinessDetailsName),
              icon: const Icon(Icons.arrow_back),
            ),
            Expanded(
              child: Text(
                'Step 4 of 7',
                textAlign: TextAlign.center,
                style: AppTextStyles.bodyMedium,
              ),
            ),
            const SizedBox(width: 48),
          ],
        ),
        const SizedBox(height: 8),
        const LinearProgressIndicator(value: 4 / 7, minHeight: 3),
        const SizedBox(height: 24),
        Text('Amenities', style: AppTextStyles.headingLarge),
        const SizedBox(height: 8),
        Text(
          'Select everything available at your gym.',
          style: AppTextStyles.bodyMedium,
        ),
        const SizedBox(height: 28),
        if (_loading)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(36),
              child: CircularProgressIndicator(),
            ),
          )
        else if (_error != null)
          Column(
            children: [
              Text(
                _error!,
                style: AppTextStyles.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              OutlinedButton(onPressed: _load, child: const Text('Retry')),
            ],
          )
        else ...[
          Text('Available Amenities', style: AppTextStyles.titleLarge),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              final width = (constraints.maxWidth - 12) / 2;
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: _amenities
                    .map(
                      (amenity) => SizedBox(
                        width: width,
                        child: _AmenitySelectionCard(
                          key: ValueKey('amenity-card-${amenity.id}'),
                          amenity: amenity,
                          icon: _iconFor(amenity),
                          selected: _selected.contains(amenity.id),
                          onTap: () => setState(() {
                            if (!_selected.add(amenity.id))
                              _selected.remove(amenity.id);
                          }),
                        ),
                      ),
                    )
                    .toList(),
              );
            },
          ),
          const SizedBox(height: 28),
          AppPrimaryButton(
            key: const Key('gym-amenities-continue'),
            label: 'Continue',
            onPressed: _saving ? null : _save,
          ),
        ],
      ],
    ),
  );
}

class _AmenitySelectionCard extends StatelessWidget {
  const _AmenitySelectionCard({
    super.key,
    required this.amenity,
    required this.icon,
    required this.selected,
    required this.onTap,
  });
  final GymAmenity amenity;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    selected: selected,
    label: '${amenity.name}, ${selected ? 'selected' : 'not selected'}',
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        height: 72,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(
          color: selected
              ? AppColors.primary.withValues(alpha: 0.12)
              : AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(
            color: selected ? AppColors.primary : AppColors.border,
          ),
        ),
        child: Row(
          children: [
            Icon(
              icon,
              color: selected ? AppColors.primary : AppColors.textMuted,
              size: 22,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                amenity.name,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: AppTextStyles.bodyMedium.copyWith(fontSize: 13),
              ),
            ),
            if (selected)
              const Icon(
                Icons.check_circle,
                color: AppColors.primary,
                size: 19,
              ),
          ],
        ),
      ),
    ),
  );
}

class GymBusinessDetailsScreen extends ConsumerStatefulWidget {
  const GymBusinessDetailsScreen({super.key});
  @override
  ConsumerState<GymBusinessDetailsScreen> createState() =>
      _GymBusinessDetailsScreenState();
}

class _GymBusinessDetailsScreenState
    extends ConsumerState<GymBusinessDetailsScreen> {
  final _legal = TextEditingController();
  final _registration = TextEditingController();
  final _tax = TextEditingController();
  final _contact = TextEditingController();
  final _phone = TextEditingController();
  final _businessPhoneFocus = FocusNode();
  String? _gymId;
  String? _type;
  bool _loading = true;
  bool _saving = false;
  String? _error;
  String? _phoneError;
  static const _types = <MapEntry<String, String>>[
    MapEntry('sole_proprietorship', 'Sole Proprietorship'),
    MapEntry('partnership', 'Partnership'),
    MapEntry('limited_company', 'Limited Company'),
    MapEntry('non_profit', 'Non-profit'),
    MapEntry('other', 'Other'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final gym = await ref.read(gymOwnerRepositoryProvider).getCurrentGym();
      if (!mounted) return;
      setState(() {
        _gymId = gym.id;
        _legal.text = gym.legalBusinessName ?? '';
        _type = gym.businessType;
        _registration.text = gym.registrationNumber ?? '';
        _tax.text = gym.taxNumber ?? '';
        _contact.text = gym.contactPersonName ?? '';
        _phone.text = gym.contactPersonPhone == null
            ? ''
            : KenyaPhoneFormatter.formatForField(gym.contactPersonPhone!);
        _loading = false;
      });
    } catch (_) {
      if (mounted)
        setState(() {
          _loading = false;
          _error = 'Unable to load business details.';
        });
    }
  }

  Future<void> _chooseType() async {
    final result = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: AppColors.surfaceElevated,
      isScrollControlled: true,
      builder: (context) =>
          SafeArea(child: _BusinessTypeSheet(selected: _type)),
    );
    if (result != null && mounted) setState(() => _type = result);
  }

  Future<void> _save() async {
    if (_gymId == null) {
      setState(() => _error = 'Your gym could not be found.');
      return;
    }
    if (_type == null) {
      setState(() => _error = 'Select a business type.');
      return;
    }
    if (_contact.text.trim().length < 2) {
      setState(() => _error = 'Enter the contact person name.');
      return;
    }
    if (!KenyaPhoneFormatter.isValid(_phone.text)) {
      setState(() => _phoneError = 'Enter a valid Kenyan mobile number.');
      return;
    }
    if (_legal.text.trim().length < 2) {
      setState(() => _error = 'Complete the required business fields.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref
          .read(gymOwnerRepositoryProvider)
          .updateGymBusinessDetails(
            _gymId!,
            GymBusinessDetails(
              legalBusinessName: _legal.text.trim(),
              businessType: _type!,
              registrationNumber: _registration.text.trim().isEmpty
                  ? null
                  : _registration.text.trim(),
              taxNumber: _tax.text.trim().isEmpty ? null : _tax.text.trim(),
              contactPersonName: _contact.text.trim(),
              contactPersonPhone: KenyaPhoneFormatter.toInternational(
                _phone.text,
              ),
            ),
          );
      final destination = await ref
          .read(onboardingCoordinatorProvider)
          .resolve();
      if (mounted) goToDestination(context, destination);
    } on DioException catch (error) {
      if (mounted) setState(() => _error = _apiMessage(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  void dispose() {
    for (final c in [_legal, _registration, _tax, _contact, _phone]) {
      c.dispose();
    }
    _businessPhoneFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    child: _loading
        ? const Center(
            child: CircularProgressIndicator(color: AppColors.primary),
          )
        : Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () => context.goNamed(AppRoutes.gymLocationName),
                  ),
                  Expanded(
                    child: Text(
                      'Step 3 of ${GymOwnerProgress.ordered.length}',
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
              const LinearProgressIndicator(
                value: 3 / 7,
                minHeight: 4,
                backgroundColor: AppColors.border,
                valueColor: AlwaysStoppedAnimation(AppColors.primary),
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Business Details',
                style: AppTextStyles.headingLarge.copyWith(
                  color: AppColors.white,
                ),
              ),
              const SizedBox(height: 8),
              const Text('Tell members who operates your gym.'),
              const SizedBox(height: 28),
              const Text(
                'Business Information',
                style: AppTextStyles.labelLarge,
              ),
              const SizedBox(height: 14),
              _selector(),
              _businessField(
                _legal,
                'Legal Business Name',
                'e.g. Hunters Fitness Limited',
                TextInputAction.next,
              ),
              const SizedBox(height: 28),
              const Text('Registration', style: AppTextStyles.labelLarge),
              const SizedBox(height: 14),
              _businessField(
                _registration,
                'Business Registration Number',
                'Optional',
                TextInputAction.next,
              ),
              _businessField(
                _tax,
                'KRA PIN / Tax Number',
                'Optional',
                TextInputAction.next,
              ),
              const SizedBox(height: 28),
              const Text('Primary Contact', style: AppTextStyles.labelLarge),
              const SizedBox(height: 14),
              _businessField(
                _contact,
                'Contact Person Name',
                'Full name',
                TextInputAction.next,
              ),
              const Padding(
                padding: EdgeInsets.only(bottom: AppSpacing.xs),
                child: Text('Phone Number', style: AppTextStyles.labelMedium),
              ),
              KenyaPhoneField(
                key: const Key('business-phone-field'),
                fieldKey: const Key('business-phone-input'),
                compact: true,
                controller: _phone,
                focusNode: _businessPhoneFocus,
                errorText: _phoneError,
                onChanged: (_) => setState(() => _phoneError = null),
              ),
              if (_error != null)
                Text(
                  _error!,
                  key: const Key('business-details-error'),
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.error,
                  ),
                ),
              const SizedBox(height: 28),
              AppPrimaryButton(
                key: const Key('business-details-continue'),
                label: _saving ? 'Saving...' : 'Continue',
                onPressed: _saving ? null : _save,
              ),
            ],
          ),
  );
  Widget _selector() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    mainAxisSize: MainAxisSize.min,
    children: [
      const Padding(
        padding: EdgeInsets.only(bottom: AppSpacing.xs),
        child: Text('Business Type', style: AppTextStyles.labelMedium),
      ),
      InkWell(
        key: const Key('business-type-selector'),
        onTap: _saving ? null : _chooseType,
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: Container(
          width: double.infinity,
          height: 60,
          padding: const EdgeInsets.symmetric(horizontal: 20),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(color: AppColors.border),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  _types
                      .firstWhere(
                        (e) => e.key == _type,
                        orElse: () =>
                            const MapEntry('', 'Select business type'),
                      )
                      .value,
                ),
              ),
              const Icon(Icons.expand_more),
            ],
          ),
        ),
      ),
      const SizedBox(height: 12),
    ],
  );
  Widget _businessField(
    TextEditingController c,
    String label,
    String hint,
    TextInputAction action,
  ) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.xs),
          child: Text(label, style: AppTextStyles.labelMedium),
        ),
        TextField(
          controller: c,
          textInputAction: action,
          onTapOutside: (_) => FocusScope.of(context).unfocus(),
          decoration: InputDecoration(
            hintText: hint,
            filled: true,
            fillColor: AppColors.surface,
            isDense: true,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 20,
              vertical: 17,
            ),
          ),
        ),
      ],
    ),
  );
}

class _BusinessTypeSheet extends StatefulWidget {
  const _BusinessTypeSheet({required this.selected});
  final String? selected;
  @override
  State<_BusinessTypeSheet> createState() => _BusinessTypeSheetState();
}

class _BusinessTypeSheetState extends State<_BusinessTypeSheet> {
  final _search = TextEditingController();
  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final query = _search.text.toLowerCase();
    final values = GymBusinessDetailsScreenStateTypes.values.where(
      (e) => e.value.toLowerCase().contains(query),
    );
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _search,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Search business types',
            ),
          ),
          Flexible(
            child: ListView(
              shrinkWrap: true,
              children: values
                  .map(
                    (e) => ListTile(
                      title: Text(e.value),
                      trailing: e.key == widget.selected
                          ? const Icon(Icons.check, color: AppColors.primary)
                          : null,
                      onTap: () => Navigator.pop(context, e.key),
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
      ),
    );
  }
}

class GymBusinessDetailsScreenStateTypes {
  static const values = <MapEntry<String, String>>[
    MapEntry('sole_proprietorship', 'Sole Proprietorship'),
    MapEntry('partnership', 'Partnership'),
    MapEntry('limited_company', 'Limited Company'),
    MapEntry('non_profit', 'Non-profit'),
    MapEntry('other', 'Other'),
  ];
}

class GymLocationScreen extends ConsumerStatefulWidget {
  const GymLocationScreen({super.key});
  @override
  ConsumerState<GymLocationScreen> createState() => _GymLocationScreenState();
}

class _GymLocationScreenState extends ConsumerState<GymLocationScreen> {
  final _address = TextEditingController();
  final _neighbourhood = TextEditingController();
  final _county = TextEditingController();
  String? _gymId;
  double _latitude = -1.286389;
  double _longitude = 36.817223;
  bool _loading = true;
  bool _saving = false;
  String? _error;
  final GymLocationService _locationService = DeviceGymLocationService();
  GoogleMapController? _mapController;
  bool _locating = false;
  String? _locationError;
  String? _geocodingWarning;
  bool _reverseGeocoding = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final gym = await ref.read(gymOwnerRepositoryProvider).getCurrentGym();
      if (!mounted) return;
      final location = gym.location;
      setState(() {
        _gymId = gym.id;
        if (location != null) {
          _latitude = location.latitude;
          _longitude = location.longitude;
          _address.text = location.addressLine;
          _neighbourhood.text = location.neighbourhood;
          _county.text = location.city;
        }
        _loading = false;
      });
    } catch (_) {
      if (mounted)
        setState(() {
          _loading = false;
          _error = 'Unable to load your gym location.';
        });
    }
  }

  Future<void> _useCurrentLocation() async {
    setState(() {
      _locating = true;
      _locationError = null;
    });
    try {
      if (!await _locationService.isServiceEnabled()) {
        throw const _LocationMessage('Location services are disabled.');
      }
      var permission = await _locationService.checkPermission();
      if (permission == LocationPermissionState.denied) {
        permission = await _locationService.requestPermission();
      }
      if (permission == LocationPermissionState.deniedForever) {
        throw const _LocationMessage(
          'Location permission is disabled. Open settings to enable it.',
        );
      }
      if (permission == LocationPermissionState.denied) {
        throw const _LocationMessage(
          'Location permission was denied. You can select a point on the map.',
        );
      }
      final position = await _locationService.getCurrentPosition();
      await _selectPosition(position.latitude, position.longitude);
    } catch (error) {
      if (mounted)
        setState(
          () => _locationError = error is _LocationMessage
              ? error.message
              : 'Current location is unavailable.',
        );
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  Future<void> _selectPosition(double latitude, double longitude) async {
    if (!latitude.isFinite || !longitude.isFinite) return;
    setState(() {
      _latitude = latitude;
      _longitude = longitude;
    });
    await _mapController?.animateCamera(
      CameraUpdate.newLatLng(LatLng(latitude, longitude)),
    );
    if (mounted) setState(() => _reverseGeocoding = true);
    try {
      final address = await _locationService.reverseGeocode(
        latitude: latitude,
        longitude: longitude,
      );
      if (!mounted || address == null) return;
      setState(() {
        if (_address.text.trim().isEmpty) _address.text = address.addressLine;
        if (_neighbourhood.text.trim().isEmpty)
          _neighbourhood.text = address.neighbourhood;
        if (_county.text.trim().isEmpty) _county.text = address.city;
      });
    } catch (_) {
      if (mounted)
        setState(
          () => _geocodingWarning =
              'Address lookup unavailable. Enter the details manually.',
        );
    } finally {
      if (mounted) setState(() => _reverseGeocoding = false);
    }
  }

  bool get _canSave =>
      !_saving &&
      _gymId != null &&
      _address.text.trim().length >= 3 &&
      _county.text.trim().length >= 2 &&
      _latitude.isFinite &&
      _longitude.isFinite;

  Future<void> _save() async {
    if (_gymId == null) {
      setState(() => _error = 'Your gym could not be found.');
      return;
    }
    if (_address.text.trim().length < 3) {
      setState(() => _error = 'Enter a valid gym address.');
      return;
    }
    if (_county.text.trim().length < 2) {
      setState(() => _error = 'Enter a county or city.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref
          .read(gymOwnerRepositoryProvider)
          .updateGymLocation(
            _gymId!,
            GymLocation(
              latitude: _latitude,
              longitude: _longitude,
              addressLine: _address.text.trim(),
              neighbourhood: _neighbourhood.text.trim(),
              city: _county.text.trim(),
              countryCode: 'KE',
            ),
          );
      final destination = await ref
          .read(onboardingCoordinatorProvider)
          .resolve();
      if (mounted) goToDestination(context, destination);
    } on DioException catch (error) {
      if (mounted) setState(() => _error = _apiMessage(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  void dispose() {
    _address.dispose();
    _neighbourhood.dispose();
    _county.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    child: _loading
        ? const Center(
            child: CircularProgressIndicator(color: AppColors.primary),
          )
        : Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () => context.canPop()
                        ? context.pop()
                        : context.goNamed(AppRoutes.gymRegistrationName),
                  ),
                  Expanded(
                    child: Text(
                      'Step 2 of ${GymOwnerProgress.ordered.length}',
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.pill),
                  child: const LinearProgressIndicator(
                    value: 2 / 7,
                    minHeight: 4,
                    backgroundColor: AppColors.border,
                    valueColor: AlwaysStoppedAnimation(AppColors.primary),
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Set Gym Location',
                style: AppTextStyles.headingLarge.copyWith(
                  color: AppColors.white,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              const Text('Help members find your gym easily.'),
              const SizedBox(height: AppSpacing.sm),
              SizedBox(
                height: 270,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  child: GoogleMap(
                    initialCameraPosition: CameraPosition(
                      target: LatLng(_latitude, _longitude),
                      zoom: 14,
                    ),
                    myLocationButtonEnabled: false,
                    zoomControlsEnabled: false,
                    markers: {
                      Marker(
                        markerId: const MarkerId('gym-location'),
                        position: LatLng(_latitude, _longitude),
                        draggable: true,
                        onDragEnd: (value) =>
                            _selectPosition(value.latitude, value.longitude),
                      ),
                    },
                    onMapCreated: (controller) => _mapController = controller,
                    onTap: (value) =>
                        _selectPosition(value.latitude, value.longitude),
                  ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(top: AppSpacing.xs),
                child: Text(
                  'Drag the map to position your gym',
                  style: AppTextStyles.caption,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              OutlinedButton.icon(
                onPressed: _locating ? null : _useCurrentLocation,
                icon: const Icon(Icons.my_location),
                label: Text(
                  _locating ? 'Finding location...' : 'Use my current location',
                ),
              ),
              if (_reverseGeocoding)
                const Padding(
                  padding: EdgeInsets.only(top: AppSpacing.xs),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: AppColors.primary,
                        ),
                      ),
                      SizedBox(width: AppSpacing.xs),
                      Text('Updating address...'),
                    ],
                  ),
                ),
              if (_locationError != null)
                Text(
                  _locationError!,
                  key: const Key('location-permission-error'),
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.error,
                  ),
                ),
              if (_geocodingWarning != null)
                Text(
                  _geocodingWarning!,
                  key: const Key('location-geocoding-warning'),
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textMuted,
                  ),
                ),
              const SizedBox(height: AppSpacing.sm),
              _locationField(
                _address,
                'Address',
                hint: 'Enter street, building or landmark',
                key: 'location-address',
                action: TextInputAction.next,
              ),
              _locationField(
                _neighbourhood,
                'Neighbourhood',
                hint: 'e.g. Kasarani',
                key: 'location-neighbourhood',
                action: TextInputAction.next,
              ),
              _locationField(
                _county,
                'City / Town',
                hint: 'e.g. Nairobi',
                key: 'location-county',
                action: TextInputAction.done,
              ),
              if (_error != null)
                Text(
                  _error!,
                  key: const Key('location-error'),
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.error,
                  ),
                ),
              const SizedBox(height: AppSpacing.md),
              AppPrimaryButton(
                key: const Key('location-continue'),
                label: _saving ? 'Saving...' : 'Continue',
                onPressed: _canSave ? _save : null,
              ),
            ],
          ),
  );

  Widget _locationField(
    TextEditingController controller,
    String label, {
    required String key,
    String? hint,
    TextInputAction? action,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: TextField(
      key: Key(key),
      controller: controller,
      textInputAction: action,
      onChanged: (_) => setState(() {}),
      onTapOutside: (_) => FocusScope.of(context).unfocus(),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        filled: true,
        fillColor: AppColors.surface,
        isDense: true,
      ),
    ),
  );
}

class _LocationMessage implements Exception {
  const _LocationMessage(this.message);
  final String message;
}

class _LocationMapPreview extends StatelessWidget {
  const _LocationMapPreview({
    required this.latitude,
    required this.longitude,
    required this.onTap,
  });
  final double latitude;
  final double longitude;
  final void Function(double latitude, double longitude) onTap;
  @override
  Widget build(BuildContext context) => GestureDetector(
    key: const Key('location-map'),
    onTapDown: (details) {
      final box = context.findRenderObject()! as RenderBox;
      final point = details.localPosition;
      onTap(
        -4 + (1 - point.dy / box.size.height) * 8,
        33 + point.dx / box.size.width * 9,
      );
    },
    child: Container(
      height: 190,
      width: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0xFF202A25),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.border),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          const Icon(Icons.map_outlined, size: 82, color: Color(0xFF3E5148)),
          const Icon(Icons.location_pin, size: 46, color: AppColors.primary),
        ],
      ),
    ),
  );
}

class SimpleOnboardingPlaceholder extends StatelessWidget {
  const SimpleOnboardingPlaceholder({
    required this.title,
    required this.message,
    required this.actionLabel,
    required this.action,
    super.key,
  });
  final String title;
  final String message;
  final String actionLabel;
  final VoidCallback action;
  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    child: Column(
      children: [
        const SwetoLogo(width: 120),
        const SizedBox(height: AppSpacing.xl),
        Text(
          title,
          textAlign: TextAlign.center,
          style: AppTextStyles.headingLarge.copyWith(color: AppColors.white),
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          message,
          textAlign: TextAlign.center,
          style: AppTextStyles.bodyMedium,
        ),
        const SizedBox(height: AppSpacing.xl),
        AppPrimaryButton(
          key: const Key('onboarding-placeholder-action'),
          label: actionLabel,
          onPressed: action,
        ),
      ],
    ),
  );
}

class UnsupportedOnboardingScreen extends ConsumerStatefulWidget {
  const UnsupportedOnboardingScreen({super.key});

  @override
  ConsumerState<UnsupportedOnboardingScreen> createState() =>
      _UnsupportedOnboardingScreenState();
}

class _UnsupportedOnboardingScreenState
    extends ConsumerState<UnsupportedOnboardingScreen> {
  bool _loggingOut = false;

  Future<void> _logout() async {
    if (_loggingOut) return;
    setState(() => _loggingOut = true);
    // The session controller revokes and clears the session; the router then
    // returns the user to sign-in.
    await ref.read(sessionControllerProvider.notifier).logout();
  }

  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    showAccountMenu: false,
    child: Column(
      children: [
        const KeyedSubtree(
          key: Key('unsupported-onboarding-screen'),
          child: SwetoLogo(width: 120),
        ),
        const SizedBox(height: AppSpacing.xl),
        Text(
          'Continue setting up your gym',
          textAlign: TextAlign.center,
          style: AppTextStyles.headingLarge.copyWith(color: AppColors.white),
        ),
        const SizedBox(height: AppSpacing.md),
        const Text(
          "We couldn't determine the next step of your gym setup.\nPlease try again.",
          textAlign: TextAlign.center,
          style: AppTextStyles.bodyMedium,
        ),
        const SizedBox(height: AppSpacing.xl),
        AppPrimaryButton(
          key: const Key('unsupported-onboarding-retry'),
          label: 'Retry',
          onPressed: () => context.goNamed(AppRoutes.splashName),
        ),
        TextButton(
          key: const Key('unsupported-onboarding-logout'),
          onPressed: _loggingOut ? null : _logout,
          child: Text(_loggingOut ? 'Signing out...' : 'Sign out'),
        ),
      ],
    ),
  );
}

String _verificationLabel(String type) => switch (type) {
  'business_registration' => 'Business Registration Certificate',
  'owner_identification' => 'Owner Identification',
  'tax_certificate' => 'KRA PIN Certificate',
  'operating_license' => 'County Business Permit',
  'proof_of_address' => 'Proof of Address',
  _ => type.replaceAll('_', ' '),
};

class _VerificationStatusCard extends StatelessWidget {
  const _VerificationStatusCard({
    required this.icon,
    required this.color,
    required this.title,
    required this.message,
  });
  final IconData icon;
  final Color color;
  final String title;
  final String message;
  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 16),
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      border: Border.all(color: color.withValues(alpha: .5)),
    ),
    child: Row(
      children: [
        Icon(icon, color: color, size: 26),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: AppTextStyles.labelMedium),
              const SizedBox(height: 4),
              Text(message, style: AppTextStyles.bodySmall),
            ],
          ),
        ),
      ],
    ),
  );
}

class _VerificationDocumentCard extends StatelessWidget {
  const _VerificationDocumentCard({
    required this.type,
    required this.document,
    required this.editable,
    this.onAction,
  });
  final String type;
  final VerificationDocument? document;
  final bool editable;
  final VoidCallback? onAction;
  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 10),
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      border: Border.all(
        color: document != null
            ? AppColors.secondary.withValues(alpha: .45)
            : AppColors.border,
      ),
    ),
    child: Row(
      children: [
        Icon(
          document != null ? Icons.check_circle : Icons.description_outlined,
          color: document != null ? AppColors.secondary : AppColors.primary,
          size: 24,
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(_verificationLabel(type), style: AppTextStyles.labelMedium),
              const SizedBox(height: 3),
              Text(
                document?.name ?? 'Required · PDF, JPG or PNG',
                style: AppTextStyles.bodySmall,
              ),
              if (document != null)
                const Text(
                  'Uploaded successfully',
                  style: TextStyle(color: AppColors.secondary, fontSize: 11),
                ),
            ],
          ),
        ),
        if (editable)
          OutlinedButton(
            onPressed: onAction,
            child: Text(document == null ? 'Upload' : 'Replace'),
          ),
      ],
    ),
  );
}

class GymVerificationSetupScreen extends ConsumerStatefulWidget {
  const GymVerificationSetupScreen({super.key});
  @override
  ConsumerState<GymVerificationSetupScreen> createState() =>
      _GymVerificationSetupScreenState();
}

class _GymVerificationSetupScreenState
    extends ConsumerState<GymVerificationSetupScreen> {
  static const _supportedDocumentTypes = <String>[
    'business_registration',
    'owner_identification',
    'tax_certificate',
    'operating_license',
    'proof_of_address',
    'other',
  ];
  GymVerificationData? _data;
  String? _gymId;
  String? _error;
  bool _loading = true;
  bool _submitting = false;
  bool _uploading = false;
  String? _selectedType;
  String? _selectedFileName;
  XFile? _selectedFile;
  bool _pickingFile = false;
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final repo = ref.read(gymOwnerRepositoryProvider);
      final gym = await repo.getCurrentGym();
      final data = await repo.getGymVerification(gym.id);
      if (!mounted) return;
      setState(() {
        _gymId = gym.id;
        _data = data;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'We couldn’t load verification details.';
      });
    }
  }

  Future<void> _submit() async {
    if (_submitting ||
        _gymId == null ||
        _data == null ||
        _data!.missingTypes.isNotEmpty)
      return;
    final confirmed = await showSwetoConfirmationDialog(
      context,
      title: 'Submit gym for review?',
      message:
          'What happens next?\n\n'
          '• Documents are reviewed within 24–48 hours\n'
          '• Your gym remains accessible while under review\n'
          '• You’ll receive a notification once approved\n\n'
          'You can continue using limited features while SWETO reviews your documents.',
      confirmLabel: 'Submit',
    );
    if (!confirmed || !mounted) return;
    setState(() => _submitting = true);
    try {
      await ref.read(gymOwnerRepositoryProvider).submitGymVerification(_gymId!);
      final destination = await ref
          .read(onboardingCoordinatorProvider)
          .resolve();
      if (!mounted) return;
      goToDestination(context, destination);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = 'Unable to submit verification. Please try again.';
      });
    }
  }

  String _label(String type) => _verificationLabel(type);

  bool _isAdded(String type) =>
      _data?.documents.any((doc) => doc.type == type && doc.active) ?? false;

  Future<void> _chooseDocumentType() async {
    if (_data == null || _supportedDocumentTypes.every(_isAdded)) return;
    final result = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: AppColors.surfaceElevated,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => SafeArea(
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.all(18),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Select document type',
                    style: AppTextStyles.headingMedium,
                  ),
                ),
              ),
              ..._supportedDocumentTypes.map(
                (type) => ListTile(
                  enabled: !_isAdded(type),
                  leading: Icon(
                    Icons.description_outlined,
                    color: _isAdded(type)
                        ? AppColors.textMuted
                        : AppColors.primary,
                  ),
                  title: Text(_label(type)),
                  subtitle: Text(
                    _isAdded(type)
                        ? 'Added'
                        : (_data!.requiredTypes.contains(type)
                              ? 'Required'
                              : 'Optional'),
                  ),
                  trailing: _isAdded(type)
                      ? const Icon(Icons.check, color: AppColors.secondary)
                      : null,
                  onTap: _isAdded(type)
                      ? null
                      : () => Navigator.pop(context, type),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
    if (result != null && mounted)
      setState(() {
        _selectedType = result;
        _selectedFileName = null;
        _selectedFile = null;
      });
  }

  Future<void> _replaceDocument(VerificationDocument document) async {
    if (_uploading) return;
    setState(() {
      _selectedType = document.type;
      _selectedFile = null;
      _selectedFileName = null;
      _error = null;
    });
    await _chooseFile();
    if (mounted && _selectedFile != null) await _addDocument();
  }

  Future<void> _chooseFile() async {
    if (_pickingFile) return;
    if (_selectedType == null) {
      showSwetoSnackBar(
        context,
        message: 'Select a document type first.',
        type: SwetoSnackBarType.warning,
      );
      return;
    }
    setState(() => _pickingFile = true);
    try {
      final file = await openFile(
        acceptedTypeGroups: [
          XTypeGroup(
            label: 'Verification documents',
            extensions: ['pdf', 'jpg', 'jpeg', 'png'],
          ),
        ],
      );
      if (!mounted) return;
      if (file != null) {
        setState(() {
          _selectedFile = file;
          _selectedFileName = file.name;
          _error = null;
        });
      }
    } on PlatformException {
      if (mounted)
        setState(() => _error = 'Photo access is unavailable right now.');
    } catch (_) {
      if (mounted)
        setState(
          () => _error = 'We couldn’t choose that file. Please try again.',
        );
    } finally {
      if (mounted) setState(() => _pickingFile = false);
    }
  }

  String? _documentMimeType(String name) {
    final extension = name.split('.').last.toLowerCase();
    return switch (extension) {
      'jpg' || 'jpeg' => 'image/jpeg',
      'png' => 'image/png',
      'pdf' => 'application/pdf',
      _ => null,
    };
  }

  Future<void> _addDocument() async {
    final gymId = _gymId;
    final type = _selectedType;
    final file = _selectedFile;
    if (_uploading || gymId == null || type == null || file == null) return;
    final mimeType = _documentMimeType(file.name);
    if (mimeType == null) {
      setState(() => _error = 'Select a PDF, JPG, or PNG file.');
      return;
    }
    setState(() {
      _uploading = true;
      _error = null;
    });
    try {
      final bytes = await file.readAsBytes();
      if (bytes.isEmpty || bytes.length > 10 * 1024 * 1024) {
        throw const FormatException(
          'The selected file must be between 1 byte and 10 MB.',
        );
      }
      final repo = ref.read(gymOwnerRepositoryProvider);
      final intent = await repo.initiateVerificationUpload(
        gymId,
        type,
        filename: file.name,
        mimeType: mimeType,
        fileSizeBytes: bytes.length,
      );
      await repo.uploadVerificationFile(intent, bytes, mimeType: mimeType);
      await repo.completeVerificationUpload(gymId, type, intent.uploadId);
      final refreshed = await repo.getGymVerification(gymId);
      if (!mounted) return;
      setState(() {
        _data = refreshed;
        _selectedType = null;
        _selectedFile = null;
        _selectedFileName = null;
      });
    } catch (error) {
      if (kDebugMode) {
        // Log the type only: upload errors can carry presigned URLs.
        debugPrint('Verification document upload failed: ${error.runtimeType}');
      }
      if (mounted) {
        setState(() => _error = _friendlyVerificationUploadError(error));
      }
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  String _friendlyVerificationUploadError(Object error) {
    if (error is DioException) {
      final status = error.response?.statusCode;
      if (status == 401 || status == 403) {
        return 'Your session expired. Please sign in again.';
      }
      if (status == 413) return 'The selected file is too large.';
      if (status == 422)
        return 'This file cannot be uploaded. Check its type and size.';
      if (error.type == DioExceptionType.connectionTimeout ||
          error.type == DioExceptionType.sendTimeout ||
          error.type == DioExceptionType.receiveTimeout) {
        return 'Upload timed out. Please try again.';
      }
    }
    if (error is FormatException) return error.message;
    return 'Upload failed. Please try again.';
  }

  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    child: Column(
      children: [
        Row(
          children: [
            IconButton(
              key: const Key('verification-back'),
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.goNamed(AppRoutes.gymPricingName),
            ),
            const Expanded(
              child: Text('Step 7 of 7', textAlign: TextAlign.center),
            ),
            const SizedBox(width: 48),
          ],
        ),
        const LinearProgressIndicator(
          value: 1,
          minHeight: 4,
          backgroundColor: AppColors.border,
          valueColor: AlwaysStoppedAnimation(AppColors.primary),
        ),
        const SizedBox(height: 20),
        Text(
          'Verify Your Gym',
          key: const Key('gym-verification-title'),
          style: AppTextStyles.headingLarge.copyWith(color: AppColors.white),
        ),
        const SizedBox(height: AppSpacing.md),
        const Text(
          'Submit your business documents for review.',
          textAlign: TextAlign.center,
          style: AppTextStyles.bodyMedium,
        ),
        const SizedBox(height: 24),
        if (_loading)
          const CircularProgressIndicator()
        else if (_error != null && _data == null) ...[
          Text(_error!, style: AppTextStyles.bodyMedium),
          TextButton(onPressed: _load, child: const Text('Retry')),
        ] else if (_data != null) ...[
          if (_data!.status == 'approved')
            _VerificationStatusCard(
              icon: Icons.verified,
              color: AppColors.secondary,
              title: 'Gym Verified',
              message: 'Congratulations! Your gym is now visible to members.',
            )
          else if (_data!.status == 'pending')
            _VerificationStatusCard(
              icon: Icons.hourglass_top,
              color: AppColors.primary,
              title: 'Verification Under Review',
              message:
                  'Documents received successfully. We’re reviewing your submission.',
            )
          else if (_data!.status == 'rejected')
            _VerificationStatusCard(
              icon: Icons.info_outline,
              color: AppColors.error,
              title: 'Verification Needs Attention',
              message:
                  _data!.rejectionReason ??
                  'Please review and replace the requested documents.',
            ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: Text('Add Document', style: AppTextStyles.titleLarge),
          ),
          const SizedBox(height: 10),
          Text('Document type', style: AppTextStyles.labelMedium),
          const SizedBox(height: 6),
          InkWell(
            onTap: _chooseDocumentType,
            borderRadius: BorderRadius.circular(AppRadius.md),
            child: Container(
              height: 60,
              padding: const EdgeInsets.symmetric(horizontal: 20),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(AppRadius.md),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _selectedType == null
                          ? 'Select document type'
                          : _label(_selectedType!),
                    ),
                  ),
                  const Icon(Icons.expand_more),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerLeft,
            child: Text('Upload file', style: AppTextStyles.bodyMedium),
          ),
          const SizedBox(height: 6),
          Container(
            height: 76,
            width: double.infinity,
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(AppRadius.lg),
              border: Border.all(color: AppColors.border),
            ),
            child: InkWell(
              onTap: _pickingFile ? null : _chooseFile,
              borderRadius: BorderRadius.circular(AppRadius.lg),
              child: Row(
                children: [
                  const SizedBox(width: 16),
                  const Icon(
                    Icons.cloud_upload_outlined,
                    color: AppColors.primary,
                    size: 28,
                  ),
                  const SizedBox(width: 14),
                  Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _pickingFile
                            ? 'Choosing file…'
                            : (_selectedFileName ?? 'Choose file'),
                        style: AppTextStyles.labelMedium,
                      ),
                      Text(
                        'PDF, JPG or PNG · Max 10MB',
                        style: AppTextStyles.bodySmall,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed:
                  _selectedType != null && _selectedFile != null && !_uploading
                  ? _addDocument
                  : null,
              child: _uploading
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Add Document'),
            ),
          ),
          if (_data!.missingTypes.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                '${_data!.missingTypes.length} required document${_data!.missingTypes.length == 1 ? '' : 's'} remaining before submission.',
                style: AppTextStyles.caption,
              ),
            ),
          const SizedBox(height: 20),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Uploaded Documents (${_data!.documents.where((doc) => doc.active).length} of ${_data!.requiredTypes.length} required)',
              style: AppTextStyles.titleLarge,
            ),
          ),
          const SizedBox(height: 10),
          ..._data!.documents
              .where((doc) => doc.active)
              .map(
                (document) => _VerificationDocumentCard(
                  type: document.type,
                  document: document,
                  editable:
                      _data!.status != 'pending' && _data!.status != 'approved',
                  onAction: () => _replaceDocument(document),
                ),
              ),
          const SizedBox(height: 20),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Submission Checklist',
              style: AppTextStyles.titleLarge,
            ),
          ),
          const SizedBox(height: 8),
          ...[
            'Basic Information',
            'Gym Location',
            'Business Details',
            'Amenities',
            'Operating Hours',
            'Membership Pricing',
          ].map(
            (label) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  const Icon(
                    Icons.check_circle,
                    color: AppColors.secondary,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(label, style: AppTextStyles.bodySmall),
                ],
              ),
            ),
          ),
          ..._data!.requiredTypes.map((type) {
            final complete = !_data!.missingTypes.contains(type);
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Icon(
                    complete
                        ? Icons.check_circle
                        : Icons.radio_button_unchecked,
                    color: complete ? AppColors.secondary : AppColors.textMuted,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _verificationLabel(type),
                    style: AppTextStyles.bodySmall,
                  ),
                ],
              ),
            );
          }),
          if (_data!.rejectionReason != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(
                'Needs attention: ${_data!.rejectionReason}',
                style: TextStyle(color: AppColors.error),
              ),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_error!, style: TextStyle(color: AppColors.error)),
            ),
        ],
        const SizedBox(height: 24),
        AppPrimaryButton(
          key: const Key('gym-verification-continue'),
          label: _submitting ? 'Submitting…' : 'Submit for Review',
          onPressed:
              _data != null &&
                  _data!.missingTypes.isEmpty &&
                  !_submitting &&
                  _data!.status != 'pending' &&
                  _data!.status != 'approved'
              ? _submit
              : null,
        ),
      ],
    ),
  );
}

class VerificationPendingScreen extends ConsumerStatefulWidget {
  const VerificationPendingScreen({super.key});

  @override
  ConsumerState<VerificationPendingScreen> createState() =>
      _VerificationPendingScreenState();
}

class _VerificationPendingScreenState
    extends ConsumerState<VerificationPendingScreen> {
  bool _loggingOut = false;

  Future<void> _logout() async {
    if (_loggingOut) return;
    setState(() => _loggingOut = true);
    // The session controller revokes and clears the session; the router then
    // returns the user to sign-in.
    await ref.read(sessionControllerProvider.notifier).logout();
  }

  @override
  Widget build(BuildContext context) => _OnboardingScaffold(
    showAccountMenu: false,
    child: Column(
      children: [
        const KeyedSubtree(
          key: Key('verification-pending-screen'),
          child: SwetoLogo(width: 120),
        ),
        const SizedBox(height: AppSpacing.xl),
        Text(
          'Verification pending',
          textAlign: TextAlign.center,
          style: AppTextStyles.headingLarge.copyWith(color: AppColors.white),
        ),
        const SizedBox(height: AppSpacing.md),
        const Text(
          'Your gym is being reviewed. Limited access is available while you wait.',
          textAlign: TextAlign.center,
          style: AppTextStyles.bodyMedium,
        ),
        const SizedBox(height: AppSpacing.xl),
        AppPrimaryButton(
          key: const Key('verification-pending-retry'),
          label: 'Retry',
          onPressed: () => context.goNamed(AppRoutes.splashName),
        ),
        const SizedBox(height: AppSpacing.sm),
        TextButton(
          key: const Key('verification-pending-logout'),
          onPressed: _loggingOut ? null : _logout,
          child: Text(_loggingOut ? 'Signing out...' : 'Log out'),
        ),
      ],
    ),
  );
}

class _OnboardingScaffold extends StatelessWidget {
  const _OnboardingScaffold({
    required this.child,
    this.showAccountMenu = true,
  });
  final Widget child;

  /// Shows a top-right menu with "Log out" so an owner is never stuck in
  /// onboarding. Screens with their own logout button turn it off.
  final bool showAccountMenu;

  @override
  Widget build(BuildContext context) {
    final page = _buildPage(context);
    if (!showAccountMenu) return page;
    return Stack(
      children: [
        page,
        const Positioned(
          top: 0,
          right: 0,
          child: SafeArea(child: _OnboardingAccountMenu()),
        ),
      ],
    );
  }

  Widget _buildPage(BuildContext context) {
    final bodyPadding = EdgeInsets.fromLTRB(
      AppSpacing.md,
      AppSpacing.lg,
      AppSpacing.md,
      MediaQuery.viewInsetsOf(context).bottom + AppSpacing.lg,
    );
    if (child is Column) {
      final column = child as Column;
      final children = column.children;
      final progressIndex = children.indexWhere(
        (item) => item is LinearProgressIndicator,
      );
      if (progressIndex >= 0) {
        final fixed = children.take(progressIndex + 1).toList();
        final scrollable = children.skip(progressIndex + 1).toList();
        return Scaffold(
          backgroundColor: AppColors.background,
          body: SafeArea(
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                AppSpacing.md,
                AppSpacing.lg,
                AppSpacing.md,
                0,
              ),
              child: Column(
                crossAxisAlignment: column.crossAxisAlignment,
                children: [
                  Column(
                    crossAxisAlignment: column.crossAxisAlignment,
                    children: fixed,
                  ),
                  Expanded(
                    child: GestureDetector(
                      onTap: () =>
                          FocusManager.instance.primaryFocus?.unfocus(),
                      child: SingleChildScrollView(
                        keyboardDismissBehavior:
                            ScrollViewKeyboardDismissBehavior.onDrag,
                        padding: bodyPadding.copyWith(top: 0),
                        child: Column(
                          crossAxisAlignment: column.crossAxisAlignment,
                          children: scrollable,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      }
    }
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: bodyPadding,
          child: child,
        ),
      ),
    );
  }
}

class _OnboardingAccountMenu extends ConsumerWidget {
  const _OnboardingAccountMenu();

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    final confirmed = await showSwetoConfirmationDialog(
      context,
      title: 'Log out of SWETO?',
      message:
          'Your gym setup is saved. Sign in again with your phone number to '
          'continue where you left off.',
      confirmLabel: 'Log out',
      type: SwetoDialogType.info,
    );
    if (!confirmed) return;
    // The session controller revokes and clears the session; the router then
    // returns the user to sign-in.
    await ref.read(sessionControllerProvider.notifier).logout();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Material(
      type: MaterialType.transparency,
      child: PopupMenuButton<String>(
        key: const Key('onboarding-account-menu'),
        tooltip: 'Account',
        icon: const Icon(
          Icons.more_vert_rounded,
          color: AppColors.textSecondary,
        ),
        color: AppColors.surfaceElevated,
        onSelected: (value) {
          if (value == 'logout') _logout(context, ref);
        },
        itemBuilder: (context) => const [
          PopupMenuItem<String>(
            key: Key('onboarding-account-menu-logout'),
            value: 'logout',
            child: Text('Log out'),
          ),
        ],
      ),
    );
  }
}

class _RoleCard extends StatelessWidget {
  const _RoleCard({
    required super.key,
    required this.title,
    required this.bullets,
    required this.selected,
    required this.onTap,
    required this.imageAsset,
    required this.accent,
    required this.icon,
    this.badge,
  });
  final String title;
  final List<String> bullets;
  final bool selected;
  final VoidCallback onTap;
  final String imageAsset;
  final Color accent;
  final IconData icon;
  final String? badge;
  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    splashColor: accent.withValues(alpha: 0.12),
    highlightColor: accent.withValues(alpha: 0.06),
    borderRadius: BorderRadius.circular(AppRadius.lg),
    child: Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(
          color: selected ? Colors.transparent : AppColors.border,
          width: 1,
        ),
        boxShadow: selected
            ? [BoxShadow(color: accent.withValues(alpha: 0.22), blurRadius: 18)]
            : null,
      ),
      foregroundDecoration: selected
          ? BoxDecoration(
              border: Border.all(color: accent, width: 2),
              borderRadius: BorderRadius.circular(AppRadius.lg),
            )
          : null,
      clipBehavior: Clip.antiAlias,
      child: Row(
        children: [
          SizedBox(
            width: 132,
            height: 190,
            child: Stack(
              fit: StackFit.expand,
              children: [
                Image.asset(imageAsset, fit: BoxFit.cover),
                DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        Colors.transparent,
                        AppColors.surface.withValues(alpha: 0.9),
                      ],
                      begin: Alignment.centerLeft,
                      end: Alignment.centerRight,
                    ),
                  ),
                ),
                Positioned(
                  right: AppSpacing.sm,
                  top: AppSpacing.sm,
                  child: CircleAvatar(
                    radius: 17,
                    backgroundColor: accent,
                    foregroundColor: AppColors.background,
                    child: Icon(icon, size: 19),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.sm,
                AppSpacing.md,
                AppSpacing.md,
                AppSpacing.md,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          style: AppTextStyles.titleLarge.copyWith(
                            color: AppColors.white,
                          ),
                        ),
                      ),
                      if (selected)
                        Icon(Icons.check_circle, color: accent, size: 22),
                    ],
                  ),
                  if (badge != null) ...[
                    const SizedBox(height: AppSpacing.xs),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: accent,
                        borderRadius: BorderRadius.circular(AppRadius.pill),
                      ),
                      child: Text(
                        badge!,
                        style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.background,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.xs),
                  ...bullets.map(
                    (bullet) => Padding(
                      padding: const EdgeInsets.only(top: 3),
                      child: Text(
                        '• $bullet',
                        style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class _MemberComingSoonSheet extends StatelessWidget {
  const _MemberComingSoonSheet();
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(AppSpacing.lg),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('Member access is coming soon', style: AppTextStyles.titleLarge),
        const SizedBox(height: AppSpacing.sm),
        const Text('Gym-owner onboarding is available in this MVP.'),
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Got it'),
        ),
      ],
    ),
  );
}

String _apiMessage(DioException error) {
  final apiError = error.error;
  return apiError is ApiException
      ? apiError.message
      : 'Something went wrong. Please try again.';
}
