import 'dart:async';

import 'package:geocoding/geocoding.dart' as geocoding;
import 'package:geolocator/geolocator.dart';

class GeoPosition {
  const GeoPosition(this.latitude, this.longitude);
  final double latitude;
  final double longitude;
}

enum LocationPermissionState { denied, deniedForever, whileInUse, always }

class ResolvedAddress {
  const ResolvedAddress({
    required this.addressLine,
    required this.neighbourhood,
    required this.city,
    required this.countryCode,
  });
  final String addressLine;
  final String neighbourhood;
  final String city;
  final String countryCode;
}

abstract interface class GymLocationService {
  Future<LocationPermissionState> checkPermission();
  Future<LocationPermissionState> requestPermission();
  Future<bool> isServiceEnabled();
  Future<GeoPosition> getCurrentPosition();
  Future<ResolvedAddress?> reverseGeocode({
    required double latitude,
    required double longitude,
  });
  Future<bool> openAppSettings();
  Future<bool> openLocationSettings();
}

const currentPositionTimeout = Duration(seconds: 10);

class DeviceGymLocationService implements GymLocationService {
  @override
  Future<LocationPermissionState> checkPermission() async {
    final permission = await GeolocatorPlatform.instance.checkPermission();
    return _permission(permission);
  }

  @override
  Future<LocationPermissionState> requestPermission() async =>
      _permission(await GeolocatorPlatform.instance.requestPermission());

  @override
  Future<bool> isServiceEnabled() =>
      GeolocatorPlatform.instance.isLocationServiceEnabled();

  @override
  Future<GeoPosition> getCurrentPosition() async {
    try {
      final value = await GeolocatorPlatform.instance.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: currentPositionTimeout,
        ),
      );
      return GeoPosition(value.latitude, value.longitude);
    } on TimeoutException {
      final last = await GeolocatorPlatform.instance.getLastKnownPosition();
      if (last == null) rethrow;
      return GeoPosition(last.latitude, last.longitude);
    }
  }

  @override
  Future<ResolvedAddress?> reverseGeocode({
    required double latitude,
    required double longitude,
  }) async {
    final places = await geocoding.Geocoding().placemarkFromCoordinates(
      latitude,
      longitude,
    );
    if (places.isEmpty) return null;
    final place = places.first;
    return ResolvedAddress(
      addressLine:
          [place.name, place.street, place.subThoroughfare, place.thoroughfare]
              .whereType<String>()
              .where((value) => value.trim().isNotEmpty)
              .toSet()
              .join(', '),
      neighbourhood: place.subLocality ?? place.locality ?? '',
      city: place.locality ?? place.administrativeArea ?? '',
      countryCode: place.isoCountryCode ?? 'KE',
    );
  }

  @override
  Future<bool> openAppSettings() =>
      GeolocatorPlatform.instance.openAppSettings();

  @override
  Future<bool> openLocationSettings() =>
      GeolocatorPlatform.instance.openLocationSettings();

  LocationPermissionState _permission(LocationPermission value) =>
      switch (value) {
        LocationPermission.denied => LocationPermissionState.denied,
        LocationPermission.deniedForever =>
          LocationPermissionState.deniedForever,
        LocationPermission.always => LocationPermissionState.always,
        LocationPermission.whileInUse => LocationPermissionState.whileInUse,
        LocationPermission.unableToDetermine => LocationPermissionState.denied,
      };
}
