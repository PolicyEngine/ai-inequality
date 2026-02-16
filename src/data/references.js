/**
 * References database in BibTeX-inspired format
 * Extracted from "Economics of Transformative AI" course materials
 * by Phil Trammell and Zach Mazlish, Stanford Digital Economy Lab, 2025
 *
 * Each reference contains:
 * - id: Unique identifier (convention: LastnameYYYY or LastnameLastnameYYYY)
 * - type: article, book, inproceedings, techreport, misc, etc.
 * - Standard BibTeX fields: author, title, year, journal, etc.
 * - Optional: url, doi, abstract
 */

export const references = [
  {
    id: "TrammellandMazlish2025",
    type: "misc",
    author: "Trammell, Philip and Mazlish, Zach",
    title: "Economics of Transformative AI Course Materials",
    year: 2025,
    note: "Two-week summer program hosted at the Stanford Digital Economy Lab, August 16-29, 2025",
    url: "https://docs.google.com/document/d/1hS-Pu0gq22IwB9mWeig8Ui9kvUITgHj9eH3ik2zNVpo",
  },
  {
    id: "Zeira1998",
    type: "article",
    author: "Zeira, Joseph",
    title: "Workers, Machines, and Economic Growth",
    year: 1998,
    journal: "Quarterly Journal of Economics",
    url: "https://josephzeira.weebly.com/uploads/5/7/3/4/57342721/98_qje.pdf",
  },
  {
    id: "Aghion2019",
    type: "article",
    author: "Aghion, Philippe and Jones, Benjamin F. and Jones, Charles I.",
    title: "Artificial Intelligence and Economic Growth",
    year: 2019,
    url: "https://web.stanford.edu/~chadj/AJJ-AIandGrowth.pdf",
  },
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
    url: "https://academic.oup.com/economicpolicy/article/40/121/13/7728473",
  },
  {
    id: "Autor2024",
    type: "techreport",
    author: "Autor, David H.",
    title: "Applying AI to Rebuild Middle Class Jobs",
    year: 2024,
    institution: "NBER",
    number: "32140",
    url: "https://www.nber.org/system/files/working_papers/w32140/w32140.pdf",
  },
  {
    id: "Brynjolfsson2021",
    type: "article",
    author: "Brynjolfsson, Erik and Rock, Daniel and Syverson, Chad",
    title:
      "The Productivity J-Curve: How Intangibles Complement General Purpose Technologies",
    year: 2021,
    journal: "American Economic Journal: Macroeconomics",
    url: "https://pubs.aeaweb.org/doi/pdfplus/10.1257/mac.20180386",
  },
  {
    id: "AghionandBunel2024",
    type: "article",
    author: "Aghion, Philippe and Bunel, Simon",
    title: "AI and Growth",
    year: 2024,
    url: "https://www.frbsf.org/wp-content/uploads/AI-and-Growth-Aghion-Bunel.pdf",
  },
  {
    id: "HumlumandVestergaard2024",
    type: "article",
    author: "Humlum, Anders and Vestergaard, Emilie",
    title:
      "The Impact of ChatGPT on High-Skilled Work: Evidence from Freelancers",
    year: 2024,
    url: "https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID4826800_code1213723.pdf?abstractid=4807516&mirid=1",
  },
  {
    id: "BrynjolfssonChandarandChen2025",
    type: "article",
    author: "Brynjolfsson, Erik and Chandar, Bharat and Chen, Sida",
    title:
      "Canaries in the Coal Mine: Early Indicators of Labor Market Transformation",
    year: 2025,
    url: "https://digitaleconomy.stanford.edu/wp-content/uploads/2025/08/Canaries_BrynjolfssonChandarChen.pdf",
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
  },
  {
    id: "Hanson2001",
    type: "article",
    author: "Hanson, Robin",
    title: "Economic Growth Given Machine Intelligence",
    year: 2001,
    url: "https://mason.gmu.edu/~rhanson/aigrow.pdf",
  },
  {
    id: "Acemoglu2003",
    type: "article",
    author: "Acemoglu, Daron",
    title: "Labor- and Capital-Augmenting Technical Change",
    year: 2003,
    url: "https://economics.mit.edu/sites/default/files/publications/labor-and-capital-augmenting.pdf",
  },
  {
    id: "SachsandKotlikoff2012",
    type: "techreport",
    author: "Sachs, Jeffrey D. and Kotlikoff, Laurence J.",
    title: "Smart Machines and Long-Term Misery",
    year: 2012,
    institution: "NBER",
    number: "18629",
    url: "https://www.nber.org/system/files/working_papers/w18629/revisions/w18629.rev0.pdf",
  },
  {
    id: "Nordhaus2021",
    type: "article",
    author: "Nordhaus, William D.",
    title: "Are We Approaching an Economic Singularity?",
    year: 2021,
    url: "https://williamnordhaus.com/files/williamdnordhaus/files/singularity-2021.pdf",
  },
  {
    id: "MookherjeeandRay2022",
    type: "article",
    author: "Mookherjee, Dilip and Ray, Debraj",
    title: "Capital-Labor Substitution, Inequality, and Growth",
    year: 2022,
    url: "https://www.sciencedirect.com/science/article/pii/S1094202521000661",
  },
  {
    id: "Bessen2018",
    type: "techreport",
    author: "Bessen, James",
    title: "AI and Jobs: The Role of Demand",
    year: 2018,
    institution: "NBER",
    number: "24235",
    url: "https://www.nber.org/system/files/working_papers/w24235/w24235.pdf",
  },
  {
    id: "Sotala2012",
    type: "article",
    author: "Sotala, Kaj",
    title: "Advantages of Artificial Intelligences, Uploads, and Digital Minds",
    year: 2012,
    url: "https://intelligence.org/files/AdvantagesOfAIs.pdf",
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
    url: "https://www.nber.org/system/files/working_papers/w24541/w24541.pdf",
  },
  {
    id: "EthandDavidson2025",
    type: "article",
    author: "Eth, Daniel and Davidson, Tom",
    title: "Will AI R&D Automation Cause a Software Intelligence Explosion?",
    year: 2025,
    url: "https://www.forethought.org/research/will-ai-r-and-d-automation-cause-a-software-intelligence-explosion",
  },
  {
    id: "DavidsonandHoulden2025",
    type: "article",
    author: "Davidson, Tom and Houlden, Tom",
    title: "How Quick and Big Would a Software Intelligence Explosion Be?",
    year: 2025,
    url: "https://www.forethought.org/research/how-quick-and-big-would-a-software-intelligence-explosion-be",
  },
  {
    id: "ErdilandBarnett2025",
    type: "article",
    author: "Erdil, Ege and Barnett, Megan",
    title: "Most AI Value Will Come From Broad Automation, Not from R&D",
    year: 2025,
    url: "https://epoch.ai/gradient-updates/most-ai-value-will-come-from-broad-automation-not-from-r-d",
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
  },
  {
    id: "Roodman2020",
    type: "article",
    author: "Roodman, David",
    title: "Modeling the Human Trajectory",
    year: 2020,
    url: "https://www.openphilanthropy.org/wp-content/uploads/Modeling-the-human-trajectory-2.pdf",
  },
  {
    id: "Davidson2021",
    type: "article",
    author: "Davidson, Tom",
    title: "Could Advanced AI Drive Explosive Economic Growth?",
    year: 2021,
    url: "https://www.openphilanthropy.org/research/could-advanced-ai-drive-explosive-economic-growth/",
  },
  {
    id: "DavidsonandHadshar2025",
    type: "article",
    author: "Davidson, Tom and Hadshar, Lukas",
    title: "The Industrial Explosion",
    year: 2025,
    url: "https://www.forethought.org/research/the-industrial-explosion",
  },
  {
    id: "Villalobos2023",
    type: "article",
    author: "Villalobos, Pablo",
    title: "Scaling Laws Literature Review",
    year: 2023,
    url: "https://epoch.ai/blog/scaling-laws-literature-review",
  },
  {
    id: "Nordhaus2004",
    type: "techreport",
    author: "Nordhaus, William D.",
    title: "Schumpeterian Profits in the American Economy",
    year: 2004,
    institution: "NBER",
    number: "10433",
    url: "https://www.nber.org/system/files/working_papers/w10433/w10433.pdf",
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
    url: "https://www.nber.org/system/files/working_papers/w28453/w28453.pdf",
  },
  {
    id: "Bostrom2003",
    type: "article",
    author: "Bostrom, Nick",
    title:
      "Astronomical Waste: The Opportunity Cost of Delayed Technological Development",
    year: 2003,
    url: "https://nickbostrom.com/papers/astronomical-waste/",
  },
  {
    id: "Nordhaus2009",
    type: "article",
    author: "Nordhaus, William D.",
    title: "The Economics of an Integrated World Carbon Dioxide Market",
    year: 2009,
    url: "https://elischolar.library.yale.edu/cgi/viewcontent.cgi?article=3002&context=cowles-discussion-paper-series",
  },
  {
    id: "Beckstead2013",
    type: "article",
    author: "Beckstead, Nick",
    title: "On the Overwhelming Importance of Shaping the Far Future",
    year: 2013,
    url: "https://80000hours.org/wp-content/uploads/2022/01/Beckstead-Nick-On-the-Overwhelming-Importance-of-Shaping-the-Far-Future-better-formatting.pdf",
  },
  {
    id: "GreavesandMacAskill2021",
    type: "article",
    author: "Greaves, Hilary and MacAskill, William",
    title: "The Case for Strong Longtermism",
    year: 2021,
    url: "https://globalprioritiesinstitute.org/wp-content/uploads/The-Case-for-Strong-Longtermism-GPI-Working-Paper-June-2021-2-2.pdf",
  },
  {
    id: "Jones2024",
    type: "article",
    author: "Jones, Charles I.",
    title: "The AI Dilemma: Growth versus Existential Risk",
    year: 2024,
    journal: "American Economic Review: Insights",
    url: "https://www.aeaweb.org/articles?id=10.1257/aeri.20230570&from=f",
  },
  {
    id: "TrammellandAschenbrenner2025",
    type: "article",
    author: "Trammell, Philip and Aschenbrenner, Leopold",
    title: "Existential Risk and Growth",
    year: 2025,
    url: "https://philiptrammell.com/static/Existential_Risk_and_Growth.pdf",
  },
  {
    id: "AcemogluandLensman2024",
    type: "article",
    author: "Acemoglu, Daron and Lensman, Todd",
    title: "Regulating Transformative Technologies",
    year: 2024,
    url: "https://economics.mit.edu/sites/default/files/2024-10/Regulating%20Transformative%20Technologies.pdf",
  },
  {
    id: "Ahnetal2025",
    type: "article",
    author: "Ahn, Hie Joo and Dillender, Marcus and Kim, Jisoo and Saggio, Raffaele and Wentland, Scott",
    title: "Canaries in the Coal Mine: Early Indicators of AI Labor Market Transformation",
    year: 2025,
    url: "https://digitaleconomy.stanford.edu/publications/canaries-in-the-coal-mine/",
  },
  {
    id: "MITIcebergIndex2025",
    type: "techreport",
    author: "MIT and Oak Ridge National Lab",
    title: "Iceberg Index: Measuring AI's Impact on the Labor Market",
    year: 2025,
    institution: "MIT",
    url: "https://iceberg.mit.edu/report.pdf",
  },
  {
    id: "Rockalletal2025",
    type: "techreport",
    author: "Rockall, Erik and Tavares, Marina M. and Pizzinelli, Carlo",
    title: "AI Adoption and Inequality",
    year: 2025,
    institution: "IMF",
    number: "WP/25/68",
    url: "https://www.imf.org/en/publications/wp/issues/2025/04/04/ai-adoption-and-inequality-565729",
  },
  {
    id: "AnthropicEconomicIndex2026",
    type: "techreport",
    author: "Anthropic",
    title: "Anthropic Economic Index",
    year: 2026,
    institution: "Anthropic",
    url: "https://www.anthropic.com/economic-index",
  },
  {
    id: "PWBM2025",
    type: "techreport",
    author: "Penn Wharton Budget Model",
    title: "Projected Impact of Generative AI on Future Productivity Growth",
    year: 2025,
    institution: "Penn Wharton Budget Model",
    url: "https://budgetmodel.wharton.upenn.edu/issues/2025/9/8/projected-impact-of-generative-ai-on-future-productivity-growth",
  },
  {
    id: "BrookingsTaxPolicy2026",
    type: "article",
    author: "Brookings Institution",
    title: "Future of Tax Policy: A Public Finance Framework for the Age of AI",
    year: 2026,
    url: "https://www.brookings.edu/articles/future-tax-policy-a-public-finance-framework-for-the-age-of-ai/",
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
  },
  {
    id: "Halperinetal2025",
    type: "article",
    author: "Halperin, Basil and Ho, Benjamin and Srinivasan, Akhil and Tao, Siyuan",
    title: "Is Automating AI Research Enough?",
    year: 2025,
    url: "https://www.basilhalperin.com/papers/shs.pdf",
  },
  {
    id: "BenzellKotlikoffYe2025",
    type: "article",
    author: "Benzell, Seth G. and Kotlikoff, Laurence J. and Ye, Yifan",
    title: "The Future of Global Economic Power",
    year: 2025,
    journal: "Oxford Review of Economic Policy",
    url: "https://digitalcommons.chapman.edu/economics_articles/288/",
  },
  {
    id: "Zakeriniaetal2024",
    type: "article",
    author: "Zakerinia, Saeede and Chen, Jingyu and Srinivasan, Suraj",
    title: "Displacement or Complementarity? The Impact of AI on Occupational Tasks",
    year: 2024,
    url: "https://www.hbs.edu/faculty/Pages/item.aspx?num=67045",
  },
  {
    id: "OECD2024",
    type: "techreport",
    author: "OECD",
    title: "What Impact Has AI Had on Wage Inequality?",
    year: 2024,
    institution: "OECD",
    url: "https://www.oecd.org/en/publications/what-impact-has-ai-had-on-wage-inequality_7fb21f59-en.html",
  },
  {
    id: "GovAI2025",
    type: "techreport",
    author: "GovAI",
    title: "AI's Impact on Income Inequality in the US",
    year: 2025,
    institution: "GovAI",
    url: "https://www.governance.ai/research-paper/ais-impact-on-income-inequality-in-the-us",
  },
  {
    id: "ConvergenceAnalysis2025",
    type: "techreport",
    author: "Convergence Analysis",
    title: "Threshold 2030: Comprehensive Summary",
    year: 2025,
    institution: "Convergence Analysis",
    url: "https://www.convergenceanalysis.org/threshold-2030/comprehensive-summary",
  },
];

/**
 * Get reference by ID
 */
export function getReferenceById(id) {
  return references.find((ref) => ref.id === id);
}

/**
 * Get all references sorted by year (descending) then author
 */
export function getAllReferences() {
  return [...references].sort((a, b) => {
    if (b.year !== a.year) {
      return b.year - a.year;
    }
    return a.author.localeCompare(b.author);
  });
}

/**
 * Get references by type
 */
export function getReferencesByType(type) {
  return references.filter((ref) => ref.type === type);
}

/**
 * Format author names for display
 */
export function formatAuthors(authorString) {
  return authorString;
}

/**
 * Generate APA-style citation
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
 * Generate BibTeX entry
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
