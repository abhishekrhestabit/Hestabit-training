import Link from "next/link";

export default function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-6">
      <div className="max-w-2xl text-center space-y-4">
        <h1 className="text-3xl font-bold text-gray-800">About This Project</h1>
        <p className="text-gray-600">
          This project is a learning exercise to master Next.js Routing.
          We are using <strong>Nested Layouts</strong> to apply the Sidebar only to the dashboard section,
          keeping the marketing pages clean.
        </p>
        <Link href="/" className="text-blue-600 hover:underline">
          &larr; Back to Home
        </Link>
      </div>
    </div>
  );
}