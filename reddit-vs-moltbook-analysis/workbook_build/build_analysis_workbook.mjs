import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outDir = process.env.ANALYSIS_OUT_DIR ?? path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const workbookPath = path.join(outDir, "reddit_moltbook_question_taxonomy_analysis.xlsx");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];
    if (inQuotes) {
      if (ch === '"' && next === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
    } else {
      if (ch === '"') inQuotes = true;
      else if (ch === ",") {
        row.push(field);
        field = "";
      } else if (ch === "\n") {
        row.push(field);
        rows.push(row);
        row = [];
        field = "";
      } else if (ch !== "\r") field += ch;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows.filter((r) => r.some((c) => String(c).trim() !== ""));
}

async function readCsv(name) {
  const text = await fs.readFile(path.join(outDir, name), "utf8");
  return parseCsv(text);
}

function colName(n) {
  let s = "";
  while (n > 0) {
    const m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = Math.floor((n - m - 1) / 26);
  }
  return s;
}

function rangeFor(rows, start = "A1") {
  const match = start.match(/^([A-Z]+)(\d+)$/);
  const startColLetters = match[1];
  const startRow = Number(match[2]);
  let startCol = 0;
  for (const ch of startColLetters) startCol = startCol * 26 + (ch.charCodeAt(0) - 64);
  const endCol = startCol + rows[0].length - 1;
  const endRow = startRow + rows.length - 1;
  return `${start}:${colName(endCol)}${endRow}`;
}

function typedRows(rows) {
  return rows.map((row, idx) =>
    row.map((v) => {
      if (idx === 0) return v;
      if (v === "") return "";
      const num = Number(v);
      return Number.isFinite(num) && String(v).trim() !== "" ? num : v;
    }),
  );
}

function writeBlock(sheet, start, rows) {
  const range = sheet.getRange(rangeFor(rows, start));
  range.values = typedRows(rows);
  return range;
}

function styleSheet(sheet) {
  sheet.showGridLines = false;
  const used = sheet.getUsedRange();
  if (used) {
    used.format.font = { name: "Aptos", size: 10, color: "#1F2937" };
    used.format.wrapText = true;
  }
}

function styleTable(sheet, rangeAddress, headerFill = "#1F4E79") {
  const range = sheet.getRange(rangeAddress);
  range.format.borders = { preset: "all", style: "thin", color: "#D9E2EC" };
  const header = range.getRow(0);
  header.format.fill = { color: headerFill };
  header.format.font = { bold: true, color: "#FFFFFF" };
  header.format.wrapText = true;
  return range;
}

function setWidths(sheet, widths) {
  for (const [col, width] of Object.entries(widths)) {
    sheet.getRange(`${col}:${col}`).format.columnWidthPx = width;
  }
}

function pct(v) {
  return typeof v === "number" ? `${v.toFixed(1)}%` : v;
}

const datasetSummary = await readCsv("dataset_summary.csv");
const topLevel = await readCsv("top_level_distribution.csv");
const subcats = await readCsv("subcategory_distribution.csv");
const combinedTop = await readCsv("combined_reddit_vs_moltbook_top_level.csv");
const combinedSub = await readCsv("combined_reddit_vs_moltbook_subcategories.csv");
const examples = await readCsv("classification_examples.csv");
const allQuestions = await readCsv("all_classified_questions.csv");

const workbook = Workbook.create();
const dashboard = workbook.worksheets.add("Dashboard");
const summary = workbook.worksheets.add("Dataset Summary");
const top = workbook.worksheets.add("Top Level");
const sub = workbook.worksheets.add("Subcategories");
const ex = workbook.worksheets.add("Examples");
const raw = workbook.worksheets.add("All Questions");

dashboard.getRange("A1").values = [["Reddit Human Software Threads vs Moltbook Agent Questions"]];
dashboard.getRange("A1").format.font = { bold: true, size: 18, color: "#17324D" };
dashboard.mergeCells("A1:H1");
dashboard.getRange("A2").values = [["Analysis uses saved Gemini 2.5 Flash classifications only; no additional model calls were made for comparison."]];
dashboard.mergeCells("A2:H2");

const summaryRows = typedRows(datasetSummary);
writeBlock(summary, "A1", datasetSummary);
styleTable(summary, rangeFor(datasetSummary, "A1"));
summary.tables.add(rangeFor(datasetSummary, "A1"), true, "DatasetSummaryTable");
summary.freezePanes.freezeRows(1);
setWidths(summary, { A: 210, B: 90, C: 90, D: 100, E: 80, F: 80, G: 80 });

writeBlock(top, "A1", topLevel);
styleTable(top, rangeFor(topLevel, "A1"));
top.tables.add(rangeFor(topLevel, "A1"), true, "TopLevelDistributionTable");
top.freezePanes.freezeRows(1);
setWidths(top, { A: 190, B: 90, C: 80, D: 90 });

writeBlock(sub, "A1", subcats);
styleTable(sub, rangeFor(subcats, "A1"));
sub.tables.add(rangeFor(subcats, "A1"), true, "SubcategoryDistributionTable");
sub.freezePanes.freezeRows(1);
setWidths(sub, { A: 190, B: 250, C: 80, D: 90 });

writeBlock(ex, "A1", examples);
styleTable(ex, rangeFor(examples, "A1"));
ex.tables.add(rangeFor(examples, "A1"), true, "ExamplesTable");
ex.freezePanes.freezeRows(1);
setWidths(ex, { A: 180, B: 520, C: 70, D: 220, E: 360 });

writeBlock(raw, "A1", allQuestions);
styleTable(raw, rangeFor(allQuestions, "A1"), "#374151");
raw.tables.add(rangeFor(allQuestions, "A1"), true, "AllQuestionsTable");
raw.freezePanes.freezeRows(1);
setWidths(raw, { A: 180, B: 80, C: 580, D: 70, E: 220, F: 70 });

// Dashboard KPI blocks
const dashSummary = [
  ["Dataset", "Questions", "LLQ %", "DRQ %", "GDQ %"],
  ...summaryRows.slice(1).map((r) => [r[0], r[1], r[4], r[5], r[6]]),
];
writeBlock(dashboard, "A4", dashSummary);
styleTable(dashboard, rangeFor(dashSummary, "A4"));

const topRows = typedRows(combinedTop);
dashboard.getRange("A11").values = [["Combined Reddit vs Moltbook: Top-Level Delta"]];
dashboard.getRange("A11").format.font = { bold: true, size: 13, color: "#17324D" };
writeBlock(dashboard, "A12", combinedTop);
styleTable(dashboard, rangeFor(combinedTop, "A12"), "#2563EB");

const subRows = typedRows(combinedSub);
const subDash = [combinedSub[0], ...combinedSub.slice(1, 13)];
dashboard.getRange("A18").values = [["Largest Subcategory Differences"]];
dashboard.getRange("A18").format.font = { bold: true, size: 13, color: "#17324D" };
writeBlock(dashboard, "A19", subDash);
styleTable(dashboard, rangeFor(subDash, "A19"), "#047857");

dashboard.getRange("H4").values = [["Key Takeaways"], ["1. Reddit combined and Moltbook are both majority LLQ."], ["2. CMS Reddit has the highest DRQ share."], ["3. Reddit has many more verification and feature-specification questions."], ["4. Moltbook has far more disjunctive and procedural/design-process questions."]];
dashboard.getRange("H4:H8").format.fill = { color: "#F8FAFC" };
dashboard.getRange("H4").format.font = { bold: true, color: "#17324D" };
dashboard.getRange("H4:H8").format.borders = { preset: "outside", style: "thin", color: "#CBD5E1" };
setWidths(dashboard, { A: 210, B: 95, C: 95, D: 95, E: 95, F: 95, G: 95, H: 390 });

// Chart helper ranges, kept outside the visible dashboard area.
const topChart = [["Label", "Reddit Combined %", "Moltbook %"], ...topRows.slice(1).map((r) => [r[0], r[2], r[4]])];
writeBlock(dashboard, "R4", topChart);
const chart1 = dashboard.charts.add("bar", dashboard.getRange(rangeFor(topChart, "R4")));
chart1.title = "Top-Level Category Mix";
chart1.hasLegend = true;
chart1.xAxis = { axisType: "textAxis" };
chart1.yAxis = { numberFormatCode: "0.0" };
chart1.setPosition("J4", "Q20");

const subChart = [["Subcategory", "Delta pp"], ...subRows.slice(1, 11).map((r) => [String(r[0]).slice(0, 28), r[5]])];
writeBlock(dashboard, "R10", subChart);
const chart2 = dashboard.charts.add("bar", dashboard.getRange(rangeFor(subChart, "R10")));
chart2.title = "Largest Subcategory Delta: Reddit Combined - Moltbook";
chart2.hasLegend = false;
chart2.xAxis = { axisType: "textAxis" };
chart2.yAxis = { numberFormatCode: "0.0" };
chart2.setPosition("J22", "Q50");

for (const sheet of [dashboard, summary, top, sub, ex, raw]) {
  styleSheet(sheet);
}

// Percent-like columns
for (const range of ["E2:G5"]) summary.getRange(range).setNumberFormat("0.0");
for (const range of ["D2:D13"]) top.getRange(range).setNumberFormat("0.00");
for (const range of ["D2:D80"]) sub.getRange(range).setNumberFormat("0.00");
dashboard.getRange("C5:E8").setNumberFormat("0.0");
dashboard.getRange("C13:C15").setNumberFormat("0.00");
dashboard.getRange("E13:F15").setNumberFormat("0.00");
dashboard.getRange("C20:C31").setNumberFormat("0.00");
dashboard.getRange("E20:F31").setNumberFormat("0.00");

// Compact visual verification renders.
await fs.mkdir(outDir, { recursive: true });
const dashPreview = await workbook.render({ sheetName: "Dashboard", range: "A1:Q50", scale: 1, format: "png" });
await fs.writeFile(path.join(outDir, "dashboard_preview.png"), new Uint8Array(await dashPreview.arrayBuffer()));

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(workbookPath);
console.log(workbookPath);
