import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';

/// Hands a check-in QR to the phone's share sheet (WhatsApp, Messages...).
typedef CheckInCodeSharer =
    Future<void> Function({
      required Uint8List png,
      required String fileName,
      required String text,
      Rect? origin,
    });

final checkInCodeSharerProvider = Provider<CheckInCodeSharer>(
  (ref) => ({required png, required fileName, required text, origin}) async {
    await SharePlus.instance.share(
      ShareParams(
        text: text,
        files: [XFile.fromData(png, mimeType: 'image/png')],
        fileNameOverrides: [fileName],
        sharePositionOrigin: origin,
      ),
    );
  },
);

/// What goes with the image, for a member who only gets the text.
String checkInCodeShareText(String memberName, CheckInCode code) =>
    '$memberName, your gym check-in code is ${code.code}. Show this QR or '
    'the code at the door.';

/// The QR as a PNG on white with a quiet margin, so it scans even when a
/// chat app shows it on a dark background.
Future<Uint8List> checkInQrPng(
  String data, {
  double size = 720,
  double margin = 60,
}) async {
  final total = size + margin * 2;
  final recorder = ui.PictureRecorder();
  final canvas = Canvas(recorder)
    ..drawRect(
      Rect.fromLTWH(0, 0, total, total),
      Paint()..color = const Color(0xFFFFFFFF),
    )
    ..translate(margin, margin);
  QrPainter(
    data: data,
    version: QrVersions.auto,
    gapless: true,
    eyeStyle: const QrEyeStyle(
      eyeShape: QrEyeShape.square,
      color: Color(0xFF000000),
    ),
    dataModuleStyle: const QrDataModuleStyle(
      dataModuleShape: QrDataModuleShape.square,
      color: Color(0xFF000000),
    ),
  ).paint(canvas, Size(size, size));
  final image = await recorder.endRecording().toImage(
    total.round(),
    total.round(),
  );
  final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
  image.dispose();
  return bytes!.buffer.asUint8List();
}

/// "achieng-otieno-check-in.png"
String checkInQrFileName(String memberName) {
  final slug = memberName
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');
  return '${slug.isEmpty ? 'member' : slug}-check-in.png';
}
