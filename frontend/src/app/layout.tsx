import "./globals.css";
import { SessionProvider } from "@/lib/session";

export const metadata = {
  title: "Nettle Basic",
  description: "Risk engineering platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
