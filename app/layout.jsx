import "./globals.css";
import PolicyEngineHeader from "./PolicyEngineHeader";

export const metadata = {
  title:
    "How do economic policies mediate AI's impact on inequality? | PolicyEngine",
  description:
    "PolicyEngine models how policy choices, safety nets, and capital taxation shape inequality under AI-driven economic change.",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "any" },
    ],
    apple: "/logo512.png",
  },
  manifest: "/manifest.json",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <PolicyEngineHeader />
        {children}
      </body>
    </html>
  );
}
