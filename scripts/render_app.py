import html
import os
import struct
import zlib

APP_NAME = os.environ["APP_NAME"]
APP_URL = os.environ["APP_URL"]
PACKAGE = os.environ["PACKAGE_NAME"]
ICON_FILE = os.environ.get("ICON_FILE", "")
ROOT = "android"
PNG_SIGNATURE = bytes([137, 80, 78, 71, 13, 10, 26, 10])
THEME_RGB = (37, 99, 235)

SETTINGS = '''pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "WebApp"
include ':app'
'''

ROOT_BUILD = '''plugins {
    id 'com.android.application' version '8.5.2' apply false
}
'''

GRADLE_PROPERTIES = '''org.gradle.jvmargs=-Xmx2g
android.useAndroidX=true
'''

APP_BUILD = '''plugins {
    id 'com.android.application'
}

android {
    namespace '__PACKAGE__'
    compileSdk 34

    defaultConfig {
        applicationId '__PACKAGE__'
        minSdk 21
        targetSdk 34
        versionCode 1
        versionName '1.0.0'
    }

    buildTypes {
        release {
            minifyEnabled false
            signingConfig signingConfigs.debug
        }
    }

    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}
'''

STRINGS = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">__NAME__</string>
</resources>
'''

MANIFEST = '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

__PERMISSIONS__

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:usesCleartextTraffic="true"
        android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
'''

MAIN_ACTIVITY = '''package __PACKAGE__;

import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.webkit.GeolocationPermissions;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.util.ArrayList;

public class MainActivity extends Activity {
    private static final String[] APP_PERMISSIONS = { __PERMS__ };
    private static final String LOCATION = "android.permission.ACCESS_FINE_LOCATION";
    private static final int REQUEST_STARTUP = 1001;
    private static final int REQUEST_WEB = 1002;
    private WebView webView;
    private PermissionRequest pendingWebRequest;
    private GeolocationPermissions.Callback pendingGeoCallback;
    private String pendingGeoOrigin;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setGeolocationEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                String[] needed = missing(androidPermissionsFor(request.getResources()));
                if (needed.length == 0) {
                    request.grant(request.getResources());
                    return;
                }
                pendingWebRequest = request;
                requestPermissions(needed, REQUEST_WEB);
            }

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
                if (hasPermission(LOCATION)) {
                    callback.invoke(origin, true, false);
                    return;
                }
                pendingGeoOrigin = origin;
                pendingGeoCallback = callback;
                requestPermissions(new String[] { LOCATION }, REQUEST_WEB);
            }
        });
        setContentView(webView);
        webView.loadUrl(__URL__);
        requestStartupPermissions();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQUEST_WEB) return;
        if (pendingWebRequest != null) {
            PermissionRequest request = pendingWebRequest;
            pendingWebRequest = null;
            if (missing(androidPermissionsFor(request.getResources())).length == 0) {
                request.grant(request.getResources());
            } else {
                request.deny();
            }
        }
        if (pendingGeoCallback != null) {
            pendingGeoCallback.invoke(pendingGeoOrigin, hasPermission(LOCATION), false);
            pendingGeoCallback = null;
            pendingGeoOrigin = null;
        }
    }

    private void requestStartupPermissions() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return;
        String[] startup = missing(APP_PERMISSIONS);
        if (startup.length > 0) requestPermissions(startup, REQUEST_STARTUP);
    }

    private String[] androidPermissionsFor(String[] resources) {
        ArrayList<String> list = new ArrayList<String>();
        for (String resource : resources) {
            if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource)) list.add("android.permission.CAMERA");
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) list.add("android.permission.RECORD_AUDIO");
        }
        return list.toArray(new String[0]);
    }

    private String[] missing(String[] permissions) {
        ArrayList<String> list = new ArrayList<String>();
        for (String permission : permissions) {
            if (!hasPermission(permission)) list.add(permission);
        }
        return list.toArray(new String[0]);
    }

    private boolean hasPermission(String permission) {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.M
            || checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED;
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
'''


PERMISSIONS = [item for item in os.environ.get("PERMISSIONS", "").split(",") if item]
ANDROID_PERMISSIONS = ["android.permission.INTERNET"] + ["android.permission." + item for item in PERMISSIONS]
MANIFEST_PERMISSIONS = "\n".join('    <uses-permission android:name="%s" />' % name for name in ANDROID_PERMISSIONS)
JAVA_PERMISSIONS = ", ".join('"%s"' % name for name in ANDROID_PERMISSIONS)


def write_text(path, text):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(text)


def write_bytes(path, data):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as handle:
        handle.write(data)


def png_chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def default_icon(size=192):
    pixels = (bytes([0]) + bytes(THEME_RGB) * size) * size
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return PNG_SIGNATURE + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", zlib.compress(pixels)) + png_chunk(b"IEND", b"")


def app_icon():
    if ICON_FILE and os.path.exists(ICON_FILE):
        with open(ICON_FILE, "rb") as handle:
            data = handle.read()
        if data[:8] != PNG_SIGNATURE:
            raise SystemExit("App icon must be a PNG file")
        return data
    return default_icon()


def main():
    package_path = PACKAGE.replace(".", "/")
    write_text("settings.gradle", SETTINGS)
    write_text("build.gradle", ROOT_BUILD)
    write_text("gradle.properties", GRADLE_PROPERTIES)
    write_text("app/build.gradle", APP_BUILD.replace("__PACKAGE__", PACKAGE))
    write_text("app/src/main/AndroidManifest.xml", MANIFEST.replace("__PERMISSIONS__", MANIFEST_PERMISSIONS))
    write_text("app/src/main/res/values/strings.xml", STRINGS.replace("__NAME__", html.escape(APP_NAME)))
    write_text("app/src/main/java/" + package_path + "/MainActivity.java",
               MAIN_ACTIVITY.replace("__PACKAGE__", PACKAGE).replace("__PERMS__", JAVA_PERMISSIONS).replace("__URL__", json_string(APP_URL)))
    write_bytes("app/src/main/res/mipmap-xxxhdpi/ic_launcher.png", app_icon())


def json_string(value):
    import json
    return json.dumps(value)


main()
