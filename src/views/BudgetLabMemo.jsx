import React from "react";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { memoMarkdown } from "../data/memoContent";
import { countrySearchParams } from "../utils/countryConfig";

// The write-up lives in ai-scenarios-memo.md; src/data/memoContent.js is
// generated from it by `bun run build:memo`. This view only renders it.
function BudgetLabMemo() {
  // The memo covers the US scenarios, so its link opens the US experiment on
  // either country's path: on /uk/ai-inequality it adds ?country=us.
  const usQuery = new URLSearchParams(countrySearchParams("us")).toString();
  return (
    <div className="section">
      <article className="memo-page">
        <nav className="memo-page-nav">
          <Link
            to={{
              pathname: "/income-shift",
              search: usQuery ? `?${usQuery}` : "",
            }}
          >
            Interactive version of this analysis
          </Link>
        </nav>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {memoMarkdown}
        </ReactMarkdown>
      </article>
    </div>
  );
}

export default BudgetLabMemo;
