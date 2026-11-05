import "./globals.css";
import Link from "next/link";

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
        <nav className="bg-white border-b border-gray-200 px-6 py-3">
          <div className="max-w-7xl mx-auto flex items-center gap-8">
            <Link href="/" className="font-bold text-lg">
              Nettle
            </Link>
            <div className="flex gap-6 text-sm">
              <Link
                href="/portfolio"
                className="text-gray-600 hover:text-gray-900"
              >
                Portfolio
              </Link>
              <Link
                href="/assessments"
                className="text-gray-600 hover:text-gray-900"
              >
                Assessments
              </Link>
              <Link
                href="/reports"
                className="text-gray-600 hover:text-gray-900"
              >
                Reports
              </Link>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
