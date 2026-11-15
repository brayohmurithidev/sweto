import Flutter
import UIKit
import GoogleMaps

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  /// Google Maps aborts the whole app when a map is drawn without a key, so
  /// the app asks first (channel `sweto/maps`) and skips the map without one.
  private var mapsConfigured = false

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    if let key = Bundle.main.object(forInfoDictionaryKey: "GMSApiKey") as? String,
       !key.isEmpty, !key.hasPrefix("$(") {
      GMSServices.provideAPIKey(key)
      mapsConfigured = true
    }
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    guard let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "SwetoMaps") else {
      return
    }
    let channel = FlutterMethodChannel(
      name: "sweto/maps", binaryMessenger: registrar.messenger())
    let configured = mapsConfigured
    channel.setMethodCallHandler { call, result in
      if call.method == "isConfigured" {
        result(configured)
      } else {
        result(FlutterMethodNotImplemented)
      }
    }
  }
}
