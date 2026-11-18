import ClientAppRouter from "../../src/ClientAppRouter";
import { routeMetadata } from "../../src/utils/routeMetadata";

const routes = [
  "",
  "research",
  "policy-analysis",
  "income-shift",
  "references",
  "budget-lab",
];

export function generateStaticParams() {
  return routes.map((route) => ({
    slug: route ? [route] : [],
  }));
}

// Link-preview tags, built at export time. Reading searchParams here would
// stop the static export, so the tags can't follow ?country=.
export async function generateMetadata({ params }) {
  const { slug } = await params;
  return routeMetadata(slug?.[0] ?? "");
}

export default function Page() {
  return <ClientAppRouter />;
}
