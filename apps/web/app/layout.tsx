/* Root layout — PWA + auth guard + responsive shell */
"use client";
import { useEffect } from "react";
import { useAuthStore } from "@/app/stores/authStore";
import LoginPage from "@/app/pages/login";
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);

  // Register service worker
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }, []);

  return (
    <html lang="en" className="dark">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=1, user-scalable=no" />
        <meta name="theme-color" content="#0f172a" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Memori" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/icon-192.svg" />
        <link rel="icon" type="image/svg+xml" href="/icons/icon-192.svg" />
      </head>
      <body>
        {token ? children : <LoginPage />}
      </body>
    </html>
  );
}