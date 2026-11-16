import 'dart:typed_data';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';

/// Hands an export to the phone's share sheet: save to Files, email it,
/// send it on WhatsApp or open it in Sheets.
typedef ExportSharer = Future<void> Function(ExportFile file, {Rect? origin});

final exportSharerProvider = Provider<ExportSharer>(
  (ref) => (file, {origin}) async {
    await SharePlus.instance.share(
      ShareParams(
        files: [
          XFile.fromData(
            Uint8List.fromList(file.bytes),
            mimeType: 'text/csv',
            name: file.fileName,
          ),
        ],
        fileNameOverrides: [file.fileName],
        sharePositionOrigin: origin,
      ),
    );
  },
);
