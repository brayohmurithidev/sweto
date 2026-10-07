# Google Maps setup

Enable Maps SDK for Android, Maps SDK for iOS, and device location services in
the Google Cloud project. Never commit API keys.

## Android

Add this line to the ignored `android/local.properties` file:

```properties
MAPS_API_KEY=your-android-key
```

The manifest reads it through a Gradle manifest placeholder. Restrict the key
to the Android application ID and signing certificate before release.

## iOS

Create an ignored `ios/Flutter/GoogleMaps.local.xcconfig` containing:

```text
GOOGLE_MAPS_API_KEY = your-ios-key
```

Include that file from the Runner build configuration in Xcode, or pass
`--dart-define`/an equivalent CI build setting that supplies the same
`GOOGLE_MAPS_API_KEY` build variable. Restrict the key to the iOS bundle ID.

After adding the packages, run `flutter pub get`, then `cd ios && pod install`.
Missing native pods or keys usually appear as a blank map or a plugin-channel
error during startup. Configure separate restricted release keys later.
