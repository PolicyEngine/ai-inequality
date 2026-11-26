import {
  cite,
  formatAPACitation,
  formatAuthors,
  formatBibTeX,
  formatInTextCitation,
  getReferenceById,
  references,
} from "./references";

test("reference ids are unique and every entry has the fields the site renders", () => {
  const ids = references.map((ref) => ref.id);
  expect(new Set(ids).size).toBe(ids.length);
  references.forEach((ref) => {
    expect(ref.author, ref.id).toBeTruthy();
    expect(ref.title, ref.id).toBeTruthy();
    expect(ref.year, ref.id).toEqual(expect.any(Number));
    expect(ref.url, ref.id).toMatch(/^https:\/\//);
    if (ref.site) {
      expect(ref.site, ref.id).toMatch(/^https:\/\//);
      expect(ref.site, ref.id).not.toBe(ref.url);
    }
  });
});

test("formatAuthors abbreviates given names APA-style", () => {
  expect(formatAuthors("Zeira, Joseph")).toBe("Zeira, J.");
  expect(formatAuthors("Korinek, Anton and Stiglitz, Joseph E.")).toBe(
    "Korinek, A., & Stiglitz, J. E.",
  );
  expect(
    formatAuthors(
      "Aghion, Philippe and Jones, Benjamin F. and Jones, Charles I.",
    ),
  ).toBe("Aghion, P., Jones, B. F., & Jones, C. I.");
  expect(formatAuthors("Anthropic")).toBe("Anthropic");
  expect(formatAuthors("Lee, Jean-Pierre")).toBe("Lee, J.-P.");
});

test("formatAuthors keeps braced corporate names whole", () => {
  expect(
    formatAuthors("{Department for Science, Innovation and Technology}"),
  ).toBe("Department for Science, Innovation and Technology");
  expect(
    formatAuthors(
      "{Department for Science, Innovation and Technology} and {Department for Digital, Culture, Media and Sport}",
    ),
  ).toBe(
    "Department for Science, Innovation and Technology, & Department for Digital, Culture, Media and Sport",
  );
  expect(formatInTextCitation(getReferenceById("DSITActionPlan2026"))).toBe(
    "Department for Science, Innovation and Technology (2026)",
  );
});

test("formatAuthors truncates lists longer than twenty names", () => {
  const many = Array.from(
    { length: 22 },
    (_, i) => `Author${i + 1}, Alex`,
  ).join(" and ");
  const first19 = Array.from(
    { length: 19 },
    (_, i) => `Author${i + 1}, A.`,
  ).join(", ");
  expect(formatAuthors(many)).toBe(`${first19}, ... Author22, A.`);
});

test("formatInTextCitation follows one, two, and many-author forms", () => {
  expect(formatInTextCitation(getReferenceById("Zeira1998"))).toBe(
    "Zeira (1998)",
  );
  expect(formatInTextCitation(getReferenceById("KorinekandStiglitz2018"))).toBe(
    "Korinek and Stiglitz (2018)",
  );
  expect(formatInTextCitation(getReferenceById("Chopraetal2025"))).toBe(
    "Chopra et al. (2025)",
  );
  expect(
    formatInTextCitation(getReferenceById("AnthropicEconomicIndex2026")),
  ).toBe("Anthropic (2026)");
});

test("the Iceberg Index entry matches the report and links to iceberg.mit.edu", () => {
  const { ref, label, url } = cite("Chopraetal2025");
  expect(label).toBe("MIT Iceberg Index");
  expect(url).toBe("https://iceberg.mit.edu");
  expect(ref.url).toBe("https://iceberg.mit.edu/report.pdf");
  expect(ref.author).toMatch(/^Chopra, Ayush and /);
  expect(ref.author).toMatch(/Balaprakash, Prasanna$/);
  expect(ref.title).toBe(
    "The Iceberg Index: Measuring Skills-centered Exposure in the AI Economy",
  );
  expect(formatAPACitation(ref)).toBe(
    "Chopra, A., Bhattacharya, S., Salvador, D., Paul, A., Wright, T., Garg, A., Ahmad, F., Schwarze, A. C., Raskar, R., & Balaprakash, P. (2025). The Iceberg Index: Measuring Skills-centered Exposure in the AI Economy. MIT and Oak Ridge National Laboratory.",
  );
});

test("formatAPACitation handles question titles and corporate publishers", () => {
  expect(formatAPACitation(getReferenceById("OECD2024"))).toBe(
    "OECD (2024). What Impact Has AI Had on Wage Inequality?",
  );
  expect(formatAPACitation(getReferenceById("PwC2025"))).toBe(
    "PwC UK (2025). AI-Exposed Sectors See Pay and Productivity Uplift, but Job Openings Rise at Slower Pace. Press release, June 3, 2025, on the 2025 Global AI Jobs Barometer.",
  );
  expect(formatAPACitation(getReferenceById("DSITActionPlan2026"))).toBe(
    "Department for Science, Innovation and Technology (2026). AI Opportunities Action Plan: One Year On. GOV.UK. Published January 29, 2026.",
  );
});

test("cite falls back to the in-text form when an entry has no label", () => {
  const { label, url } = cite("Zeira1998");
  expect(label).toBe("Zeira (1998)");
  expect(url).toBe(getReferenceById("Zeira1998").url);
});

test("cite throws on an unknown id", () => {
  expect(() => cite("NoSuchReference2026")).toThrow(
    "Unknown reference id: NoSuchReference2026",
  );
});

test("formatBibTeX exports bibliographic fields only", () => {
  const bibtex = formatBibTeX(getReferenceById("Chopraetal2025"));
  expect(bibtex).toContain("@techreport{Chopraetal2025,");
  expect(bibtex).toContain("url = {https://iceberg.mit.edu/report.pdf}");
  expect(bibtex).not.toContain("label");
  expect(bibtex).not.toContain("site");
});

test("no reference is attributed to MIT FutureTech", () => {
  references.forEach((ref) => {
    expect(JSON.stringify(ref)).not.toMatch(/futuretech/i);
  });
});
