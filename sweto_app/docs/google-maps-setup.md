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
GMS_API_KEY = your-ios-key
```

`Debug.xcconfig` and `Release.xcconfig` include it when present, and
`Info.plist` passes it to the app as `GMSApiKey`. Restrict the key to the iOS
bundle ID.

After adding the packages, run `flutter pub get`, then `cd ios && pod install`.

## Without a key

Google Maps for iOS aborts the whole app when a map is drawn without a key.
The app therefore asks the native side first (method channel `sweto/maps`,
`isConfigured`). Without a key, the Location step shows a short note in place
of the map, and the address fields and "Use my current location" still work.
A fresh checkout, CI or a new machine has no key until you add the files above.

## Release builds checklist

Before building for TestFlight, the App Store or Play:

- `ios/Flutter/GoogleMaps.local.xcconfig` has `GMS_API_KEY` (iOS key,
  restricted to the bundle ID `com.fazilabs.swetoApp`);
- `android/local.properties` has `MAPS_API_KEY` (Android key, restricted to
  `com.fazilabs.sweto_app` and the release signing certificate);
- open the Location step once on the built app and see the map.

Use separate keys for release builds, not the ones on developer machines.
