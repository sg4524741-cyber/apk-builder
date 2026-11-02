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

MANIFEST = '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />

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
import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());
        webView.loadUrl(__URL__);
        setContentView(webView);
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
    write_text("app/src/main/AndroidManifest.xml", MANIFEST)
    write_text("app/src/main/res/values/strings.xml",
               '<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">'
               + html.escape(APP_NAME) + "</string>
</resources>
")
    write_text("app/src/main/java/" + package_path + "/MainActivity.java",
               MAIN_ACTIVITY.replace("__PACKAGE__", PACKAGE).replace("__URL__", json_string(APP_URL)))
    write_bytes("app/src/main/res/mipmap-xxxhdpi/ic_launcher.png", app_icon())


def json_string(value):
    import json
    return json.dumps(value)


main()
