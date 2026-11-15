import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/network/dio_provider.dart';
import 'package:sweto_app/features/admin/data/dio_admin_repository.dart';
import 'package:sweto_app/features/admin/domain/admin_repository.dart';
import 'package:url_launcher/url_launcher.dart';

final adminRepositoryProvider = Provider<AdminRepository>(
  (ref) => DioAdminRepository(ref.watch(dioProvider)),
);

/// Opens a link outside the app (a document in the browser or a viewer).
/// Returns false when nothing could open it.
typedef LinkOpener = Future<bool> Function(Uri uri);

final linkOpenerProvider = Provider<LinkOpener>(
  (ref) =>
      (uri) => launchUrl(uri, mode: LaunchMode.externalApplication),
);
