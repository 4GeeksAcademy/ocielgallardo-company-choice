import {
  sampleAppointments,
  sampleClaims,
  sampleInvoiceRejectionPredictions,
  sampleInvoices,
  sampleNoShowPredictions,
  samplePatients
} from "./test-data.js";

const state = {
  modules: null
};

const outputNodes = {
  collections: document.getElementById("collections-output"),
  collectionsTable: document.getElementById("collections-table"),
  search: document.getElementById("search-output"),
  searchTable: document.getElementById("search-table"),
  transformations: document.getElementById("transformations-output"),
  transformationsTable: document.getElementById("transformations-table"),
  validations: document.getElementById("validations-output"),
  validationMessages: document.getElementById("validation-messages"),
  loadStatus: document.getElementById("load-status")
};

function setLoadStatus(message, type = "info") {
  const palette = {
    info: "border-slate-600 bg-slate-900/70 text-slate-200",
    success: "border-emerald-500/50 bg-emerald-500/10 text-emerald-200",
    error: "border-red-500/50 bg-red-500/10 text-red-200"
  };
  outputNodes.loadStatus.className = `rounded-xl border px-4 py-3 text-sm ${palette[type]}`;
  outputNodes.loadStatus.textContent = message;
}

// Carga el compilador de TypeScript en el navegador para transpilar los .ts existentes.
async function loadTypeScriptCompiler() {
  if (window.ts) return;

  await new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/typescript@5.6.3/lib/typescript.min.js";
    script.async = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error("No se pudo cargar TypeScript CDN."));
    document.head.appendChild(script);
  });
}

// Elimina imports del archivo de tipos para evitar resoluciones ESM en runtime del navegador.
function stripTypeOnlyImports(tsSource) {
  return tsSource
    .replace(/import\s+type\s*{[\s\S]*?}\s*from\s*["']\.\.\/types\/models["'];?\s*/gm, "")
    .replace(/import\s*{[\s\S]*?}\s*from\s*["']\.\.\/types\/models["'];?\s*/gm, "");
}

// Transpila un archivo .ts del proyecto y lo carga como modulo ESM en el browser.
async function loadTsModule(tsPath) {
  const response = await fetch(tsPath);
  if (!response.ok) {
    throw new Error(`No se pudo leer ${tsPath}.`);
  }

  const source = stripTypeOnlyImports(await response.text());
  const transpiled = window.ts.transpileModule(source, {
    compilerOptions: {
      module: window.ts.ModuleKind.ES2020,
      target: window.ts.ScriptTarget.ES2020,
      strict: false,
      removeComments: false
    }
  }).outputText;

  const moduleBlob = new Blob([transpiled], { type: "text/javascript" });
  const moduleUrl = URL.createObjectURL(moduleBlob);
  try {
    const imported = await import(moduleUrl);
    return imported;
  } finally {
    URL.revokeObjectURL(moduleUrl);
  }
}

async function loadProjectUtilities() {
  await loadTypeScriptCompiler();

  const [collections, search, transformations, validations] = await Promise.all([
    loadTsModule("./src/utils/collections.ts"),
    loadTsModule("./src/utils/search.ts"),
    loadTsModule("./src/utils/transformations.ts"),
    loadTsModule("./src/utils/validations.ts")
  ]);

  state.modules = { collections, search, transformations, validations };
}

function toPrettyJson(value) {
  return JSON.stringify(value, null, 2);
}

function renderJson(node, payload) {
  node.textContent = toPrettyJson(payload);
}

function renderTable(node, rows) {
  if (!rows || rows.length === 0) {
    node.innerHTML = "<p class=\"text-sm text-slate-400\">Sin resultados tabulares.</p>";
    return;
  }

  const keys = Object.keys(rows[0]);
  const header = keys.map((key) => `<th class=\"px-3 py-2 text-left font-semibold\">${key}</th>`).join("");
  const body = rows
    .map((row) => {
      const cells = keys.map((key) => `<td class=\"px-3 py-2 align-top\">${String(row[key])}</td>`).join("");
      return `<tr class=\"border-t border-slate-800\">${cells}</tr>`;
    })
    .join("");

  node.innerHTML = `
    <div class="overflow-x-auto rounded-lg border border-slate-800">
      <table class="w-full min-w-[620px] text-sm">
        <thead class="bg-slate-900 text-slate-300"><tr>${header}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  `;
}

function normalizePredictionRows() {
  const noShowRows = sampleNoShowPredictions.map((item) => ({
    ...item,
    category: "no-show"
  }));

  const rejectionRows = sampleInvoiceRejectionPredictions.map((item) => ({
    ...item,
    category: "invoice-rejection"
  }));

  return [...noShowRows, ...rejectionRows];
}

function runCollectionsDemo() {
  const rows = normalizePredictionRows();
  const { collections } = state.modules;

  const filteredByCategory = collections.filterByCategory(rows, "no-show");
  const filteredByStatus = collections.filterByStatus(rows, "pending");
  const filteredByRange = collections.filterByProbabilityRange(rows, { min: 0.3, max: 0.8 });
  const filteredCritical = collections.filterCritical(rows, {
    category: "invoice-rejection",
    status: "pending",
    probabilityRange: { min: 0.4 },
    onlyCritical: true
  });

  const orderedAsc = collections.sortByField(rows, "probability", "asc");
  const orderedMulti = collections.sortByMultipleFields(rows, [
    { field: "status", direction: "asc" },
    { field: "probability", direction: "desc" }
  ]);

  const oneById = collections.findOneById(rows, "predictionId", "ns-003");

  renderJson(outputNodes.collections, {
    sourceCount: rows.length,
    filteredByCategory,
    filteredByStatus,
    filteredByRange,
    filteredCritical,
    orderedAsc,
    orderedMulti,
    oneById
  });

  renderTable(outputNodes.collectionsTable, orderedMulti);
}

function runSearchDemo() {
  const { search, collections } = state.modules;

  const patientFound = search.linearSearchByField(samplePatients, "patientId", "pat-002");
  const unsortedInvoice = search.linearSearchUnsorted(sampleInvoices, (invoice) => invoice.status === "rejected");

  const sortedAppointments = collections.sortByField(sampleAppointments, "noShowProbability", "asc");
  const binaryByNumber = search.binarySearchByNumber(
    sortedAppointments,
    (appointment) => appointment.noShowProbability,
    0.52
  );

  const sortedPredictions = collections.sortByField(sampleNoShowPredictions, "predictionId", "asc");
  const binaryByField = search.binarySearchByField(sortedPredictions, "predictionId", "ns-003");

  renderJson(outputNodes.search, {
    patientFound,
    unsortedInvoice,
    sortedAppointments,
    binaryByNumber,
    sortedPredictions,
    binaryByField
  });

  renderTable(outputNodes.searchTable, sortedAppointments);
}

function runTransformationsDemo() {
  const { transformations } = state.modules;

  const noShowRate = transformations.calculateNoShowRate(sampleAppointments);
  const rejectionRate = transformations.calculateInvoiceRejectionRate(sampleInvoices);
  const alerts = transformations.generateCriticalAlerts(
    sampleNoShowPredictions,
    sampleInvoiceRejectionPredictions
  );
  const alertsByStatus = transformations.groupAlertsByStatus(alerts);
  const countInvoicesByStatus = transformations.countByCategory(sampleInvoices, "status");
  const totalInvoiced = transformations.calculateTotal(sampleInvoices, (invoice) => invoice.amount);
  const avgInvoiced = transformations.calculateAverage(sampleInvoices, (invoice) => invoice.amount);
  const maxInvoiced = transformations.calculateMax(sampleInvoices, (invoice) => invoice.amount);
  const minInvoiced = transformations.calculateMin(sampleInvoices, (invoice) => invoice.amount);

  renderJson(outputNodes.transformations, {
    noShowRate,
    rejectionRate,
    alerts,
    alertsByStatus,
    countInvoicesByStatus,
    totalInvoiced,
    avgInvoiced,
    maxInvoiced,
    minInvoiced,
    claimsInfo: sampleClaims.length === 0 ? "No hay claims en este contexto de ejemplo." : sampleClaims.length
  });

  renderTable(outputNodes.transformationsTable, alerts);
}

function renderValidationMessages(messages) {
  if (messages.length === 0) {
    outputNodes.validationMessages.innerHTML = "<p class=\"text-emerald-300\">Sin errores de validacion.</p>";
    return;
  }

  outputNodes.validationMessages.innerHTML = `
    <ul class="list-disc space-y-1 pl-5 text-red-300">
      ${messages.map((msg) => `<li>${msg}</li>`).join("")}
    </ul>
  `;
}

function runValidationsDemo() {
  const { validations } = state.modules;

  const patientErrors = validations.validatePatient(samplePatients[2]);
  const appointmentErrors = validations.validateAppointment(sampleAppointments[0]);
  const invoiceErrors = validations.validateInvoice(sampleInvoices[0], "US");

  const noShowPredictionErrors = validations.validateNoShowPrediction({
    ...sampleNoShowPredictions[0],
    criticalThreshold: 0.1
  });

  const recordErrors = validations.validateRecordBeforeProcessing({
    patient: samplePatients[2],
    appointment: {
      ...sampleAppointments[1],
      category: "Patient Experience and Access"
    },
    invoice: {
      ...sampleInvoices[1],
      rejectionProbability: 0.05
    }
  });

  const allErrors = [
    ...patientErrors,
    ...appointmentErrors,
    ...invoiceErrors,
    ...noShowPredictionErrors,
    ...recordErrors
  ];

  renderJson(outputNodes.validations, {
    patientErrors,
    appointmentErrors,
    invoiceErrors,
    noShowPredictionErrors,
    recordErrors
  });

  renderValidationMessages(allErrors);
}

async function bootstrap() {
  try {
    setLoadStatus("Cargando utilidades TypeScript del proyecto...", "info");
    await loadProjectUtilities();
    setLoadStatus("Utilidades cargadas. Ya puedes ejecutar pruebas manuales.", "success");
  } catch (error) {
    setLoadStatus(`Error al cargar utilidades: ${error.message}`, "error");
    return;
  }

  document.getElementById("run-collections").addEventListener("click", runCollectionsDemo);
  document.getElementById("run-search").addEventListener("click", runSearchDemo);
  document.getElementById("run-transformations").addEventListener("click", runTransformationsDemo);
  document.getElementById("run-validations").addEventListener("click", runValidationsDemo);

  document.getElementById("run-all").addEventListener("click", () => {
    runCollectionsDemo();
    runSearchDemo();
    runTransformationsDemo();
    runValidationsDemo();
  });
}

bootstrap();
