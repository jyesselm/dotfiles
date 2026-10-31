package com.yesselman.watchtv;

import android.app.Activity;
import android.app.SearchManager;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

/** The dashboard's Watch view, full screen. Trailers, services and Plex open in their own TV apps. */
public class MainActivity extends Activity {
    static final String LAN = "http://192.168.4.26:3000/?tv=1#watch";
    static final String TAILNET = "https://plex-server.tail2813f4.ts.net/?tv=1#watch";
    WebView web;
    boolean triedTailnet;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        web = new WebView(this);
        web.setBackgroundColor(Color.BLACK);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setUserAgentString(s.getUserAgentString() + " PlexTV");  // the page switches to its TV layout
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
                Uri u = req.getUrl();
                if ("watch".equals(u.getScheme())) return watch(u);
                String host = String.valueOf(u.getHost());
                if (host.equals("192.168.4.26") || host.equals("plex-server.tail2813f4.ts.net")) return false;
                if (open(new Intent(Intent.ACTION_VIEW, u))) return true;
                String yt = host.endsWith("youtube.com") ? u.getQueryParameter("v") : null;
                return yt != null && open(new Intent(Intent.ACTION_VIEW, Uri.parse("vnd.youtube:" + yt)));
            }

            @Override
            public void onReceivedError(WebView v, WebResourceRequest req, WebResourceError err) {
                if (!req.isForMainFrame()) return;
                if (!triedTailnet && req.getUrl().toString().startsWith("http://192.168.4.26")) {
                    triedTailnet = true;
                    v.loadUrl(TAILNET);
                } else {
                    toast("Can't reach the server");
                }
            }
        });
        setContentView(web);
        web.loadUrl(LAN);
    }

    /** watch://plex opens Plex; watch://search?q=… opens Google TV search, whose results deep-link into each service. */
    boolean watch(Uri u) {
        if ("plex".equals(u.getHost())) {
            Intent i = getPackageManager().getLeanbackLaunchIntentForPackage("com.plexapp.android");
            if (i == null) i = getPackageManager().getLaunchIntentForPackage("com.plexapp.android");
            if (i == null || !open(i)) toast("Plex app not installed");
            return true;
        }
        String q = u.getQueryParameter("q");
        if (!open(new Intent("android.search.action.GLOBAL_SEARCH").putExtra(SearchManager.QUERY, q))
                && !open(new Intent(Intent.ACTION_WEB_SEARCH).putExtra(SearchManager.QUERY, q))) {
            toast("No search app for " + q);
        }
        return true;
    }

    boolean open(Intent i) {
        try {
            startActivity(i);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_LONG).show();
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }
}
