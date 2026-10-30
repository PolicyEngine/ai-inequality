/**
 * References database for the AI inequality site.
 *
 * This is the single source of truth for both the /references page and the
 * topic-organized cards on the Research page. Each entry has:
 *   - id:       unique identifier (LastnameYYYY / LastnameLastnameYYYY style)
 *   - type:     BibTeX-style type (article, techreport, misc, book, ...)
 *   - author, title, year: required
 *   - journal/volume/number/pages/institution/note: when applicable
 *   - url:      canonical link (prefer DOI url > publisher > working paper PDF)
 *   - doi:      optional, used for the citation link if present
 *   - topics:   array of topic slugs from `TOPICS` below — drives Research.jsx
 *   - summary:  one-sentence plain-text takeaway, surfaced in Research cards
 *
 * Topics are tags, not exclusive categories — most papers carry 2-3.
 */

export const TOPICS = {
  productivity_empirical: {
    title: "Empirical evidence on AI productivity",
    blurb:
      "Field experiments and observational studies measuring how generative AI changes worker output, quality, and skill complementarity.",
  },
  labor_markets: {
    title: "AI and labor markets",
    blurb:
      "How AI is reshaping employment, wages, and the composition of jobs — including the unresolved debate between middle-class augmentation (Autor) and high-skill displacement (Liu et al.).",
  },
  exposure_measurement: {
    title: "Occupational exposure measurement",
    blurb:
      "Methods for quantifying which occupations are most exposed to AI — the input to most distributional and macro forecasts.",
  },
  ai_adoption: {
    title: "AI adoption and diffusion",
    blurb:
      "Survey-based and telemetry-based measures of how fast AI is being used at work, and by whom.",
  },
  growth_theory: {
    title: "Growth, productivity, and macro modeling",
    blurb:
      "Macroeconomic models of how AI affects GDP, total factor productivity, and the long-run growth path.",
  },
  capital_labor: {
    title: "Capital, labor, and the Piketty debate",
    blurb:
      "Whether AI tilts income shares toward capital, and what that implies for taxation, ownership, and political economy.",
  },
  inequality_distribution: {
    title: "Inequality and distribution",
    blurb:
      "Direct evidence on AI's effects on wage inequality, wealth inequality, and the cross-country distribution of gains.",
  },
  tax_policy: {
    title: "Tax policy in the age of AI",
    blurb:
      "Public-finance responses to AI: capital taxation, consumption taxation, automation taxes, and the eroding labor-income tax base.",
  },
  ubi_transfers: {
    title: "UBI, transfers, and safety-net reform",
    blurb:
      "Proposed transfer-side responses — universal basic income, expanded safety nets, sovereign AI wealth funds — and what they require to be fiscally feasible.",
  },
  microsimulation: {
    title: "Tax-benefit microsimulation",
    blurb:
      "Methods and platforms for translating macro shocks into household-level distributional outcomes.",
  },
  general_equilibrium: {
    title: "Dynamic OLG and general equilibrium",
    blurb:
      "Overlapping-generations and broader GE models that capture intergenerational, savings, and capital-accumulation responses.",
  },
  stochastic_forecasting: {
    title: "Stochastic economic forecasting",
    blurb:
      "Probabilistic forecasting of macro inputs — joint distributions, Bayesian VARs, and growth-at-risk methods — that microsimulation can read in.",
  },
  transformative_ai: {
    title: "Transformative AI and explosive growth",
    blurb:
      "Scenarios in which AI drives qualitative shifts in the growth rate, R&D dynamics, or industrial output.",
  },
  scenarios: {
    title: "AI scenarios and futures",
    blurb:
      "Taxonomies of AI economic scenarios useful as inputs to policy-mediation analysis.",
  },
  existential_risk: {
    title: "Long-run, existential, and welfare framing",
    blurb:
      "Frameworks for thinking about AI alongside far-future welfare, existential risk, and longtermist evaluation.",
  },
  uk: {
    title: "United Kingdom evidence",
    blurb:
      "UK-specific evidence on AI exposure, adoption, and labour-market effects.",
  },
};

export const references = [
  // -------------------------------------------------------------------------
  // Empirical AI productivity field studies
  // -------------------------------------------------------------------------
  {
    id: "BrynjolfssonLiRaymond2025",
    type: "article",
    author: "Brynjolfsson, Erik and Li, Danielle and Raymond, Lindsey R.",
    title: "Generative AI at Work",
    year: 2025,
    journal: "Quarterly Journal of Economics",
    volume: 140,
    number: 2,
    pages: "889-942",
    doi: "10.1093/qje/qjae044",
    url: "https://academic.oup.com/qje/article/140/2/889/7929399",
    topics: ["productivity_empirical"],
    summary:
      "Field study of 5,179 customer-support agents using GenAI: 14% average productivity gain, 34% for novices, near-zero for experienced workers. The canonical worker-level RCT.",
  },
  {
    id: "NoyandZhang2023",
    type: "article",
    author: "Noy, Shakked and Zhang, Whitney",
    title:
      "Experimental Evidence on the Productivity Effects of Generative Artificial Intelligence",
    year: 2023,
    journal: "Science",
    volume: 381,
    number: 6654,
    pages: "187-192",
    doi: "10.1126/science.adh2586",
    url: "https://www.science.org/doi/10.1126/science.adh2586",
    topics: ["productivity_empirical"],
    summary:
      "Mid-level professional writers using ChatGPT cut task time by 37% and improved quality, with the largest gains for initially lower-skilled workers.",
  },
  {
    id: "Pengetal2023",
    type: "techreport",
    author:
      "Peng, Sida and Kalliamvakou, Eirini and Cihon, Peter and Demirer, Mert",
    title:
      "The Impact of AI on Developer Productivity: Evidence from GitHub Copilot",
    year: 2023,
    institution: "arXiv",
    number: "2302.06590",
    url: "https://arxiv.org/abs/2302.06590",
    topics: ["productivity_empirical"],
    summary:
      "RCT of GitHub Copilot users: 56% faster completion of a standard programming task, with larger gains for less experienced developers.",
  },
  {
    id: "DellAcquaetal2023",
    type: "techreport",
    author:
      "Dell'Acqua, Fabrizio and McFowland III, Edward and Mollick, Ethan and Lifshitz-Assaf, Hila and Kellogg, Katherine and Rajendran, Saran and Krayer, Lisa and Candelon, François and Lakhani, Karim R.",
    title:
      "Navigating the Jagged Technological Frontier: Field Experimental Evidence of the Effects of AI on Knowledge Worker Productivity and Quality",
    year: 2023,
    institution: "Harvard Business School",
    number: "Working Paper 24-013",
    url: "https://www.hbs.edu/faculty/Pages/item.aspx?num=64700",
    topics: ["productivity_empirical"],
    summary:
      "BCG consultants using GPT-4: large speed and quality gains on tasks inside the AI's frontier, but mistakes on tasks just outside it. Below-median performers gained most.",
  },
  {
    id: "HumlumandVestergaard2024",
    type: "techreport",
    author: "Humlum, Anders and Vestergaard, Emilie",
    title:
      "The Impact of ChatGPT on High-Skilled Work: Evidence from Freelancers",
    year: 2024,
    institution: "SSRN",
    url: "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4807516",
    topics: ["productivity_empirical"],
    summary:
      "Danish high-skilled freelancers: ChatGPT adoption produced small earnings effects despite large self-reported time savings, suggesting markets absorb productivity gains.",
  },

  // -------------------------------------------------------------------------
  // Occupational exposure measurement
  // -------------------------------------------------------------------------
  {
    id: "Eloundouetal2024",
    type: "article",
    author:
      "Eloundou, Tyna and Manning, Sam and Mishkin, Pamela and Rock, Daniel",
    title: "GPTs are GPTs: Labor Market Impact Potential of LLMs",
    year: 2024,
    journal: "Science",
    volume: 384,
    number: 6702,
    pages: "1306-1308",
    doi: "10.1126/science.adj0998",
    url: "https://www.science.org/doi/10.1126/science.adj0998",
    topics: ["exposure_measurement"],
    summary:
      "Roughly 80% of US workers could have at least 10% of tasks affected by LLMs; 19% could see at least 50%. Higher-wage occupations are more exposed.",
  },
  {
    id: "FeltenRajSeamans2021",
    type: "article",
    author: "Felten, Edward W. and Raj, Manav and Seamans, Robert",
    title:
      "Occupational, Industry, and Geographic Exposure to Artificial Intelligence",
    year: 2021,
    journal: "Strategic Management Journal",
    volume: 42,
    number: 12,
    pages: "2195-2217",
    doi: "10.1002/smj.3286",
    url: "https://onlinelibrary.wiley.com/doi/10.1002/smj.3286",
    topics: ["exposure_measurement"],
    summary:
      "The AI Occupational Exposure (AIOE) measure that underpins most subsequent labor-economics work on AI exposure.",
  },
  {
    id: "Webb2020",
    type: "techreport",
    author: "Webb, Michael",
    title: "The Impact of Artificial Intelligence on the Labor Market",
    year: 2020,
    institution: "SSRN",
    url: "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3482150",
    topics: ["exposure_measurement"],
    summary:
      "Patent-text-based exposure measure: previous waves of automation hit low-wage manual work; AI exposure is concentrated in high-wage cognitive occupations.",
  },
  {
    id: "Zakeriniaetal2024",
    type: "techreport",
    author: "Zakerinia, Saeede and Chen, Jingyu and Srinivasan, Suraj",
    title:
      "Displacement or Complementarity? The Impact of AI on Occupational Tasks",
    year: 2024,
    institution: "Harvard Business School",
    url: "https://www.hbs.edu/faculty/Pages/item.aspx?num=67045",
    topics: ["exposure_measurement"],
  },

  // -------------------------------------------------------------------------
  // AI adoption
  // -------------------------------------------------------------------------
  {
    id: "BickBlandinDeming2024",
    type: "techreport",
    author: "Bick, Alexander and Blandin, Adam and Deming, David J.",
    title: "The Rapid Adoption of Generative AI",
    year: 2024,
    institution: "NBER",
    number: "32966",
    url: "https://www.nber.org/papers/w32966",
    topics: ["ai_adoption"],
    summary:
      "Nationally representative US survey: by August 2024, 39.4% of working-age adults had used GenAI and 28% had used it at work. Adoption is faster than the PC or the internet.",
  },
  {
    id: "AnthropicEconomicIndex2026",
    type: "techreport",
    author: "Anthropic",
    title: "Anthropic Economic Index",
    year: 2026,
    institution: "Anthropic",
    url: "https://www.anthropic.com/economic-index",
    topics: ["ai_adoption"],
    summary:
      "Quarterly index of Claude usage by occupation. Share of jobs using AI for 25%+ of tasks rose from 36% (Jan 2025) to 49% by late 2025; 52% augmentation vs. 45% automation.",
  },

  // -------------------------------------------------------------------------
  // AI and labor markets — debate and evidence
  // -------------------------------------------------------------------------
  {
    id: "Autor2024",
    type: "techreport",
    author: "Autor, David H.",
    title: "Applying AI to Rebuild Middle Class Jobs",
    year: 2024,
    institution: "NBER",
    number: "32140",
    url: "https://www.nber.org/papers/w32140",
    topics: ["labor_markets"],
    summary:
      "Argues AI can extend expertise to middle-skill workers, partially reversing four decades of polarization — but only with deliberate policy.",
  },
  {
    id: "AutorandThompson2025",
    type: "techreport",
    author: "Autor, David H. and Thompson, Neil",
    title: "Expertise",
    year: 2025,
    institution: "NBER",
    number: "33941",
    url: "https://www.nber.org/papers/w33941",
    topics: ["labor_markets"],
    summary:
      "Formalizes how AI redistributes expertise across the wage distribution. The theoretical complement to Autor (2024).",
  },
  {
    id: "Liuetal2025",
    type: "techreport",
    author:
      "Liu, Huben and Papanikolaou, Dimitris and Schmidt, Lawrence D. W. and Seegmiller, Bryan",
    title:
      "Technology and Labor Markets: Past, Present, and Future; Evidence from Two Centuries of Innovation",
    year: 2025,
    institution: "NBER",
    number: "34386",
    note: "Brookings Papers on Economic Activity, Fall 2025",
    url: "https://www.brookings.edu/wp-content/uploads/2025/09/4_Liu-et-al_unembargoed.pdf",
    topics: ["labor_markets"],
    summary:
      "Patent-based analysis of 200 years of innovation. AI is the first wave that favors low-education jobs and threatens high-skill workers — reversing the historical pattern.",
  },
  {
    id: "BrynjolfssonChandarandChen2025",
    type: "techreport",
    author: "Brynjolfsson, Erik and Chandar, Bharat and Chen, Sida",
    title:
      "Canaries in the Coal Mine: Early Indicators of Labor Market Transformation",
    year: 2025,
    institution: "Stanford Digital Economy Lab",
    url: "https://digitaleconomy.stanford.edu/publications/canaries-in-the-coal-mine/",
    topics: ["labor_markets"],
    summary:
      "Early-career workers in AI-exposed occupations saw a 16% relative employment decline since late 2022; software developers aged 22-25 saw employment fall 20%.",
  },
  {
    id: "Bessen2018",
    type: "techreport",
    author: "Bessen, James",
    title: "AI and Jobs: The Role of Demand",
    year: 2018,
    institution: "NBER",
    number: "24235",
    url: "https://www.nber.org/papers/w24235",
    topics: ["labor_markets"],
  },
  {
    id: "MITIcebergIndex2025",
    type: "techreport",
    author: "MIT FutureTech and Oak Ridge National Laboratory",
    title: "Iceberg Index: Measuring AI's Impact on the Labor Market",
    year: 2025,
    institution: "MIT",
    url: "https://iceberg.mit.edu/",
    topics: ["labor_markets", "exposure_measurement"],
    summary:
      "Simulates 151M US workers across 32,000+ skills. AI can currently automate 11.7% of the US labor market (~$1.2T in wage value).",
  },

  // -------------------------------------------------------------------------
  // Growth and productivity
  // -------------------------------------------------------------------------
  {
    id: "Acemoglu2025",
    type: "article",
    author: "Acemoglu, Daron",
    title: "The Simple Macroeconomics of AI",
    year: 2025,
    journal: "Economic Policy",
    volume: 40,
    number: 121,
    pages: "13-63",
    doi: "10.1093/epolic/eiae042",
    url: "https://academic.oup.com/economicpolicy/article/40/121/13/7728473",
    topics: ["growth_theory"],
    summary:
      "Calibrates AI's macroeconomic impact at ~1.1-1.6% cumulative TFP gain over 10 years — well below industry projections. Predicts modest, not transformative, growth.",
  },
  {
    id: "Aghion2019",
    type: "article",
    author: "Aghion, Philippe and Jones, Benjamin F. and Jones, Charles I.",
    title: "Artificial Intelligence and Economic Growth",
    year: 2019,
    note: "In Agrawal, Gans, and Goldfarb (eds.), The Economics of Artificial Intelligence",
    url: "https://web.stanford.edu/~chadj/AJJ-AIandGrowth.pdf",
    topics: ["growth_theory", "transformative_ai"],
    summary:
      "Models AI as raising returns to capital and automating R&D itself. The Baumol-disease branch predicts persistent labor scarcity bottlenecks.",
  },
  {
    id: "AghionandBunel2024",
    type: "techreport",
    author: "Aghion, Philippe and Bunel, Simon",
    title: "AI and Growth: Where Do We Stand?",
    year: 2024,
    institution: "Federal Reserve Bank of San Francisco",
    url: "https://www.frbsf.org/wp-content/uploads/AI-and-Growth-Aghion-Bunel.pdf",
    topics: ["growth_theory"],
  },
  {
    id: "Brynjolfsson2021",
    type: "article",
    author: "Brynjolfsson, Erik and Rock, Daniel and Syverson, Chad",
    title:
      "The Productivity J-Curve: How Intangibles Complement General Purpose Technologies",
    year: 2021,
    journal: "American Economic Journal: Macroeconomics",
    doi: "10.1257/mac.20180386",
    url: "https://pubs.aeaweb.org/doi/10.1257/mac.20180386",
    topics: ["growth_theory", "productivity_empirical"],
  },
  {
    id: "ErdilandBesiroglu2023",
    type: "techreport",
    author: "Erdil, Ege and Besiroglu, Tamay",
    title: "Explosive Growth from AI Automation: A Review of the Arguments",
    year: 2023,
    institution: "arXiv",
    number: "2309.11690",
    url: "https://arxiv.org/abs/2309.11690",
    topics: ["growth_theory", "transformative_ai"],
    summary:
      "Reviews the case for >30%/year growth under full AI automation: removes labor as a bottleneck and accelerates R&D. Survey of mechanisms and counterarguments.",
  },
  {
    id: "BesiroglEmeryXuThompson2024",
    type: "article",
    author: "Besiroglu, Tamay and Emery-Xu, Nicholas and Thompson, Neil",
    title: "Economic Impacts of AI-Augmented R&D",
    year: 2024,
    journal: "Research Policy",
    doi: "10.1016/j.respol.2024.105028",
    url: "https://www.sciencedirect.com/science/article/pii/S0048733324000866",
    topics: ["growth_theory", "transformative_ai"],
  },
  {
    id: "ThompsonGeManso2022",
    type: "techreport",
    author: "Thompson, Neil C. and Ge, Shuning and Manso, Gabriel F.",
    title: "The Importance of (Exponentially More) Computing Power",
    year: 2022,
    institution: "arXiv",
    number: "2206.14007",
    url: "https://arxiv.org/abs/2206.14007",
    topics: ["growth_theory"],
  },
  {
    id: "Villalobos2023",
    type: "misc",
    author: "Villalobos, Pablo",
    title: "Scaling Laws Literature Review",
    year: 2023,
    note: "Epoch AI blog",
    url: "https://epoch.ai/blog/scaling-laws-literature-review",
    topics: ["growth_theory"],
  },
  {
    id: "Halperinetal2025",
    type: "techreport",
    author:
      "Halperin, Basil and Ho, Benjamin and Srinivasan, Akhil and Tao, Siyuan",
    title: "Is Automating AI Research Enough?",
    year: 2025,
    url: "https://www.basilhalperin.com/papers/shs.pdf",
    topics: ["growth_theory", "transformative_ai"],
  },
  {
    id: "EthandDavidson2025",
    type: "misc",
    author: "Eth, Daniel and Davidson, Tom",
    title: "Will AI R&D Automation Cause a Software Intelligence Explosion?",
    year: 2025,
    note: "Forethought Research",
    url: "https://www.forethought.org/research/will-ai-r-and-d-automation-cause-a-software-intelligence-explosion",
    topics: ["transformative_ai", "scenarios"],
  },
  {
    id: "DavidsonandHoulden2025",
    type: "misc",
    author: "Davidson, Tom and Houlden, Tom",
    title: "How Quick and Big Would a Software Intelligence Explosion Be?",
    year: 2025,
    note: "Forethought Research",
    url: "https://www.forethought.org/research/how-quick-and-big-would-a-software-intelligence-explosion-be",
    topics: ["transformative_ai", "scenarios"],
  },
  {
    id: "DavidsonandHadshar2025",
    type: "misc",
    author: "Davidson, Tom and Hadshar, Lukas",
    title: "The Industrial Explosion",
    year: 2025,
    note: "Forethought Research",
    url: "https://www.forethought.org/research/the-industrial-explosion",
    topics: ["transformative_ai", "scenarios"],
  },
  {
    id: "ErdilandBarnett2025",
    type: "misc",
    author: "Erdil, Ege and Barnett, Megan",
    title: "Most AI Value Will Come From Broad Automation, Not from R&D",
    year: 2025,
    note: "Epoch AI Gradient Updates",
    url: "https://epoch.ai/gradient-updates/most-ai-value-will-come-from-broad-automation-not-from-r-d",
    topics: ["growth_theory", "scenarios"],
  },
  {
    id: "Davidson2021",
    type: "misc",
    author: "Davidson, Tom",
    title: "Could Advanced AI Drive Explosive Economic Growth?",
    year: 2021,
    institution: "Open Philanthropy",
    url: "https://www.openphilanthropy.org/research/could-advanced-ai-drive-explosive-economic-growth/",
    topics: ["transformative_ai", "growth_theory"],
  },
  {
    id: "Roodman2020",
    type: "misc",
    author: "Roodman, David",
    title: "Modeling the Human Trajectory",
    year: 2020,
    institution: "Open Philanthropy",
    url: "https://www.openphilanthropy.org/research/modeling-the-human-trajectory/",
    topics: ["growth_theory", "transformative_ai"],
  },
  {
    id: "Hanson2001",
    type: "misc",
    author: "Hanson, Robin",
    title: "Economic Growth Given Machine Intelligence",
    year: 2001,
    url: "https://mason.gmu.edu/~rhanson/aigrow.pdf",
    topics: ["growth_theory", "transformative_ai"],
  },
  {
    id: "Nordhaus2021",
    type: "article",
    author: "Nordhaus, William D.",
    title: "Are We Approaching an Economic Singularity?",
    year: 2021,
    url: "https://williamnordhaus.com/files/williamdnordhaus/files/singularity-2021.pdf",
    topics: ["growth_theory", "transformative_ai"],
  },
  {
    id: "Kremer1993",
    type: "article",
    author: "Kremer, Michael",
    title:
      "Population Growth and Technological Change: One Million B.C. to 1990",
    year: 1993,
    journal: "Quarterly Journal of Economics",
    url: "https://faculty.econ.ucdavis.edu/faculty/gclark/210a/readings/kremer1993.pdf",
    topics: ["growth_theory"],
  },
  {
    id: "Zeira1998",
    type: "article",
    author: "Zeira, Joseph",
    title: "Workers, Machines, and Economic Growth",
    year: 1998,
    journal: "Quarterly Journal of Economics",
    url: "https://josephzeira.weebly.com/uploads/5/7/3/4/57342721/98_qje.pdf",
    topics: ["growth_theory", "capital_labor"],
  },
  {
    id: "Acemoglu2003",
    type: "article",
    author: "Acemoglu, Daron",
    title: "Labor- and Capital-Augmenting Technical Change",
    year: 2003,
    journal: "Journal of the European Economic Association",
    url: "https://economics.mit.edu/sites/default/files/publications/labor-and-capital-augmenting.pdf",
    topics: ["capital_labor", "growth_theory"],
  },
  {
    id: "Nordhaus2004",
    type: "techreport",
    author: "Nordhaus, William D.",
    title: "Schumpeterian Profits in the American Economy",
    year: 2004,
    institution: "NBER",
    number: "10433",
    url: "https://www.nber.org/papers/w10433",
    topics: ["growth_theory"],
  },
  {
    id: "Agrawal2019",
    type: "techreport",
    author: "Agrawal, Ajay and Gans, Joshua S. and Goldfarb, Avi",
    title:
      "Exploring the Impact of Artificial Intelligence: Prediction versus Judgment",
    year: 2019,
    institution: "NBER",
    number: "24541",
    url: "https://www.nber.org/papers/w24541",
    topics: ["growth_theory"],
  },
  {
    id: "PWBM2025",
    type: "techreport",
    author: "Penn Wharton Budget Model",
    title: "Projected Impact of Generative AI on Future Productivity Growth",
    year: 2025,
    institution: "Penn Wharton Budget Model",
    url: "https://budgetmodel.wharton.upenn.edu/issues/2025/9/8/projected-impact-of-generative-ai-on-future-productivity-growth",
    topics: ["growth_theory", "general_equilibrium"],
    summary:
      "Generative AI projected to raise US GDP 1.5% by 2035, ~3% by 2055. About 40% of current GDP could be substantially affected.",
  },
  {
    id: "GoldmanSachs2023",
    type: "techreport",
    author:
      "Hatzius, Jan and Briggs, Joseph and Kodnani, Devesh and Pierdomenico, Giovanni",
    title:
      "The Potentially Large Effects of Artificial Intelligence on Economic Growth",
    year: 2023,
    institution: "Goldman Sachs Economic Research",
    url: "https://www.gspublishing.com/content/research/en/reports/2023/03/27/d64e052b-0f6e-45d7-967b-d7be35fabd16.html",
    topics: ["growth_theory"],
    summary:
      "Industry baseline often cited by policy shops: GenAI could raise global GDP by ~7% over 10 years and exposes a quarter of work to automation.",
  },
  {
    id: "WEF2025",
    type: "techreport",
    author: "World Economic Forum",
    title: "Future of Jobs Report 2025",
    year: 2025,
    institution: "World Economic Forum",
    url: "https://www.weforum.org/publications/the-future-of-jobs-report-2025/",
    topics: ["ai_adoption"],
    summary:
      "Global employer survey: 22% structural labor-market churn through 2030, with AI a top driver. 92M jobs displaced, 170M created on net.",
  },
  {
    id: "McKinsey2023",
    type: "techreport",
    author: "McKinsey Global Institute",
    title:
      "The Economic Potential of Generative AI: The Next Productivity Frontier",
    year: 2023,
    institution: "McKinsey & Company",
    url: "https://www.mckinsey.com/capabilities/mckinsey-digital/our-insights/the-economic-potential-of-generative-ai-the-next-productivity-frontier",
    topics: ["growth_theory", "productivity_empirical"],
    summary:
      "Often-cited industry estimate of $2.6-4.4T per year in productivity from generative AI across 63 use cases.",
  },

  // -------------------------------------------------------------------------
  // Capital, labor, Piketty debate
  // -------------------------------------------------------------------------
  {
    id: "TrammellandPatel2025",
    type: "misc",
    author: "Trammell, Philip and Patel, Dwarkesh",
    title: "Capital in the 22nd Century",
    year: 2025,
    note: "Trammell Substack",
    url: "https://philiptrammell.substack.com/p/capital-in-the-22nd-century",
    topics: ["capital_labor", "tax_policy", "scenarios"],
    summary:
      "Argues AI will let capital fully substitute for labor, producing Piketty-style inequality spirals. Calls for progressive capital and rent taxation as the central policy response.",
  },
  {
    id: "TrammellandKorinek2023",
    type: "techreport",
    author: "Trammell, Philip and Korinek, Anton",
    title: "Economic Growth under Transformative AI",
    year: 2023,
    institution: "NBER",
    number: "31815",
    url: "https://www.nber.org/papers/w31815",
    topics: ["growth_theory", "transformative_ai", "capital_labor"],
    summary:
      "Survey of growth-model results under transformative AI: the elasticity of substitution between capital and labor is the single most decisive parameter.",
  },
  {
    id: "MookherjeeandRay2022",
    type: "article",
    author: "Mookherjee, Dilip and Ray, Debraj",
    title: "Capital-Labor Substitution, Inequality, and Growth",
    year: 2022,
    journal: "Research in Economics",
    url: "https://www.sciencedirect.com/science/article/pii/S1094202521000661",
    topics: ["capital_labor", "growth_theory"],
  },
  {
    id: "SachsandKotlikoff2012",
    type: "techreport",
    author: "Sachs, Jeffrey D. and Kotlikoff, Laurence J.",
    title: "Smart Machines and Long-Term Misery",
    year: 2012,
    institution: "NBER",
    number: "18629",
    url: "https://www.nber.org/papers/w18629",
    topics: ["capital_labor", "general_equilibrium", "inequality_distribution"],
    summary:
      "OLG model where smart machines depress wages enough that younger generations save less, driving long-run capital and consumption decline. An early formal warning shot.",
  },
  {
    id: "KorinekandStiglitz2021",
    type: "techreport",
    author: "Korinek, Anton and Stiglitz, Joseph E.",
    title:
      "Artificial Intelligence and Its Implications for Income Distribution and Unemployment",
    year: 2021,
    institution: "NBER",
    number: "28453",
    url: "https://www.nber.org/papers/w28453",
    topics: ["capital_labor", "inequality_distribution"],
    summary:
      "Foundational analytic taxonomy: AI may raise productivity yet immiserate workers if technical change is sufficiently labor-replacing. Lays out the policy menu.",
  },
  {
    id: "KorinekandJuelfs2024",
    type: "article",
    author: "Korinek, Anton and Juelfs, Megan",
    title: "Preparing for the (Non-Existent?) Future of Work",
    year: 2024,
    journal: "Annual Review of Economics",
    volume: 16,
    doi: "10.1146/annurev-economics-082423-110506",
    url: "https://www.annualreviews.org/doi/10.1146/annurev-economics-082423-110506",
    topics: ["capital_labor", "ubi_transfers"],
    summary:
      "Reviews policy options if AI hollows out the demand for human labor: human-complementing innovation policy, income support, and redistribution of capital ownership.",
  },
  {
    id: "KorinekandSuh2024",
    type: "techreport",
    author: "Korinek, Anton and Suh, Donghyun",
    title: "Scenarios for the Transition to AGI",
    year: 2024,
    institution: "NBER",
    number: "32255",
    url: "https://www.nber.org/papers/w32255",
    topics: ["scenarios", "growth_theory", "capital_labor"],
    summary:
      "Maps AGI transition into a 2x2 of timeline and substitutability. Output growth, wages, and income shares all turn on those two dials.",
  },
  {
    id: "Jones2024",
    type: "article",
    author: "Jones, Charles I.",
    title: "The AI Dilemma: Growth versus Existential Risk",
    year: 2024,
    journal: "American Economic Review: Insights",
    doi: "10.1257/aeri.20230570",
    url: "https://www.aeaweb.org/articles?id=10.1257/aeri.20230570",
    topics: ["growth_theory", "existential_risk"],
  },
  {
    id: "TrammellandAschenbrenner2025",
    type: "article",
    author: "Trammell, Philip and Aschenbrenner, Leopold",
    title: "Existential Risk and Growth",
    year: 2025,
    url: "https://philiptrammell.com/static/Existential_Risk_and_Growth.pdf",
    topics: ["growth_theory", "existential_risk"],
  },
  {
    id: "AcemogluandLensman2024",
    type: "article",
    author: "Acemoglu, Daron and Lensman, Todd",
    title: "Regulating Transformative Technologies",
    year: 2024,
    url: "https://economics.mit.edu/sites/default/files/2024-10/Regulating%20Transformative%20Technologies.pdf",
    topics: ["existential_risk", "tax_policy"],
  },
  {
    id: "Sotala2012",
    type: "article",
    author: "Sotala, Kaj",
    title: "Advantages of Artificial Intelligences, Uploads, and Digital Minds",
    year: 2012,
    journal: "International Journal of Machine Consciousness",
    url: "https://intelligence.org/files/AdvantagesOfAIs.pdf",
    topics: ["existential_risk"],
  },
  {
    id: "Bostrom2003",
    type: "article",
    author: "Bostrom, Nick",
    title:
      "Astronomical Waste: The Opportunity Cost of Delayed Technological Development",
    year: 2003,
    journal: "Utilitas",
    url: "https://nickbostrom.com/papers/astronomical-waste/",
    topics: ["existential_risk"],
  },
  {
    id: "Nordhaus2009",
    type: "article",
    author: "Nordhaus, William D.",
    title: "The Economics of an Integrated World Carbon Dioxide Market",
    year: 2009,
    url: "https://elischolar.library.yale.edu/cgi/viewcontent.cgi?article=3002&context=cowles-discussion-paper-series",
    topics: ["existential_risk"],
  },
  {
    id: "Beckstead2013",
    type: "article",
    author: "Beckstead, Nick",
    title: "On the Overwhelming Importance of Shaping the Far Future",
    year: 2013,
    url: "https://80000hours.org/wp-content/uploads/2022/01/Beckstead-Nick-On-the-Overwhelming-Importance-of-Shaping-the-Far-Future-better-formatting.pdf",
    topics: ["existential_risk"],
  },
  {
    id: "GreavesandMacAskill2021",
    type: "article",
    author: "Greaves, Hilary and MacAskill, William",
    title: "The Case for Strong Longtermism",
    year: 2021,
    institution: "Global Priorities Institute",
    url: "https://globalprioritiesinstitute.org/wp-content/uploads/The-Case-for-Strong-Longtermism-GPI-Working-Paper-June-2021-2-2.pdf",
    topics: ["existential_risk"],
  },

  // -------------------------------------------------------------------------
  // Inequality and distribution
  // -------------------------------------------------------------------------
  {
    id: "Rockalletal2025",
    type: "techreport",
    author: "Rockall, Erik and Tavares, Marina M. and Pizzinelli, Carlo",
    title: "AI Adoption and Inequality",
    year: 2025,
    institution: "IMF",
    number: "WP/25/68",
    url: "https://www.imf.org/en/publications/wp/issues/2025/04/04/ai-adoption-and-inequality-565729",
    topics: ["inequality_distribution", "capital_labor"],
    summary:
      "AI can reduce wage inequality (because high-income tasks are most exposed) but reliably raises capital-income and wealth inequality. The wealth channel always dominates over time.",
  },
  {
    id: "CazzanigaIMF2024",
    type: "techreport",
    author:
      "Cazzaniga, Mauro and Jaumotte, Florence and Li, Longji and Melina, Giovanni and Panton, Augustus J. and Pizzinelli, Carlo and Rockall, Emma and Tavares, Marina M.",
    title: "Gen-AI: Artificial Intelligence and the Future of Work",
    year: 2024,
    institution: "IMF",
    number: "SDN/2024/001",
    url: "https://www.imf.org/en/Publications/Staff-Discussion-Notes/Issues/2024/01/14/Gen-AI-Artificial-Intelligence-and-the-Future-of-Work-542379",
    topics: ["inequality_distribution"],
    summary:
      "Globally, ~40% of jobs are exposed to AI; in advanced economies, ~60%. About half of exposed jobs benefit and half face displacement risk.",
  },
  {
    id: "OECD2024",
    type: "techreport",
    author: "OECD",
    title: "What Impact Has AI Had on Wage Inequality?",
    year: 2024,
    institution: "OECD",
    url: "https://www.oecd.org/en/publications/what-impact-has-ai-had-on-wage-inequality_7fb21f59-en.html",
    topics: ["inequality_distribution"],
  },
  {
    id: "GovAI2025",
    type: "techreport",
    author: "GovAI",
    title: "AI's Impact on Income Inequality in the US",
    year: 2025,
    institution: "GovAI",
    url: "https://www.governance.ai/research-paper/ais-impact-on-income-inequality-in-the-us",
    topics: ["inequality_distribution"],
  },
  {
    id: "BenzellKotlikoffYe2025",
    type: "article",
    author: "Benzell, Seth G. and Kotlikoff, Laurence J. and Ye, Yifan",
    title: "The Future of Global Economic Power",
    year: 2025,
    journal: "Oxford Review of Economic Policy",
    url: "https://digitalcommons.chapman.edu/economics_articles/288/",
    topics: ["general_equilibrium", "inequality_distribution"],
  },

  // -------------------------------------------------------------------------
  // Tax policy and UBI
  // -------------------------------------------------------------------------
  {
    id: "BrookingsTaxPolicy2026",
    type: "article",
    author: "Brookings Institution",
    title:
      "The Future of Tax Policy: A Public Finance Framework for the Age of AI",
    year: 2026,
    institution: "Brookings Institution",
    url: "https://www.brookings.edu/articles/future-tax-policy-a-public-finance-framework-for-the-age-of-ai/",
    topics: ["tax_policy"],
    summary:
      "AI erodes labor-based tax revenue. Argues consumption taxation becomes the primary instrument; some reforms make sense now, others would be premature.",
  },
  {
    id: "AcemogluManeraRestrepo2020",
    type: "article",
    author: "Acemoglu, Daron and Manera, Andrea and Restrepo, Pascual",
    title: "Does the U.S. Tax Code Favor Automation?",
    year: 2020,
    journal: "Brookings Papers on Economic Activity",
    note: "Spring 2020",
    url: "https://www.brookings.edu/wp-content/uploads/2020/03/Acemoglu-et-al-final-paper.pdf",
    topics: ["tax_policy", "capital_labor"],
    summary:
      "Documents that the US tax code over-subsidizes capital relative to labor, distorting automation choices. The headline pre-AI policy paper on this debate.",
  },
  {
    id: "RAND2025",
    type: "techreport",
    author: "RAND Corporation",
    title: "Managing AI's Economic Future",
    year: 2025,
    institution: "RAND",
    number: "RRA3764-1",
    url: "https://www.rand.org/pubs/research_reports/RRA3764-1.html",
    topics: ["tax_policy", "ubi_transfers"],
    summary:
      "Recommends an asymmetric automation policy: incentivize vertical (deepening) automation while moderating horizontal (broad replacement) expansion.",
  },

  // -------------------------------------------------------------------------
  // Microsimulation methodology
  // -------------------------------------------------------------------------
  {
    id: "BourguignonandSpadaro2006",
    type: "article",
    author: "Bourguignon, François and Spadaro, Amedeo",
    title: "Microsimulation as a Tool for Evaluating Redistribution Policies",
    year: 2006,
    journal: "Journal of Economic Inequality",
    volume: 4,
    pages: "77-106",
    doi: "10.1007/s10888-005-9012-6",
    url: "https://link.springer.com/article/10.1007/s10888-005-9012-6",
    topics: ["microsimulation"],
    summary:
      "Standard reference on the methodology of static and behavioral tax-benefit microsimulation for distributional analysis.",
  },
  {
    id: "SutherlandandFigari2013",
    type: "article",
    author: "Sutherland, Holly and Figari, Francesco",
    title: "EUROMOD: The European Union Tax-Benefit Microsimulation Model",
    year: 2013,
    journal: "International Journal of Microsimulation",
    volume: 6,
    number: 1,
    pages: "4-26",
    url: "https://www.microsimulation.pub/articles/00075",
    topics: ["microsimulation"],
    summary:
      "Documents EUROMOD, the cross-country tax-benefit microsimulation infrastructure that has set the methodological bar in Europe for two decades.",
  },

  // -------------------------------------------------------------------------
  // Stochastic forecasting methodology
  // -------------------------------------------------------------------------
  {
    id: "AdrianBoyarchenkoGiannone2019",
    type: "article",
    author: "Adrian, Tobias and Boyarchenko, Nina and Giannone, Domenico",
    title: "Vulnerable Growth",
    year: 2019,
    journal: "American Economic Review",
    volume: 109,
    number: 4,
    pages: "1263-1289",
    doi: "10.1257/aer.20161923",
    url: "https://www.aeaweb.org/articles?id=10.1257/aer.20161923",
    topics: ["stochastic_forecasting"],
    summary:
      "Growth-at-risk methodology: models the full conditional distribution of future GDP, not just the mean. Underpins the NY Fed's Outlook-at-Risk approach.",
  },

  // -------------------------------------------------------------------------
  // UK evidence
  // -------------------------------------------------------------------------
  {
    id: "IPPR2024",
    type: "techreport",
    author: "Jung, Carsten and Desai, Bhargav",
    title:
      "Transformed by AI: How Generative Artificial Intelligence Could Affect Work in the UK",
    year: 2024,
    institution: "Institute for Public Policy Research",
    url: "https://www.ippr.org/articles/transformed-by-ai",
    topics: ["uk"],
    summary:
      "IPPR estimates 11% of UK tasks are exposed to current generative AI, rising to 59% under deeper integration. Central second-wave scenario: 4.4M jobs displaced, £144bn annual GDP gains.",
  },
  {
    id: "GovUKAIExposure2023",
    type: "techreport",
    author: "Department for Education (UK)",
    title: "The Impact of AI on UK Jobs and Training",
    year: 2023,
    institution: "GOV.UK",
    url: "https://www.gov.uk/government/publications/the-impact-of-ai-on-uk-jobs-and-training",
    topics: ["uk", "exposure_measurement"],
    summary:
      "UK government exposure study: professional occupations, finance, information and communication, education, and London are relatively more exposed to AI.",
  },
  {
    id: "GovUKAISkills2026",
    type: "techreport",
    author: "Department for Education (UK)",
    title: "AI Skills for Life and Work: Labour Market and Skills Projections",
    year: 2026,
    institution: "GOV.UK",
    url: "https://www.gov.uk/government/publications/ai-skills-for-life-and-work-labour-market-and-skills-projections",
    topics: ["uk"],
    summary:
      "Projects UK jobs directly involving AI activities rising from 158,000 in 2024 to 3.9M by 2035 under the adjusted Technological Opportunities scenario.",
  },
  {
    id: "GovUKAIActionPlan2026",
    type: "techreport",
    author: "GOV.UK",
    title: "AI Opportunities Action Plan: One Year On",
    year: 2026,
    institution: "GOV.UK",
    url: "https://www.gov.uk/government/publications/ai-opportunities-action-plan-one-year-on/ai-opportunities-action-plan-one-year-on",
    topics: ["uk"],
    summary:
      "Reports on the UK's Future of Work Unit and progress toward upskilling 10M workers in AI by 2030.",
  },
  {
    id: "PwC2025",
    type: "techreport",
    author: "PwC United Kingdom",
    title: "AI Jobs Barometer: UK Edition",
    year: 2025,
    institution: "PwC",
    url: "https://www.pwc.co.uk/press-room/press-releases/research-commentary/2024/ai-exposed-sectors-see-pay-and-productivity-uplift--but-job-open.html",
    topics: ["uk"],
    summary:
      "11% wage premium for UK roles requiring AI skills; vacancies in AI-exposed occupations grew 12% from 2019-2024 vs. 50% for less-exposed occupations.",
  },

  // -------------------------------------------------------------------------
  // Scenarios and meta
  // -------------------------------------------------------------------------
  {
    id: "ConvergenceAnalysis2025",
    type: "techreport",
    author: "Convergence Analysis",
    title: "Threshold 2030: Comprehensive Summary",
    year: 2025,
    institution: "Convergence Analysis",
    url: "https://www.convergenceanalysis.org/threshold-2030/comprehensive-summary",
    topics: ["scenarios"],
  },
  {
    id: "BrynjolfssonKorinekAgrawal2025",
    type: "techreport",
    author: "Brynjolfsson, Erik and Korinek, Anton and Agrawal, Ajay",
    title: "Nine Grand Challenges for the Economics of Artificial Intelligence",
    year: 2025,
    institution: "NBER",
    number: "34256",
    url: "https://www.nber.org/papers/w34256",
    topics: ["growth_theory", "inequality_distribution"],
    summary:
      "Research agenda from three leading economists. Calls out probabilistic policy analysis, distributional outcomes, and capital-share dynamics as priority gaps.",
  },
  {
    id: "TrammellandMazlish2025",
    type: "misc",
    author: "Trammell, Philip and Mazlish, Zach",
    title: "Economics of Transformative AI Course Materials",
    year: 2025,
    note: "Two-week summer program hosted at the Stanford Digital Economy Lab, August 16-29, 2025",
    url: "https://digitaleconomy.stanford.edu/programs/economics-of-transformative-ai/",
    topics: ["transformative_ai", "growth_theory"],
  },
];

/**
 * Get reference by ID.
 */
export function getReferenceById(id) {
  return references.find((ref) => ref.id === id);
}

/**
 * Get references for a topic, in display order (year desc, then author).
 */
export function getReferencesByTopic(topic) {
  return references
    .filter((ref) => (ref.topics ?? []).includes(topic))
    .sort((a, b) => {
      if (b.year !== a.year) return b.year - a.year;
      return a.author.localeCompare(b.author);
    });
}

/**
 * Get all references sorted by year (desc) then author.
 */
export function getAllReferences() {
  return [...references].sort((a, b) => {
    if (b.year !== a.year) return b.year - a.year;
    return a.author.localeCompare(b.author);
  });
}

/**
 * Get references by BibTeX-style type.
 */
export function getReferencesByType(type) {
  return references.filter((ref) => ref.type === type);
}

/**
 * Format author names for display (passthrough today, but a single
 * formatting hook lets the call sites stay simple).
 */
export function formatAuthors(authorString) {
  return authorString;
}

/**
 * Generate an APA-style citation string. HTML-safe except for the journal
 * name, which is emitted in <em>...</em>.
 */
export function formatAPACitation(reference) {
  const {
    author,
    year,
    title,
    journal,
    volume,
    number,
    pages,
    institution,
    note,
  } = reference;

  let citation = `${author} (${year}).`;

  if (title) {
    citation += ` ${title}.`;
  }

  if (journal) {
    citation += ` <em>${journal}</em>`;
    if (volume) citation += `, ${volume}`;
    if (number) citation += `(${number})`;
    if (pages) citation += `, ${pages}`;
    citation += ".";
  }

  if (institution && reference.type === "techreport") {
    citation += ` ${institution}`;
    if (reference.number) citation += ` Working Paper ${reference.number}`;
    citation += ".";
  }

  if (note) {
    citation += ` ${note}.`;
  }

  return citation;
}

/**
 * Generate a BibTeX entry.
 */
export function formatBibTeX(reference) {
  const {
    id,
    type,
    author,
    title,
    year,
    journal,
    volume,
    number,
    pages,
    institution,
    note,
    doi,
    url,
  } = reference;

  let bibtex = `@${type}{${id},\n`;
  if (author) bibtex += `  author = {${author}},\n`;
  if (title) bibtex += `  title = {${title}},\n`;
  if (journal) bibtex += `  journal = {${journal}},\n`;
  if (institution) bibtex += `  institution = {${institution}},\n`;
  if (year) bibtex += `  year = {${year}},\n`;
  if (volume) bibtex += `  volume = {${volume}},\n`;
  if (number) bibtex += `  number = {${number}},\n`;
  if (pages) bibtex += `  pages = {${pages}},\n`;
  if (note) bibtex += `  note = {${note}},\n`;
  if (doi) bibtex += `  doi = {${doi}},\n`;
  if (url) bibtex += `  url = {${url}},\n`;
  bibtex += "}";

  return bibtex;
}
