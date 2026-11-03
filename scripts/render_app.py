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
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.GeolocationPermissions;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
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
    private static final int REQUEST_FILE = 1003;
    private WebView webView;
    private PermissionRequest pendingWebRequest;
    private GeolocationPermissions.Callback pendingGeoCallback;
    private String pendingGeoOrigin;
    private ValueCallback<Uri[]> pendingFileCallback;

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
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                view.evaluateJavascript(NativeBridge.SCRIPT, null);
            }
        });
        webView.addJavascriptInterface(new NativeBridge(this, webView), "AndroidNative");
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

            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, WebChromeClient.FileChooserParams params) {
                if (pendingFileCallback != null) pendingFileCallback.onReceiveValue(null);
                pendingFileCallback = callback;
                try {
                    startActivityForResult(params.createIntent(), REQUEST_FILE);
                } catch (ActivityNotFoundException e) {
                    pendingFileCallback = null;
                    return false;
                }
                return true;
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

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_FILE && pendingFileCallback != null) {
            pendingFileCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data));
            pendingFileCallback = null;
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
if "android.permission.ACCESS_FINE_LOCATION" in ANDROID_PERMISSIONS:
    ANDROID_PERMISSIONS.append("android.permission.ACCESS_COARSE_LOCATION")
MANIFEST_PERMISSIONS = "\n".join('    <uses-permission android:name="%s" />' % name for name in ANDROID_PERMISSIONS)
JAVA_PERMISSIONS = ", ".join('"%s"' % name for name in ANDROID_PERMISSIONS)


NATIVE_BRIDGE = '''package __PACKAGE__;

import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.os.Build;
import android.provider.ContactsContract;
import android.telephony.TelephonyManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

public class NativeBridge {
    static final String SCRIPT =
        "(function(){if(window.__link2apkReady)return;window.__link2apkReady=true;"
        + "var pending={},seq=0;"
        + "window.__link2apkResolve=function(id,ok,payload){var p=pending[id];if(!p)return;delete pending[id];if(ok)p.resolve(payload);else p.reject(new Error(payload));};"
        + "function call(method){return new Promise(function(resolve,reject){var id=String(++seq);pending[id]={resolve:resolve,reject:reject};window.AndroidNative[method](id);});}"
        + "window.Link2Apk={getContacts:function(){return call('getContacts');},getPhoneState:function(){return call('getPhoneState');}};"
        + "if(!('Notification' in window)){var N=function(title,options){this.title=String(title);this.body=options&&options.body?String(options.body):'';if(window.AndroidNative)window.AndroidNative.show(this.title,this.body);};"
        + "N.permission='granted';N.requestPermission=function(cb){if(cb)cb('granted');return Promise.resolve('granted');};window.Notification=N;}"
        + "})();";

    private static final String CONTACTS = "android.permission.READ_CONTACTS";
    private static final String PHONE_STATE = "android.permission.READ_PHONE_STATE";
    private static final String NOTIFICATIONS = "android.permission.POST_NOTIFICATIONS";
    private static final String CHANNEL_ID = "web";
    private static final int MAX_CONTACTS = 1000;

    private final Activity activity;
    private final WebView webView;

    public NativeBridge(Activity activity, WebView webView) {
        this.activity = activity;
        this.webView = webView;
    }

    @JavascriptInterface
    public void show(final String title, final String body) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                showNotification(title, body);
            }
        });
    }

    @JavascriptInterface
    public void getContacts(final String callId) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                if (!hasPermission(CONTACTS)) {
                    resolve(callId, false, JSONObject.quote("Contacts permission was not granted"));
                    return;
                }
                try {
                    resolve(callId, true, readContacts().toString());
                } catch (Exception e) {
                    resolve(callId, false, JSONObject.quote("Could not read contacts"));
                }
            }
        }).start();
    }

    @JavascriptInterface
    public void getPhoneState(String callId) {
        if (!hasPermission(PHONE_STATE)) {
            resolve(callId, false, JSONObject.quote("Phone state permission was not granted"));
            return;
        }
        try {
            TelephonyManager telephony = (TelephonyManager) activity.getSystemService(Context.TELEPHONY_SERVICE);
            JSONObject state = new JSONObject();
            state.put("carrier", telephony.getNetworkOperatorName());
            state.put("simState", telephony.getSimState());
            resolve(callId, true, state.toString());
        } catch (JSONException e) {
            resolve(callId, false, JSONObject.quote("Could not read phone state"));
        }
    }

    private JSONArray readContacts() throws JSONException {
        JSONArray result = new JSONArray();
        Cursor cursor = activity.getContentResolver().query(
            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
            new String[] { ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME, ContactsContract.CommonDataKinds.Phone.NUMBER },
            null,
            null,
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC");
        if (cursor == null) return result;
        try {
            while (cursor.moveToNext() && result.length() < MAX_CONTACTS) {
                JSONObject contact = new JSONObject();
                contact.put("name", cursor.getString(0));
                contact.put("phone", cursor.getString(1));
                result.put(contact);
            }
        } finally {
            cursor.close();
        }
        return result;
    }

    private void showNotification(String title, String body) {
        if (!hasPermission(NOTIFICATIONS)) return;
        NotificationManager manager = (NotificationManager) activity.getSystemService(Context.NOTIFICATION_SERVICE);
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(new NotificationChannel(CHANNEL_ID, "Website", NotificationManager.IMPORTANCE_DEFAULT));
            builder = new Notification.Builder(activity, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(activity);
        }
        builder.setContentTitle(title).setContentText(body).setSmallIcon(android.R.drawable.ic_dialog_info).setAutoCancel(true);
        manager.notify((int) System.currentTimeMillis(), builder.build());
    }

    private boolean hasPermission(String permission) {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.M
            || activity.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED;
    }

    private void resolve(final String callId, final boolean ok, final String payload) {
        final String script = "window.__link2apkResolve(" + JSONObject.quote(callId) + "," + ok + "," + payload + ")";
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                webView.evaluateJavascript(script, null);
            }
        });
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
    write_text("app/src/main/AndroidManifest.xml", MANIFEST.replace("__PERMISSIONS__", MANIFEST_PERMISSIONS))
    write_text("app/src/main/res/values/strings.xml", STRINGS.replace("__NAME__", html.escape(APP_NAME)))
    write_text("app/src/main/java/" + package_path + "/MainActivity.java",
               MAIN_ACTIVITY.replace("__PACKAGE__", PACKAGE).replace("__PERMS__", JAVA_PERMISSIONS).replace("__URL__", json_string(APP_URL)))
    write_text("app/src/main/java/" + package_path + "/NativeBridge.java", NATIVE_BRIDGE.replace("__PACKAGE__", PACKAGE))
    write_bytes("app/src/main/res/mipmap-xxxhdpi/ic_launcher.png", app_icon())


def json_string(value):
    import json
    return json.dumps(value)


main()
