package com.bilsan.director;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.URL;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * تطبيق المديرة: يفتح البرنامج من الحاسوب المركزي داخل الهاتف،
 * بنفس الصلاحيات (تدخل بنفس اسم المستخدم وكلمة المرور).
 */
public class MainActivity extends Activity {
    private static final int FILE_REQ = 7;
    private WebView web;
    private SharedPreferences prefs;
    private ValueCallback<Uri[]> fileCb;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private volatile boolean scanning = false;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(Color.parseColor("#173F36"));
        prefs = getSharedPreferences("bilsan", MODE_PRIVATE);
        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#173F36"));
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);
        s.setUserAgentString(s.getUserAgentString() + " BilsanDirectorApp/1");
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true);

        web.addJavascriptInterface(new Bridge(), "BilsanApp");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                Uri u = r.getUrl();
                String server = server();
                if ("file".equals(u.getScheme())) return false;
                if (server != null && u.toString().startsWith(server)) return false;
                try {  // الروابط الخارجية (واتساب، خرائط...) تفتح خارج التطبيق
                    startActivity(new Intent(Intent.ACTION_VIEW, u));
                } catch (ActivityNotFoundException ignored) { }
                return true;
            }

            @Override
            public void onPageFinished(WebView v, String url) {
                // الطباعة من داخل الصفحات (الوصولات، التقارير...)
                v.evaluateJavascript("window.print=function(){BilsanApp.print(document.title||'Bilsan')};", null);
                CookieManager.getInstance().flush();
            }

            @Override
            public void onReceivedError(WebView v, WebResourceRequest r, WebResourceError e) {
                if (r.isForMainFrame()) showOffline();
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (fileCb != null) fileCb.onReceiveValue(null);
                fileCb = cb;
                try {
                    startActivityForResult(p.createIntent(), FILE_REQ);
                } catch (ActivityNotFoundException e) {
                    fileCb = null;
                    return false;
                }
                return true;
            }
        });
        web.setDownloadListener((url, ua, cd, mime, len) -> {
            try {
                DownloadManager.Request req = new DownloadManager.Request(Uri.parse(url));
                req.addRequestHeader("Cookie", CookieManager.getInstance().getCookie(url));
                req.addRequestHeader("User-Agent", ua);
                String name = URLUtil.guessFileName(url, cd, mime);
                req.setTitle(name);
                req.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                req.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name);
                ((DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE)).enqueue(req);
                Toast.makeText(this, "جارٍ التحميل: " + name, Toast.LENGTH_SHORT).show();
            } catch (Exception e) {
                Toast.makeText(this, "تعذّر التحميل", Toast.LENGTH_SHORT).show();
            }
        });

        if (b != null) web.restoreState(b);
        else if (server() == null) showSetup();
        else web.loadUrl(server() + "/");
    }

    private String server() {
        return prefs.getString("server", null);
    }

    private void showSetup() {
        web.loadUrl("file:///android_asset/setup.html");
    }

    private void showOffline() {
        web.loadUrl("file:///android_asset/offline.html");
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    protected void onPause() {
        super.onPause();
        CookieManager.getInstance().flush();
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack() && !web.getUrl().startsWith("file:")) web.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (req == FILE_REQ && fileCb != null) {
            fileCb.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(res, data));
            fileCb = null;
        }
    }

    private void js(String code) {
        ui.post(() -> web.evaluateJavascript(code, null));
    }

    /** يعيد العنوان بالشكل http://IP:PORT */
    static String normalize(String in) {
        String u = in.trim();
        if (u.isEmpty()) return "";
        if (!u.startsWith("http://") && !u.startsWith("https://")) u = "http://" + u;
        while (u.endsWith("/")) u = u.substring(0, u.length() - 1);
        String rest = u.substring(u.indexOf("://") + 3);
        if (!rest.contains(":")) u = u + ":5000";
        return u;
    }

    /** يتأكد أن العنوان هو برنامج بيلسان على الحاسوب المركزي */
    static JSONObject ping(String base, int timeout) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(base + "/app/ping").openConnection();
            c.setConnectTimeout(timeout);
            c.setReadTimeout(timeout * 2);
            if (c.getResponseCode() != 200) return null;
            InputStream in = c.getInputStream();
            byte[] buf = new byte[2048];
            int n = in.read(buf);
            if (n <= 0) return null;
            JSONObject o = new JSONObject(new String(buf, 0, n, "UTF-8"));
            return o.optInt("bilsan") == 1 ? o : null;
        } catch (Exception e) {
            return null;
        } finally {
            if (c != null) c.disconnect();
        }
    }

    static List<String> localPrefixes() {
        List<String> out = new ArrayList<>();
        try {
            for (NetworkInterface ni : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!ni.isUp() || ni.isLoopback()) continue;
                for (InetAddress a : Collections.list(ni.getInetAddresses())) {
                    if (a instanceof Inet4Address && a.isSiteLocalAddress()) {
                        String ip = a.getHostAddress();
                        String p = ip.substring(0, ip.lastIndexOf('.') + 1);
                        if (!out.contains(p)) out.add(p);
                    }
                }
            }
        } catch (Exception ignored) { }
        return out;
    }

    class Bridge {
        @JavascriptInterface
        public String current() {
            String s = server();
            return s == null ? "" : s;
        }

        @JavascriptInterface
        public void connect(String addr) {
            final String base = normalize(addr);
            if (base.isEmpty()) {
                js("done(false,'اكتبي العنوان')");
                return;
            }
            new Thread(() -> {
                JSONObject o = ping(base, 3000);
                if (o == null) {
                    js("done(false," + JSONObject.quote("لم يُعثر على البرنامج في " + base + ". تأكدي أن الحاسوب المركزي شغال وأن الهاتف على نفس الويفي.") + ")");
                } else if (!o.optBoolean("central", true)) {
                    js("done(false,'هذا حاسوب فرع وليس الحاسوب المركزي')");
                } else {
                    prefs.edit().putString("server", base).apply();
                    ui.post(() -> {
                        web.clearHistory();
                        web.loadUrl(base + "/");
                    });
                }
            }).start();
        }

        @JavascriptInterface
        public void scan() {
            if (scanning) return;
            scanning = true;
            new Thread(() -> {
                List<String> prefixes = localPrefixes();
                final List<String> found = Collections.synchronizedList(new ArrayList<>());
                ExecutorService pool = Executors.newFixedThreadPool(48);
                int[] ports = {5000};
                for (String p : prefixes)
                    for (int i = 1; i < 255; i++)
                        for (int port : ports) {
                            final String base = "http://" + p + i + ":" + port;
                            pool.submit(() -> {
                                JSONObject o = ping(base, 700);
                                if (o != null && o.optBoolean("central", true)) found.add(base);
                            });
                        }
                pool.shutdown();
                try {
                    pool.awaitTermination(60, TimeUnit.SECONDS);
                } catch (InterruptedException ignored) { }
                scanning = false;
                JSONArray arr = new JSONArray(found);
                js("scanned(" + arr + "," + (prefixes.isEmpty() ? "true" : "false") + ")");
            }).start();
        }

        @JavascriptInterface
        public void retry() {
            ui.post(() -> {
                String s = server();
                if (s == null) showSetup();
                else web.loadUrl(s + "/");
            });
        }

        @JavascriptInterface
        public void setup() {
            ui.post(MainActivity.this::showSetup);
        }

        @JavascriptInterface
        public void print(String title) {
            ui.post(() -> {
                PrintManager pm = (PrintManager) getSystemService(Context.PRINT_SERVICE);
                PrintDocumentAdapter ad = web.createPrintDocumentAdapter(title);
                pm.print(title, ad, new PrintAttributes.Builder().build());
            });
        }
    }
}
