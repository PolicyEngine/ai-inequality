import ClientAppRouter from "../../src/ClientAppRouter";

const routes = ["", "research", "policy-analysis", "income-shift", "references"];

export function generateStaticParams() {
  return routes.map((route) => ({
    slug: route ? [route] : [],
  }));
}

export default function Page() {
  return <ClientAppRouter />;
}
