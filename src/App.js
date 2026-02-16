import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./App.css";
import Home from "./pages/Home";
import ResearchPage from "./pages/Research";
import PolicyAnalysis from "./pages/PolicyAnalysis";
import References from "./pages/References";

function App() {
  return (
    <Router basename={process.env.PUBLIC_URL}>
      <div className="App">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/policy-analysis" element={<PolicyAnalysis />} />
          <Route path="/references" element={<References />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
