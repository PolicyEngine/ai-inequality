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
 *
 * Corporate authors whose names contain commas are wrapped in braces, as in
 * BibTeX: "{Department for Science, Innovation and Technology}".
 *
 * Entries the overview page cites also carry two display fields that never
 * reach the BibTeX export:
 * - label: the short name the page shows next to a figure ("MIT Iceberg Index")
 * - site: the landing page to link when it differs from the document url
 *
 * Components cite an entry through cite(id) so every link, label, and year on
 * the site resolves to one record here.
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
    id: "BrynjolfssonChandarandChen2026",
    type: "techreport",
    author: "Brynjolfsson, Erik and Chandar, Bharat and Chen, Ruyu",
    title:
      "Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of Artificial Intelligence",
    year: 2026,
    institution: "Stanford Digital Economy Lab",
    note: "Working paper, revised August 12, 2026; first version August 2025",
    url: "https://digitaleconomy.stanford.edu/publications/canaries-in-the-coal-mine/",
    label: "Stanford DEL",
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
    id: "KorinekandStiglitz2018",
    type: "techreport",
    author: "Korinek, Anton and Stiglitz, Joseph E.",
    title:
      "Artificial Intelligence and Its Implications for Income Distribution and Unemployment",
    year: 2018,
    institution: "NBER",
    number: "24174",
    url: "https://www.nber.org/papers/w24174",
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
    id: "Chopraetal2025",
    type: "techreport",
    author:
      "Chopra, Ayush and Bhattacharya, Santanu and Salvador, DeAndrea and Paul, Ayan and Wright, Teddy and Garg, Aditi and Ahmad, Feroz and Schwarze, Alice C. and Raskar, Ramesh and Balaprakash, Prasanna",
    title:
      "The Iceberg Index: Measuring Skills-centered Exposure in the AI Economy",
    year: 2025,
    institution: "MIT and Oak Ridge National Laboratory",
    url: "https://iceberg.mit.edu/report.pdf",
    label: "MIT Iceberg Index",
    site: "https://iceberg.mit.edu",
  },
  {
    id: "MinnitiPrettnerandVenturini2025",
    type: "article",
    author: "Minniti, Antonio and Prettner, Klaus and Venturini, Francesco",
    title: "AI Innovation and the Labor Share in European Regions",
    year: 2025,
    journal: "European Economic Review",
    volume: 177,
    pages: "105043",
    url: "https://www.sciencedirect.com/science/article/pii/S0014292125000935",
    label: "Minniti, Prettner & Venturini",
  },
  {
    id: "Rockalletal2025",
    type: "techreport",
    author: "Rockall, Erik and Tavares, Marina M. and Pizzinelli, Carlo",
    title: "AI Adoption and Inequality",
    year: 2025,
    institution: "IMF",
    number: "WP/25/68",
    url: "https://www.imf.org/en/Publications/WP/Issues/2025/04/04/AI-Adoption-and-Inequality-565729",
    label: "IMF",
  },
  {
    id: "AnthropicEconomicIndex2026",
    type: "techreport",
    author: "Anthropic",
    title:
      "Anthropic Economic Index: New Building Blocks for Understanding AI Use",
    year: 2026,
    institution: "Anthropic",
    note: "January 15, 2026",
    url: "https://www.anthropic.com/research/economic-index-primitives",
    label: "Anthropic Economic Index",
  },
  {
    id: "PWBM2025",
    type: "techreport",
    author: "Penn Wharton Budget Model",
    title:
      "The Projected Impact of Generative AI on Future Productivity Growth",
    year: 2025,
    institution: "Penn Wharton Budget Model",
    note: "September 8, 2025",
    url: "https://budgetmodel.wharton.upenn.edu/issues/2025/9/8/projected-impact-of-generative-ai-on-future-productivity-growth",
    label: "Penn Wharton Budget Model",
  },
  {
    id: "KorinekandLockwood2026",
    type: "misc",
    author: "Korinek, Anton and Lockwood, Lee M.",
    title:
      "The Future of Tax Policy: A Public Finance Framework for the Age of AI",
    year: 2026,
    note: "Brookings Institution, January 8, 2026",
    url: "https://www.brookings.edu/articles/future-tax-policy-a-public-finance-framework-for-the-age-of-ai/",
    label: "Brookings",
  },
  {
    id: "BrynjolfssonKorinekAgrawal2025",
    label: "Brynjolfsson, Korinek & Agrawal",
    type: "techreport",
    author: "Brynjolfsson, Erik and Korinek, Anton and Agrawal, Ajay",
    title: "A Research Agenda for the Economics of Transformative AI",
    year: 2025,
    institution: "NBER",
    number: "34256",
    url: "https://www.nber.org/papers/w34256",
  },
  {
    id: "Halperinetal2025",
    type: "article",
    author:
      "Halperin, Basil and Ho, Benjamin and Srinivasan, Akhil and Tao, Siyuan",
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
    title:
      "Displacement or Complementarity? The Impact of AI on Occupational Tasks",
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
  {
    id: "IPPR2024",
    type: "techreport",
    author: "IPPR",
    title:
      "Up to 8 Million UK Jobs at Risk from AI Unless Government Acts, Finds IPPR",
    year: 2024,
    institution: "Institute for Public Policy Research",
    note: "Press release, March 27, 2024",
    url: "https://www.ippr.org/media-office/up-to-8-million-uk-jobs-at-risk-from-ai-unless-government-acts-finds-ippr",
    label: "IPPR",
  },
  {
    id: "PwC2025",
    type: "techreport",
    author: "PwC UK",
    title:
      "AI-Exposed Sectors See Pay and Productivity Uplift, but Job Openings Rise at Slower Pace",
    year: 2025,
    institution: "PwC UK",
    note: "Press release, June 3, 2025, on the 2025 Global AI Jobs Barometer",
    url: "https://www.pwc.co.uk/press-room/press-releases/research-commentary/2024/ai-exposed-sectors-see-pay-and-productivity-uplift--but-job-open.html",
    label: "PwC UK",
  },
  {
    id: "DfE2023",
    type: "techreport",
    author: "Department for Education",
    title: "The Impact of AI on UK Jobs and Training",
    year: 2023,
    institution: "GOV.UK",
    note: "Published November 28, 2023",
    url: "https://assets.publishing.service.gov.uk/media/656856b8cc1ec500138eef49/Gov.UK_Impact_of_AI_on_UK_Jobs_and_Training.pdf",
    label: "GOV.UK / DfE",
  },
  {
    id: "DSITActionPlan2026",
    type: "techreport",
    author: "{Department for Science, Innovation and Technology}",
    title: "AI Opportunities Action Plan: One Year On",
    year: 2026,
    institution: "GOV.UK",
    note: "Published January 29, 2026",
    url: "https://www.gov.uk/government/publications/ai-opportunities-action-plan-one-year-on/ai-opportunities-action-plan-one-year-on",
    label: "GOV.UK AI Opportunities Action Plan",
  },
  {
    id: "AISkillsProjections2026",
    type: "techreport",
    author:
      "{Department for Science, Innovation and Technology} and {Department for Digital, Culture, Media and Sport}",
    title: "AI Skills for Life and Work: Labour Market and Skills Projections",
    year: 2026,
    institution: "GOV.UK",
    note: "Published January 28, 2026",
    url: "https://www.gov.uk/government/publications/ai-skills-for-life-and-work-labour-market-and-skills-projections/ai-skills-for-life-and-work-labour-market-and-skills-projections",
    label: "GOV.UK AI skills projections",
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
    return a.author
      .replace(/[{}]/g, "")
      .localeCompare(b.author.replace(/[{}]/g, ""));
  });
}

/**
 * Get references by type
 */
export function getReferencesByType(type) {
  return references.filter((ref) => ref.type === type);
}

/**
 * Split a BibTeX author string ("Last, First and Last, First") into names.
 * An " and " inside braces belongs to a corporate name and does not split.
 */
export function splitAuthors(authorString) {
  const names = [];
  let depth = 0;
  let current = "";
  for (let i = 0; i < authorString.length; i += 1) {
    const char = authorString[i];
    if (char === "{") depth += 1;
    if (char === "}") depth -= 1;
    if (
      depth === 0 &&
      /\s/.test(char) &&
      /^and\s/.test(authorString.slice(i + 1))
    ) {
      names.push(current);
      current = "";
      i += 4;
      continue;
    }
    current += char;
  }
  names.push(current);
  return names.map((name) => name.trim()).filter(Boolean);
}

function parseAuthor(name) {
  if (name.startsWith("{") && name.endsWith("}")) {
    return { family: name.slice(1, -1), initials: "" };
  }
  const comma = name.indexOf(",");
  if (comma === -1) {
    return { family: name, initials: "" };
  }
  const family = name.slice(0, comma).trim();
  const initials = name
    .slice(comma + 1)
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((part) =>
      part
        .split("-")
        .map((piece) => `${piece[0]}.`)
        .join("-"),
    )
    .join(" ");
  return { family, initials };
}

/**
 * Format author names APA-style: "Korinek, A., & Stiglitz, J. E."
 * Institutional authors (no comma) pass through unchanged. Lists longer than
 * 20 names show the first 19, an ellipsis, and the last.
 */
export function formatAuthors(authorString) {
  const names = splitAuthors(authorString).map((name) => {
    const { family, initials } = parseAuthor(name);
    return initials ? `${family}, ${initials}` : family;
  });
  if (names.length === 1) {
    return names[0];
  }
  if (names.length > 20) {
    return `${names.slice(0, 19).join(", ")}, ... ${names[names.length - 1]}`;
  }
  return `${names.slice(0, -1).join(", ")}, & ${names[names.length - 1]}`;
}

/**
 * Narrative in-text form: "Chopra et al. (2025)", "Korinek and Stiglitz (2018)".
 */
export function formatInTextCitation(reference) {
  const families = splitAuthors(reference.author).map(
    (name) => parseAuthor(name).family,
  );
  let who = families[0];
  if (families.length === 2) {
    who = `${families[0]} and ${families[1]}`;
  } else if (families.length > 2) {
    who = `${families[0]} et al.`;
  }
  return `${who} (${reference.year})`;
}

/**
 * Resolve a reference for display on the site: the label to show, the page to
 * link, and the record itself. Throws on an unknown id so a typo fails tests
 * instead of shipping a dead link.
 */
export function cite(id) {
  const ref = getReferenceById(id);
  if (!ref) {
    throw new Error(`Unknown reference id: ${id}`);
  }
  return {
    ref,
    label: ref.label ?? formatInTextCitation(ref),
    url: ref.site ?? ref.url,
  };
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

  let citation = `${formatAuthors(author)} (${year}).`;

  if (title) {
    citation += /[.?!]$/.test(title) ? ` ${title}` : ` ${title}.`;
  }

  if (journal) {
    citation += ` <em>${journal}</em>`;
    if (volume) citation += `, ${volume}`;
    if (number) citation += `(${number})`;
    if (pages) citation += `, ${pages}`;
    citation += ".";
  }

  if (
    institution &&
    reference.type === "techreport" &&
    institution !== author.replace(/[{}]/g, "")
  ) {
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
