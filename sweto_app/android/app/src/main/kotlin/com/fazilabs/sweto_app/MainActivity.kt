package com.fazilabs.sweto_app

import android.content.pm.PackageManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        // Without a key the map would only show blank tiles, so the app asks
        // first (channel `sweto/maps`) and shows the address form alone.
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "sweto/maps")
            .setMethodCallHandler { call, result ->
                if (call.method == "isConfigured") result.success(hasMapsKey())
                else result.notImplemented()
            }
    }

    private fun hasMapsKey(): Boolean = try {
        val info = packageManager.getApplicationInfo(
            packageName, PackageManager.GET_META_DATA)
        !info.metaData?.getString("com.google.android.geo.API_KEY").isNullOrBlank()
    } catch (e: PackageManager.NameNotFoundException) {
        false
    }
}
