import Link from "next/link";

export default function Home() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          href="/portfolio"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
        >
          <h2 className="font-semibold text-lg mb-2">Portfolio</h2>
          <p className="text-gray-500 text-sm">
            Manage clients and their details
          </p>
        </Link>
        <Link
          href="/assessments"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
        >
          <h2 className="font-semibold text-lg mb-2">Assessments</h2>
          <p className="text-gray-500 text-sm">
            Create and manage risk assessments
          </p>
        </Link>
        <Link
          href="/reports"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
        >
          <h2 className="font-semibold text-lg mb-2">Reports</h2>
          <p className="text-gray-500 text-sm">
            View and generate AI risk reports
          </p>
        </Link>
      </div>
    </div>
  );
}
