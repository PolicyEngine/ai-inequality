import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./views/Home";
import ResearchPage from "./views/Research";
import PolicyAnalysis from "./views/PolicyAnalysis";
import IncomeShift from "./views/IncomeShift";
import References from "./views/References";
import BudgetLabMemo from "./views/BudgetLabMemo";
import { currentBasePath } from "./utils/basePath";

function App() {
  return (
    <Router basename={currentBasePath() || undefined}>
      <div className="App">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/policy-analysis" element={<PolicyAnalysis />} />
          <Route path="/income-shift" element={<IncomeShift />} />
          <Route path="/references" element={<References />} />
          <Route path="/budget-lab" element={<BudgetLabMemo />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
