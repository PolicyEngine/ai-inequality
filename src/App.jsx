import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./views/Home";
import ResearchPage from "./views/Research";
import PolicyAnalysis from "./views/PolicyAnalysis";
import IncomeShift from "./views/IncomeShift";
import References from "./views/References";
import { basePath } from "./utils/basePath";

function App() {
  return (
    <Router basename={basePath || undefined}>
      <div className="App">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/policy-analysis" element={<PolicyAnalysis />} />
          <Route path="/income-shift" element={<IncomeShift />} />
          <Route path="/references" element={<References />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
