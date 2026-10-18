import { useRef, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  CircleAlert,
  Database,
  FileSpreadsheet,
  LayoutDashboard,
  LoaderCircle,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API_URL = "http://localhost:8000";

const navigation = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Datasets", icon: Database },
  { label: "Data quality", icon: ShieldCheck },
  { label: "Analytics", icon: BarChart3 },
  { label: "Data cleaning", icon: Sparkles },
];

function MetricCard({ title, value, description, icon: Icon }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <div className="rounded-xl bg-indigo-50 p-2 text-indigo-600">
          <Icon size={19} />
        </div>
      </div>
      <p className="mt-4 text-3xl font-semibold tracking-tight text-slate-900">
        {value}
      </p>
      <p className="mt-2 text-xs text-slate-500">{description}</p>
    </div>
  );
}

function App() {
  const fileInputRef = useRef(null);
  const [profile, setProfile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [activePage, setActivePage] = useState("Overview");
  const [previewData, setPreviewData] = useState(null);
  const [previewPage, setPreviewPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [sortBy, setSortBy] = useState("");
  const [sortOrder, setSortOrder] = useState("asc");
  const [filterColumn, setFilterColumn] = useState("");
  const [filterValue, setFilterValue] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [cleanOperation, setCleanOperation] = useState("fill_missing");
  const [cleanColumn, setCleanColumn] = useState("");
  const [cleanStrategy, setCleanStrategy] = useState("mean");
  const [cleanValue, setCleanValue] = useState("");
  const [cleanDtype, setCleanDtype] = useState("string");
  const [renameColumn, setRenameColumn] = useState("");
  const [cleanPreview, setCleanPreview] = useState(null);
  const [cleanLoading, setCleanLoading] = useState(false);
  const [cleanError, setCleanError] = useState("");
  const [cleanSuccess, setCleanSuccess] = useState("");
  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");
  const [groupByColumn, setGroupByColumn] = useState("");
  const [groupAggregation, setGroupAggregation] = useState("count");
  const [groupMetric, setGroupMetric] = useState("");
  const [groupResults, setGroupResults] = useState(null);
  const [groupLoading, setGroupLoading] = useState(false);
  const [groupError, setGroupError] = useState("");

  async function uploadFile(file) {
    if (!file) return;

    const extension = file.name.split(".").pop()?.toLowerCase();

    if (!["csv", "xlsx"].includes(extension)) {
      setError("Please select a CSV or XLSX file.");
      return;
    }

    setLoading(true);
    setError("");
    setProfile(null);
    setAnalyticsData(null);
    setGroupResults(null);
    setAnalyticsError("");
    setGroupError("");
    setPreviewData(null);
    setFileName(file.name);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/api/v1/datasets/profile`, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to analyze the file.");
      }

      setProfile(result);
      setSearchInput("");
      setActiveSearch("");
      setSortBy("");
      setSortOrder("asc");
      setFilterColumn("");
      setFilterValue("");

      await loadPreview(result.dataset_id, {
        page: 1,
        search: "",
        sortBy: "",
        sortOrder: "asc",
        filterColumn: "",
        filterValue: "",
      });
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Cannot connect to the backend. Make sure FastAPI is running."
          : err.message,
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadPreview(datasetId, options = {}) {
    if (!datasetId) return;

    const page = options.page ?? 1;
    const search = options.search ?? "";
    const sort = options.sortBy ?? "";
    const order = options.sortOrder ?? "asc";
    const filter = options.filterColumn ?? "";
    const value = options.filterValue ?? "";

    const params = new URLSearchParams({
      page: String(page),
      page_size: "10",
      sort_order: order,
    });

    if (search) params.set("search", search);
    if (sort) params.set("sort_by", sort);

    if (filter && value) {
      params.set("filter_column", filter);
      params.set("filter_value", value);
    }

    setPreviewLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/api/v1/datasets/${datasetId}/preview?${params}`,
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to load preview.");
      }

      setPreviewData(result);
      setPreviewPage(page);
    } catch (err) {
      setError(err.message);
    } finally {
      setPreviewLoading(false);
    }
  }

  function buildCleaningOperation() {
    switch (cleanOperation) {
      case "fill_missing": {
        const operation = {
          type: "fill_missing",
          columns: [cleanColumn],
          strategy: cleanStrategy,
        };

        if (cleanStrategy === "constant") {
          operation.value = cleanValue;
        }

        return operation;
      }

      case "drop_missing":
        return {
          type: "drop_missing",
          columns: cleanColumn ? [cleanColumn] : [],
        };

      case "remove_duplicates":
        return {
          type: "remove_duplicates",
          columns: cleanColumn ? [cleanColumn] : [],
          keep: "first",
        };

      case "drop_columns":
        return {
          type: "drop_columns",
          columns: [cleanColumn],
        };

      case "rename_columns":
        return {
          type: "rename_columns",
          mapping: {
            [cleanColumn]: renameColumn,
          },
        };

      case "convert_type":
        return {
          type: "convert_type",
          column: cleanColumn,
          dtype: cleanDtype,
        };

      default:
        throw new Error("Select a valid cleaning operation.");
    }
  }

  async function previewCleaning() {
    if (!profile?.dataset_id) {
      setCleanError("Upload a dataset before cleaning it.");
      return;
    }

    if (
      !cleanColumn &&
      !["drop_missing", "remove_duplicates"].includes(cleanOperation)
    ) {
      setCleanError("Select a column first.");
      return;
    }

    if (cleanOperation === "rename_columns" && !renameColumn.trim()) {
      setCleanError("Enter a new column name.");
      return;
    }

    setCleanLoading(true);
    setCleanError("");
    setCleanSuccess("");
    setCleanPreview(null);

    try {
      const response = await fetch(
        `${API_URL}/api/v1/datasets/${profile.dataset_id}/clean/preview`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(buildCleaningOperation()),
        },
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to preview cleaning.");
      }

      setCleanPreview(result);
    } catch (err) {
      setCleanError(
        err instanceof TypeError
          ? "Cannot connect to the backend. Check that FastAPI is running."
          : err.message,
      );
    } finally {
      setCleanLoading(false);
    }
  }

  async function applyCleaning() {
    if (!profile?.dataset_id || !cleanPreview) return;

    setCleanLoading(true);
    setCleanError("");
    setCleanSuccess("");

    try {
      const response = await fetch(
        `${API_URL}/api/v1/datasets/${profile.dataset_id}/clean/apply`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(buildCleaningOperation()),
        },
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to apply cleaning.");
      }

      setProfile((current) =>
        current
          ? {
              ...current,
              ...result.profile,
              dataset_id: current.dataset_id,
            }
          : current,
      );

      setSearchInput("");
      setActiveSearch("");
      setSortBy("");
      setSortOrder("asc");
      setFilterColumn("");
      setFilterValue("");
      setPreviewPage(1);
      setCleanPreview(null);
      setCleanSuccess(result.message || "Cleaning applied successfully.");

      await loadPreview(profile.dataset_id, {
        page: 1,
        search: "",
        sortBy: "",
        sortOrder: "asc",
        filterColumn: "",
        filterValue: "",
      });
    } catch (err) {
      setCleanError(
        err instanceof TypeError
          ? "Cannot connect to the backend. Check that FastAPI is running."
          : err.message,
      );
    } finally {
      setCleanLoading(false);
    }
  }

  async function loadAnalytics() {
    if (!profile?.dataset_id) {
      setAnalyticsError("Upload a dataset before running analytics.");
      return;
    }

    setAnalyticsLoading(true);
    setAnalyticsError("");

    try {
      const response = await fetch(
        `${API_URL}/api/v1/datasets/${profile.dataset_id}/analytics`,
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to load analytics.");
      }

      setAnalyticsData(result);
    } catch (err) {
      setAnalyticsError(
        err instanceof TypeError
          ? "Cannot connect to the backend. Check that FastAPI is running."
          : err.message,
      );
    } finally {
      setAnalyticsLoading(false);
    }
  }

  async function loadGroupByAnalytics() {
    if (!profile?.dataset_id) {
      setGroupError("Upload a dataset before running analytics.");
      return;
    }

    if (!groupByColumn) {
      setGroupError("Select a grouping column.");
      return;
    }

    if (groupAggregation !== "count" && !groupMetric) {
      setGroupError("Select a metric column for this aggregation.");
      return;
    }

    setGroupLoading(true);
    setGroupError("");
    setGroupResults(null);

    try {
      const body = {
        group_by: groupByColumn,
        aggregation: groupAggregation,
      };

      if (groupAggregation !== "count") {
        body.metric = groupMetric;
      }

      const response = await fetch(
        `${API_URL}/api/v1/datasets/${profile.dataset_id}/analytics/group-by`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body),
        },
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to calculate groups.");
      }

      setGroupResults(result);
    } catch (err) {
      setGroupError(
        err instanceof TypeError
          ? "Cannot connect to the backend. Check that FastAPI is running."
          : err.message,
      );
    } finally {
      setGroupLoading(false);
    }
  }

  const columns = profile
    ? Object.entries(profile.columns).map(([name, details]) => ({
        name,
        ...details,
      }))
    : [];

  const missingChartData = columns
    .filter((column) => column.missing_count > 0)
    .map((column) => ({
      name:
        column.name.length > 14 ? `${column.name.slice(0, 14)}…` : column.name,
      missing: column.missing_count,
    }))
    .sort((a, b) => b.missing - a.missing)
    .slice(0, 8);

  const qualityScore = profile?.data_quality.quality_score ?? 0;

  function renderCleaningTable(rows, tableColumns) {
    if (!rows?.length) {
      return <p className="p-4 text-sm text-slate-500">No rows to display.</p>;
    }

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              {tableColumns.map((column) => (
                <th key={column} className="whitespace-nowrap px-4 py-3">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row, index) => (
              <tr key={index}>
                {tableColumns.map((column) => (
                  <td
                    key={column}
                    className="whitespace-nowrap px-4 py-3 text-slate-600"
                  >
                    {row[column] == null || row[column] === ""
                      ? "—"
                      : String(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f7f8fc] text-slate-800">
      <aside className="fixed inset-y-0 left-0 z-10 hidden w-64 border-r border-slate-200 bg-white px-5 py-6 lg:flex lg:flex-col">
        <div className="flex items-center gap-3 px-2">
          <div className="rounded-xl bg-indigo-600 p-2.5 text-white">
            <Activity size={23} />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              DataLens
            </h1>
            <p className="text-xs text-slate-500">Data intelligence</p>
          </div>
        </div>

        <p className="mb-3 mt-10 px-3 text-xs font-semibold uppercase tracking-widest text-slate-400">
          Workspace
        </p>

        <nav className="space-y-1">
          {navigation.map(({ label, icon: Icon }) => (
            <button
              key={label}
              onClick={() => setActivePage(label)}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-medium transition ${
                activePage === label
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <Icon size={19} />
              {label}
            </button>
          ))}
        </nav>

        <div className="mt-auto rounded-2xl bg-slate-50 p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <Sparkles size={17} className="text-indigo-600" />
            DataLens Starter
          </div>
          <p className="text-xs leading-5 text-slate-500">
            Upload a dataset to discover data-quality issues and statistics.
          </p>
        </div>

        <button
          onClick={() => setActivePage("Settings")}
          className="mt-5 flex items-center gap-3 px-3 py-2 text-sm text-slate-500 hover:text-slate-900"
        >
          <Settings size={18} />
          Settings
        </button>
      </aside>

      <main className="min-h-screen lg:ml-64">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white/90 px-5 py-4 backdrop-blur sm:px-8">
          <div>
            <p className="text-xs text-slate-500">Workspace / Data</p>
            <h2 className="mt-1 text-lg font-semibold text-slate-900">
              {activePage}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-500 sm:flex">
              <Search size={16} />
              <span>Data workspace</span>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 font-semibold text-indigo-700">
              D
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-7xl space-y-7 p-5 sm:p-8">
          <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-indigo-600">
                <Sparkles size={16} />
                Your data, understood
              </div>
              <h2 className="text-3xl font-bold tracking-tight text-slate-900">
                Data overview
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Profile your data, find quality issues, and explore insights
                from one workspace.
              </p>
            </div>

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
              className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-60"
            >
              <UploadCloud size={18} />
              Upload dataset
            </button>
          </section>

          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx"
            className="hidden"
            onChange={(event) => {
              uploadFile(event.target.files?.[0]);
              event.target.value = "";
            }}
          />

          <section
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) {
                setDragging(false);
              }
            }}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              uploadFile(event.dataTransfer.files?.[0]);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition sm:p-10 ${
              dragging
                ? "border-indigo-500 bg-indigo-50"
                : "border-slate-300 bg-white hover:border-indigo-400 hover:bg-indigo-50/30"
            }`}
          >
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
              {loading ? (
                <LoaderCircle className="animate-spin" size={27} />
              ) : (
                <UploadCloud size={27} />
              )}
            </div>
            <h3 className="mt-4 font-semibold text-slate-900">
              {loading ? "Analyzing your dataset..." : "Drop your dataset here"}
            </h3>
            <p className="mt-2 text-sm text-slate-500">
              {loading
                ? "Profiling columns and calculating quality metrics."
                : "Or click to browse files. CSV and XLSX supported, up to 10 MB."}
            </p>
            {fileName && (
              <p className="mt-3 text-sm font-medium text-indigo-700">
                {fileName}
              </p>
            )}
          </section>

          {error && (
            <div
              role="alert"
              className="flex items-start justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
            >
              <div className="flex items-start gap-2">
                <CircleAlert size={18} className="mt-0.5 shrink-0" />
                {error}
              </div>
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={18} />
              </button>
            </div>
          )}

          {activePage === "Data cleaning" && (
            <section className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">
                  Data Cleaning Studio
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Clean your dataset, inspect the proposed changes, and apply
                  them only when you are satisfied with the preview.
                </p>
              </div>

              {!profile && (
                <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center">
                  <Database className="mx-auto text-slate-400" size={30} />
                  <p className="mt-3 font-semibold text-slate-800">
                    Upload a dataset to get started
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    Upload a CSV or XLSX file using the button above.
                  </p>
                </div>
              )}

              {profile && (
                <>
                  <div className="rounded-2xl border border-slate-200 bg-white p-6">
                    <h3 className="font-semibold text-slate-900">
                      Configure cleaning operation
                    </h3>

                    <div className="mt-5 grid gap-5 md:grid-cols-2">
                      <label className="text-sm font-medium text-slate-700">
                        Operation
                        <select
                          value={cleanOperation}
                          onChange={(event) => {
                            setCleanOperation(event.target.value);
                            setCleanPreview(null);
                            setCleanError("");
                            setCleanSuccess("");
                          }}
                          className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3"
                        >
                          <option value="fill_missing">
                            Fill missing values
                          </option>
                          <option value="drop_missing">
                            Drop missing rows
                          </option>
                          <option value="remove_duplicates">
                            Remove duplicates
                          </option>
                          <option value="drop_columns">Drop a column</option>
                          <option value="rename_columns">
                            Rename a column
                          </option>
                          <option value="convert_type">
                            Convert data type
                          </option>
                        </select>
                      </label>

                      <label className="text-sm font-medium text-slate-700">
                        Column
                        <select
                          value={cleanColumn}
                          onChange={(event) => {
                            setCleanColumn(event.target.value);
                            setCleanPreview(null);
                            setCleanError("");
                          }}
                          className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3"
                        >
                          <option value="">All columns</option>
                          {columns.map((column) => (
                            <option key={column.name} value={column.name}>
                              {column.name}
                            </option>
                          ))}
                        </select>
                      </label>

                      {cleanOperation === "fill_missing" && (
                        <>
                          <label className="text-sm font-medium text-slate-700">
                            Fill strategy
                            <select
                              value={cleanStrategy}
                              onChange={(event) => {
                                setCleanStrategy(event.target.value);
                                setCleanPreview(null);
                              }}
                              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3"
                            >
                              <option value="mean">Mean</option>
                              <option value="median">Median</option>
                              <option value="mode">Mode</option>
                              <option value="constant">Constant value</option>
                            </select>
                          </label>

                          {cleanStrategy === "constant" && (
                            <label className="text-sm font-medium text-slate-700">
                              Replacement value
                              <input
                                value={cleanValue}
                                onChange={(event) => {
                                  setCleanValue(event.target.value);
                                  setCleanPreview(null);
                                }}
                                placeholder="Enter replacement value"
                                className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3"
                              />
                            </label>
                          )}
                        </>
                      )}

                      {cleanOperation === "rename_columns" && (
                        <label className="text-sm font-medium text-slate-700">
                          New column name
                          <input
                            value={renameColumn}
                            onChange={(event) => {
                              setRenameColumn(event.target.value);
                              setCleanPreview(null);
                            }}
                            placeholder="Enter the new name"
                            className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3"
                          />
                        </label>
                      )}

                      {cleanOperation === "convert_type" && (
                        <label className="text-sm font-medium text-slate-700">
                          Target data type
                          <select
                            value={cleanDtype}
                            onChange={(event) => {
                              setCleanDtype(event.target.value);
                              setCleanPreview(null);
                            }}
                            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3"
                          >
                            <option value="integer">Integer</option>
                            <option value="float">Float</option>
                            <option value="string">String</option>
                            <option value="datetime">Datetime</option>
                          </select>
                        </label>
                      )}
                    </div>

                    <p className="mt-4 text-xs leading-5 text-slate-500">
                      {cleanOperation === "drop_missing"
                        ? "Leave Column as All columns to remove rows containing missing values anywhere."
                        : cleanOperation === "remove_duplicates"
                          ? "Choose a column to detect duplicates using that column, or All columns to compare entire rows."
                          : cleanOperation === "fill_missing"
                            ? "Mean and median require numeric data. Mode works with the most frequent value."
                            : "Review the preview before applying changes to your working dataset."}
                    </p>

                    <div className="mt-5 flex flex-wrap gap-3">
                      <button
                        type="button"
                        disabled={cleanLoading}
                        onClick={previewCleaning}
                        className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {cleanLoading ? (
                          <LoaderCircle size={17} className="animate-spin" />
                        ) : (
                          <Sparkles size={17} />
                        )}
                        Preview changes
                      </button>

                      {cleanPreview && (
                        <button
                          type="button"
                          disabled={cleanLoading}
                          onClick={applyCleaning}
                          className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-3 text-sm font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
                        >
                          <CheckCircle2 size={17} />
                          Apply cleaning
                        </button>
                      )}
                    </div>
                  </div>

                  {cleanError && (
                    <div
                      role="alert"
                      className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
                    >
                      {cleanError}
                    </div>
                  )}

                  {cleanSuccess && (
                    <div
                      role="status"
                      className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700"
                    >
                      {cleanSuccess}
                    </div>
                  )}

                  {cleanPreview && (
                    <>
                      <div className="grid gap-4 sm:grid-cols-2">
                        <div className="rounded-2xl border border-slate-200 bg-white p-5">
                          <p className="text-sm text-slate-500">
                            Rows before cleaning
                          </p>
                          <p className="mt-2 text-3xl font-semibold text-slate-900">
                            {cleanPreview.before.rows.toLocaleString()}
                          </p>
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-white p-5">
                          <p className="text-sm text-slate-500">
                            Rows after cleaning
                          </p>
                          <p className="mt-2 text-3xl font-semibold text-emerald-700">
                            {cleanPreview.after.rows.toLocaleString()}
                          </p>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-white p-5">
                        <h3 className="font-semibold text-slate-900">
                          Operation summary
                        </h3>
                        <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-xs leading-5 text-slate-700">
                          {JSON.stringify(cleanPreview.summary, null, 2)}
                        </pre>
                      </div>

                      <div className="grid gap-6 xl:grid-cols-2">
                        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                          <div className="border-b border-slate-100 p-5">
                            <h3 className="font-semibold text-slate-900">
                              Before cleaning
                            </h3>
                          </div>
                          {renderCleaningTable(
                            cleanPreview.before.preview,
                            cleanPreview.before.columns,
                          )}
                        </div>

                        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                          <div className="border-b border-slate-100 p-5">
                            <h3 className="font-semibold text-slate-900">
                              After cleaning
                            </h3>
                          </div>
                          {renderCleaningTable(
                            cleanPreview.after.preview,
                            cleanPreview.after.columns,
                          )}
                        </div>
                      </div>

                      <p className="text-xs leading-5 text-slate-500">
                        The tables show a sample of the dataset. Previewing does
                        not apply the operation. Click Apply cleaning to update
                        the working dataset.
                      </p>
                    </>
                  )}
                </>
              )}
            </section>
          )}

          {activePage === "Analytics" && (
            <section className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">
                  Analytics Studio
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Explore numerical distributions, correlations, and grouped
                  aggregations using your current working dataset.
                </p>
              </div>

              {!profile && (
                <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center">
                  <BarChart3 className="mx-auto text-slate-400" size={30} />
                  <p className="mt-3 font-semibold text-slate-800">
                    Upload a dataset to get started
                  </p>
                </div>
              )}

              {profile && (
                <>
                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                      <div>
                        <h3 className="font-semibold text-slate-900">
                          Numerical analysis
                        </h3>
                        <p className="mt-1 text-sm text-slate-500">
                          Summary statistics for numeric columns.
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={loadAnalytics}
                        disabled={analyticsLoading}
                        className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {analyticsLoading && (
                          <LoaderCircle size={17} className="animate-spin" />
                        )}
                        {analyticsLoading
                          ? "Analyzing..."
                          : "Run numerical analysis"}
                      </button>
                    </div>

                    {analyticsError && (
                      <p role="alert" className="mt-4 text-sm text-red-600">
                        {analyticsError}
                      </p>
                    )}

                    {analyticsData && (
                      <>
                        <div className="mt-6 grid gap-4 sm:grid-cols-3">
                          <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-sm text-slate-500">
                              Rows analyzed
                            </p>
                            <p className="mt-2 text-2xl font-semibold">
                              {analyticsData.total_rows.toLocaleString()}
                            </p>
                          </div>

                          <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-sm text-slate-500">Columns</p>
                            <p className="mt-2 text-2xl font-semibold">
                              {analyticsData.total_columns}
                            </p>
                          </div>

                          <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-sm text-slate-500">
                              Numeric columns
                            </p>
                            <p className="mt-2 text-2xl font-semibold">
                              {analyticsData.numeric_columns.length}
                            </p>
                          </div>
                        </div>

                        <div className="mt-6">
                          <h4 className="font-semibold text-slate-900">
                            Mean by numeric column
                          </h4>

                          {analyticsData.numerical_summary.some(
                            (item) => item.mean !== null,
                          ) ? (
                            <div className="mt-4 h-72">
                              <ResponsiveContainer width="100%" height="100%">
                                <BarChart
                                  data={analyticsData.numerical_summary.filter(
                                    (item) => item.mean !== null,
                                  )}
                                  margin={{
                                    top: 8,
                                    right: 16,
                                    left: 8,
                                    bottom: 8,
                                  }}
                                >
                                  <CartesianGrid
                                    strokeDasharray="3 3"
                                    vertical={false}
                                  />
                                  <XAxis
                                    dataKey="column"
                                    tick={{ fontSize: 11 }}
                                  />
                                  <YAxis tick={{ fontSize: 11 }} />
                                  <Tooltip />
                                  <Bar
                                    dataKey="mean"
                                    name="Mean"
                                    fill="#6366f1"
                                    radius={[5, 5, 0, 0]}
                                  />
                                </BarChart>
                              </ResponsiveContainer>
                            </div>
                          ) : (
                            <p className="mt-4 text-sm text-slate-500">
                              No numeric columns with available values were
                              found.
                            </p>
                          )}
                        </div>

                        <div className="mt-6 overflow-x-auto rounded-xl border border-slate-100">
                          <table className="w-full text-left text-sm">
                            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                              <tr>
                                <th className="px-4 py-3">Column</th>
                                <th className="px-4 py-3">Count</th>
                                <th className="px-4 py-3">Mean</th>
                                <th className="px-4 py-3">Median</th>
                                <th className="px-4 py-3">Std. dev.</th>
                                <th className="px-4 py-3">Min</th>
                                <th className="px-4 py-3">Max</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {analyticsData.numerical_summary.map((item) => (
                                <tr key={item.column}>
                                  <td className="px-4 py-3 font-medium">
                                    {item.column}
                                  </td>
                                  <td className="px-4 py-3">{item.count}</td>
                                  <td className="px-4 py-3">
                                    {item.mean?.toLocaleString() ?? "—"}
                                  </td>
                                  <td className="px-4 py-3">
                                    {item.median?.toLocaleString() ?? "—"}
                                  </td>
                                  <td className="px-4 py-3">
                                    {item.std?.toLocaleString() ?? "—"}
                                  </td>
                                  <td className="px-4 py-3">
                                    {item.min?.toLocaleString() ?? "—"}
                                  </td>
                                  <td className="px-4 py-3">
                                    {item.max?.toLocaleString() ?? "—"}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>

                        <div className="mt-8">
                          <h4 className="font-semibold text-slate-900">
                            Correlation matrix
                          </h4>
                          <p className="mt-1 text-sm text-slate-500">
                            Values range from -1 to 1. Correlation indicates
                            association, not causation.
                          </p>

                          {analyticsData.correlation.columns.length > 0 ? (
                            <div className="mt-4 overflow-x-auto rounded-xl border border-slate-100">
                              <table className="w-full text-center text-sm">
                                <thead className="bg-slate-50">
                                  <tr>
                                    <th className="px-4 py-3 text-left">
                                      Column
                                    </th>
                                    {analyticsData.correlation.columns.map(
                                      (column) => (
                                        <th
                                          key={column}
                                          className="whitespace-nowrap px-4 py-3"
                                        >
                                          {column}
                                        </th>
                                      ),
                                    )}
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                  {analyticsData.correlation.matrix.map(
                                    (row, rowIndex) => (
                                      <tr
                                        key={
                                          analyticsData.correlation.columns[
                                            rowIndex
                                          ]
                                        }
                                      >
                                        <th className="px-4 py-3 text-left font-medium">
                                          {
                                            analyticsData.correlation.columns[
                                              rowIndex
                                            ]
                                          }
                                        </th>
                                        {row.map((value, columnIndex) => (
                                          <td
                                            key={
                                              analyticsData.correlation.columns[
                                                columnIndex
                                              ]
                                            }
                                            className="px-4 py-3 tabular-nums"
                                          >
                                            {Number(value).toFixed(3)}
                                          </td>
                                        ))}
                                      </tr>
                                    ),
                                  )}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <p className="mt-4 text-sm text-slate-500">
                              No numeric columns are available for correlation
                              analysis.
                            </p>
                          )}
                        </div>
                      </>
                    )}
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <h3 className="font-semibold text-slate-900">
                      Group-by analysis
                    </h3>
                    <p className="mt-1 text-sm text-slate-500">
                      Aggregate records by a category or other column.
                    </p>

                    <form
                      className="mt-5 grid gap-4 md:grid-cols-2"
                      onSubmit={(event) => {
                        event.preventDefault();
                        loadGroupByAnalytics();
                      }}
                    >
                      <label className="text-sm font-medium text-slate-700">
                        Group by
                        <select
                          value={groupByColumn}
                          onChange={(event) => {
                            setGroupByColumn(event.target.value);
                            setGroupResults(null);
                            setGroupError("");
                          }}
                          className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3"
                        >
                          <option value="">Select grouping column</option>
                          {columns.map((column) => (
                            <option key={column.name} value={column.name}>
                              {column.name}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="text-sm font-medium text-slate-700">
                        Aggregation
                        <select
                          value={groupAggregation}
                          onChange={(event) => {
                            setGroupAggregation(event.target.value);
                            setGroupResults(null);
                            setGroupError("");
                          }}
                          className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3"
                        >
                          <option value="count">Count rows</option>
                          <option value="sum">Sum</option>
                          <option value="mean">Mean</option>
                          <option value="median">Median</option>
                          <option value="min">Minimum</option>
                          <option value="max">Maximum</option>
                        </select>
                      </label>

                      {groupAggregation !== "count" && (
                        <label className="text-sm font-medium text-slate-700">
                          Metric column
                          <select
                            value={groupMetric}
                            onChange={(event) => {
                              setGroupMetric(event.target.value);
                              setGroupResults(null);
                              setGroupError("");
                            }}
                            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3"
                          >
                            <option value="">Select metric column</option>
                            {columns.map((column) => (
                              <option key={column.name} value={column.name}>
                                {column.name}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}

                      <div className="flex items-end">
                        <button
                          type="submit"
                          disabled={groupLoading}
                          className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                        >
                          {groupLoading && (
                            <LoaderCircle size={17} className="animate-spin" />
                          )}
                          {groupLoading ? "Calculating..." : "Run group-by"}
                        </button>
                      </div>
                    </form>

                    {groupError && (
                      <p role="alert" className="mt-4 text-sm text-red-600">
                        {groupError}
                      </p>
                    )}

                    {groupResults && (
                      <div className="mt-6">
                        <h4 className="font-semibold text-slate-900">
                          Aggregation results
                        </h4>

                        {groupResults.results.length > 0 && (
                          <div className="mt-4 h-72">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart
                                data={groupResults.results}
                                margin={{
                                  top: 8,
                                  right: 16,
                                  left: 8,
                                  bottom: 8,
                                }}
                              >
                                <CartesianGrid
                                  strokeDasharray="3 3"
                                  vertical={false}
                                />
                                <XAxis
                                  dataKey={groupResults.group_by}
                                  tick={{ fontSize: 11 }}
                                />
                                <YAxis tick={{ fontSize: 11 }} />
                                <Tooltip />
                                <Bar
                                  dataKey={groupResults.aggregation}
                                  name={groupResults.aggregation}
                                  fill="#10b981"
                                  radius={[5, 5, 0, 0]}
                                />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        )}

                        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-100">
                          <table className="w-full text-left text-sm">
                            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                              <tr>
                                {groupResults.results.length > 0 &&
                                  Object.keys(groupResults.results[0]).map(
                                    (key) => (
                                      <th key={key} className="px-4 py-3">
                                        {key}
                                      </th>
                                    ),
                                  )}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {groupResults.results.map((row, index) => (
                                <tr key={index}>
                                  {Object.values(row).map(
                                    (value, valueIndex) => (
                                      <td
                                        key={valueIndex}
                                        className="px-4 py-3"
                                      >
                                        {value == null ? "—" : String(value)}
                                      </td>
                                    ),
                                  )}
                                </tr>
                              ))}
                            </tbody>
                          </table>

                          {groupResults.results.length === 0 && (
                            <p className="p-4 text-sm text-slate-500">
                              No groups were returned for this selection.
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </section>
          )}

          {activePage === "Data quality" && (
            <section className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">
                  Data Quality Dashboard
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Identify missing values, duplicate records, and potential
                  outliers in your dataset.
                </p>
              </div>

              {!profile ? (
                <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center">
                  <ShieldCheck className="mx-auto text-slate-400" size={30} />
                  <p className="mt-3 font-semibold text-slate-800">
                    Upload a dataset to get started
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    Quality metrics will appear here after profiling.
                  </p>
                </div>
              ) : (
                <>
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <MetricCard
                      title="Quality score"
                      value={`${qualityScore}%`}
                      description="Overall dataset quality"
                      icon={ShieldCheck}
                    />
                    <MetricCard
                      title="Missing values"
                      value={profile.data_quality.missing_values.toLocaleString()}
                      description={`${profile.data_quality.missing_percentage}% of all cells`}
                      icon={CircleAlert}
                    />
                    <MetricCard
                      title="Duplicate rows"
                      value={profile.data_quality.duplicate_rows.toLocaleString()}
                      description="Repeated complete records"
                      icon={Database}
                    />
                    <MetricCard
                      title="Columns with missing data"
                      value={
                        columns.filter((column) => column.missing_count > 0)
                          .length
                      }
                      description={`Outliers detected: ${columns.reduce((total, column) => total + (column.outlier_count ?? 0), 0).toLocaleString()}`}
                      icon={FileSpreadsheet}
                    />
                  </div>

                  <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                    <div className="border-b border-slate-100 p-5">
                      <h3 className="font-semibold text-slate-900">
                        Column quality analysis
                      </h3>
                      <p className="mt-1 text-sm text-slate-500">
                        Review missing values and outliers for each column.
                      </p>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                          <tr>
                            <th className="px-5 py-3">Column</th>
                            <th className="px-5 py-3">Data type</th>
                            <th className="px-5 py-3">Missing values</th>
                            <th className="px-5 py-3">Outliers</th>
                            <th className="px-5 py-3">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {columns.map((column) => {
                            const hasMissing = column.missing_count > 0;
                            const hasOutliers = (column.outlier_count ?? 0) > 0;
                            const hasIssues = hasMissing || hasOutliers;

                            return (
                              <tr key={column.name}>
                                <td className="whitespace-nowrap px-5 py-4 font-medium">
                                  {column.name}
                                </td>
                                <td className="px-5 py-4 text-slate-600">
                                  {column.dtype}
                                </td>
                                <td className="px-5 py-4">
                                  {column.missing_count} (
                                  {column.missing_percentage}%)
                                </td>
                                <td className="px-5 py-4">
                                  {column.outlier_count ?? "—"}
                                </td>
                                <td className="px-5 py-4">
                                  <span
                                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                                      hasIssues
                                        ? "bg-amber-50 text-amber-700"
                                        : "bg-emerald-50 text-emerald-700"
                                    }`}
                                  >
                                    {hasIssues ? "Needs review" : "Healthy"}
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <h3 className="font-semibold text-slate-900">
                      Recommended actions
                    </h3>
                    <div className="mt-4 space-y-3 text-sm text-slate-600">
                      {profile.data_quality.missing_values > 0 && (
                        <p>
                          • Review missing values and consider filling or
                          removing incomplete records.
                        </p>
                      )}
                      {profile.data_quality.duplicate_rows > 0 && (
                        <p>
                          • Review duplicate rows and remove unintended
                          duplicates.
                        </p>
                      )}
                      {columns.some(
                        (column) => (column.outlier_count ?? 0) > 0,
                      ) && (
                        <p>
                          • Investigate outliers to determine whether they
                          represent valid observations or data issues.
                        </p>
                      )}
                      {profile.data_quality.missing_values === 0 &&
                        profile.data_quality.duplicate_rows === 0 &&
                        !columns.some(
                          (column) => (column.outlier_count ?? 0) > 0,
                        ) && (
                          <p className="text-emerald-700">
                            No missing values, duplicate rows, or detected
                            outliers were found by these checks.
                          </p>
                        )}
                      <p className="pt-1">
                        To make changes, open the Data cleaning page and preview
                        the operation before applying it.
                      </p>
                    </div>
                  </div>
                </>
              )}
            </section>
          )}

          {activePage === "Overview" && (
            <>
              <section>
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-900">
                      Dataset health
                    </h3>
                    <p className="mt-1 text-sm text-slate-500">
                      {profile
                        ? `Analysis results for ${fileName}`
                        : "Your analysis metrics will appear here after upload."}
                    </p>
                  </div>
                  {profile && (
                    <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
                      <CheckCircle2 size={14} />
                      Profile generated
                    </span>
                  )}
                </div>

                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  <MetricCard
                    title="Total rows"
                    value={profile?.dataset.total_rows.toLocaleString() ?? "—"}
                    description="Records in the dataset"
                    icon={Database}
                  />
                  <MetricCard
                    title="Total columns"
                    value={profile?.dataset.total_columns ?? "—"}
                    description="Fields detected"
                    icon={FileSpreadsheet}
                  />
                  <MetricCard
                    title="Missing values"
                    value={
                      profile?.data_quality.missing_values.toLocaleString() ??
                      "—"
                    }
                    description={
                      profile
                        ? `${profile.data_quality.missing_percentage}% of all cells`
                        : "Awaiting dataset analysis"
                    }
                    icon={CircleAlert}
                  />
                  <MetricCard
                    title="Quality score"
                    value={profile ? `${qualityScore}%` : "—"}
                    description="Completeness × uniqueness"
                    icon={ShieldCheck}
                  />
                </div>
              </section>

              <section className="grid gap-6 xl:grid-cols-5">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 xl:col-span-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-semibold text-slate-900">
                        Missing values by column
                      </h3>
                      <p className="mt-1 text-sm text-slate-500">
                        Columns with incomplete records
                      </p>
                    </div>
                    <BarChart3 className="text-slate-400" size={20} />
                  </div>

                  <div className="mt-6 h-64">
                    {missingChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={missingChartData}
                          margin={{ top: 8, right: 8, left: -18, bottom: 8 }}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            vertical={false}
                          />
                          <XAxis
                            dataKey="name"
                            tick={{ fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                          />
                          <Tooltip />
                          <Bar
                            dataKey="missing"
                            name="Missing values"
                            fill="#6366f1"
                            radius={[5, 5, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex h-full flex-col items-center justify-center text-center">
                        <BarChart3 size={28} className="text-slate-300" />
                        <p className="mt-3 text-sm font-medium text-slate-600">
                          {profile
                            ? "No missing values detected"
                            : "Your chart will appear here"}
                        </p>
                        <p className="mt-1 text-xs text-slate-400">
                          {profile
                            ? "All columns are complete."
                            : "Upload a dataset to begin."}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-5 xl:col-span-2">
                  <h3 className="font-semibold text-slate-900">
                    Quality summary
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Key indicators for your dataset
                  </p>

                  <div className="mt-6 space-y-5">
                    <div>
                      <div className="mb-2 flex justify-between text-sm">
                        <span className="text-slate-600">Completeness</span>
                        <span className="font-semibold">
                          {profile
                            ? `${100 - profile.data_quality.missing_percentage}%`
                            : "—"}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-indigo-500"
                          style={{
                            width: `${profile ? 100 - profile.data_quality.missing_percentage : 0}%`,
                          }}
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                      <div className="flex items-center gap-3">
                        <div className="rounded-xl bg-amber-50 p-2 text-amber-600">
                          <CircleAlert size={18} />
                        </div>
                        <div>
                          <p className="text-sm font-medium">Duplicate rows</p>
                          <p className="mt-1 text-xs text-slate-500">
                            Repeated complete records
                          </p>
                        </div>
                      </div>
                      <span className="font-semibold">
                        {profile?.data_quality.duplicate_rows ?? "—"}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="rounded-xl bg-emerald-50 p-2 text-emerald-600">
                          <CheckCircle2 size={18} />
                        </div>
                        <div>
                          <p className="text-sm font-medium">
                            Columns analyzed
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            Fields successfully profiled
                          </p>
                        </div>
                      </div>
                      <span className="font-semibold">
                        {profile?.dataset.total_columns ?? "—"}
                      </span>
                    </div>
                  </div>
                </div>
              </section>
            </>
          )}

          {activePage === "Datasets" && (
            <>
              <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <div className="border-b border-slate-100 p-5">
                  <h3 className="font-semibold text-slate-900">
                    Dataset Explorer
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Search, filter, sort, and inspect your actual records.
                  </p>

                  <form
                    className="mt-4 flex flex-col gap-3 sm:flex-row"
                    onSubmit={(event) => {
                      event.preventDefault();
                      setActiveSearch(searchInput);
                      loadPreview(profile?.dataset_id, {
                        page: 1,
                        search: searchInput,
                        sortBy,
                        sortOrder,
                        filterColumn,
                        filterValue,
                      });
                    }}
                  >
                    <input
                      value={searchInput}
                      onChange={(event) => setSearchInput(event.target.value)}
                      placeholder="Search across all columns..."
                      className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-indigo-500"
                    />

                    <button
                      type="submit"
                      disabled={!profile || previewLoading}
                      className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
                    >
                      Search
                    </button>
                  </form>

                  <form
                    className="mt-3 flex flex-col gap-3 sm:flex-row"
                    onSubmit={(event) => {
                      event.preventDefault();
                      loadPreview(profile?.dataset_id, {
                        page: 1,
                        search: activeSearch,
                        sortBy,
                        sortOrder,
                        filterColumn,
                        filterValue,
                      });
                    }}
                  >
                    <select
                      value={filterColumn}
                      onChange={(event) => setFilterColumn(event.target.value)}
                      className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
                    >
                      <option value="">All columns</option>
                      {columns.map((column) => (
                        <option key={column.name} value={column.name}>
                          {column.name}
                        </option>
                      ))}
                    </select>

                    <input
                      value={filterValue}
                      onChange={(event) => setFilterValue(event.target.value)}
                      placeholder="Filter value..."
                      className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-indigo-500"
                    />

                    <button
                      type="submit"
                      disabled={!profile || previewLoading}
                      className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium hover:bg-slate-50"
                    >
                      Apply filter
                    </button>

                    <button
                      type="button"
                      disabled={!profile || previewLoading}
                      onClick={() => {
                        setSearchInput("");
                        setActiveSearch("");
                        setFilterColumn("");
                        setFilterValue("");
                        setSortBy("");
                        setSortOrder("asc");

                        loadPreview(profile?.dataset_id, {
                          page: 1,
                          search: "",
                          sortBy: "",
                          sortOrder: "asc",
                          filterColumn: "",
                          filterValue: "",
                        });
                      }}
                      className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium hover:bg-slate-50"
                    >
                      Reset
                    </button>
                  </form>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        {(previewData?.columns ?? []).map((column) => (
                          <th
                            key={column}
                            className="whitespace-nowrap px-5 py-3"
                          >
                            <button
                              type="button"
                              disabled={previewLoading}
                              className="font-semibold hover:text-indigo-600"
                              onClick={() => {
                                const nextOrder =
                                  sortBy === column && sortOrder === "asc"
                                    ? "desc"
                                    : "asc";

                                setSortBy(column);
                                setSortOrder(nextOrder);

                                loadPreview(profile.dataset_id, {
                                  page: 1,
                                  search: activeSearch,
                                  sortBy: column,
                                  sortOrder: nextOrder,
                                  filterColumn,
                                  filterValue,
                                });
                              }}
                            >
                              {column}
                              {sortBy === column
                                ? sortOrder === "asc"
                                  ? " ↑"
                                  : " ↓"
                                : ""}
                            </button>
                          </th>
                        ))}
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-100">
                      {previewData?.rows.map((row, index) => (
                        <tr
                          key={`${previewPage}-${index}`}
                          className="hover:bg-slate-50"
                        >
                          {previewData.columns.map((column) => (
                            <td
                              key={column}
                              className="max-w-xs whitespace-nowrap px-5 py-3 text-slate-600"
                            >
                              {row[column] === null || row[column] === undefined
                                ? "—"
                                : String(row[column])}
                            </td>
                          ))}
                        </tr>
                      ))}

                      {(!previewData || previewData.rows.length === 0) && (
                        <tr>
                          <td
                            colSpan={Math.max(
                              previewData?.columns.length ?? 0,
                              1,
                            )}
                            className="px-5 py-10 text-center text-sm text-slate-500"
                          >
                            {previewLoading
                              ? "Loading records..."
                              : previewData
                                ? "No matching records found."
                                : "Upload a dataset to explore its records."}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="flex flex-col gap-3 border-t border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-sm text-slate-500">
                    {previewData
                      ? `${previewData.total_rows.toLocaleString()} matching records · Page ${previewData.page} of ${Math.max(previewData.total_pages, 1)}`
                      : "No dataset loaded"}
                  </p>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={
                        !profile ||
                        !previewData ||
                        previewPage <= 1 ||
                        previewLoading
                      }
                      onClick={() =>
                        loadPreview(profile.dataset_id, {
                          page: previewPage - 1,
                          search: activeSearch,
                          sortBy,
                          sortOrder,
                          filterColumn,
                          filterValue,
                        })
                      }
                      className="rounded-lg border border-slate-200 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-40"
                    >
                      Previous
                    </button>

                    <button
                      type="button"
                      disabled={
                        !profile ||
                        !previewData ||
                        previewPage >= previewData.total_pages ||
                        previewLoading
                      }
                      onClick={() =>
                        loadPreview(profile.dataset_id, {
                          page: previewPage + 1,
                          search: activeSearch,
                          sortBy,
                          sortOrder,
                          filterColumn,
                          filterValue,
                        })
                      }
                      className="rounded-lg border border-slate-200 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </section>

              <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <div className="flex flex-col justify-between gap-3 border-b border-slate-100 p-5 sm:flex-row sm:items-center">
                  <div>
                    <h3 className="font-semibold text-slate-900">
                      Column profile
                    </h3>
                    <p className="mt-1 text-sm text-slate-500">
                      Data types, completeness, and unique values
                    </p>
                  </div>
                  {profile && (
                    <span className="text-xs text-slate-500">
                      {columns.length} columns
                    </span>
                  )}
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-5 py-3 font-medium">Column</th>
                        <th className="px-5 py-3 font-medium">Data type</th>
                        <th className="px-5 py-3 font-medium">Missing</th>
                        <th className="px-5 py-3 font-medium">Unique</th>
                        <th className="px-5 py-3 font-medium">Outliers</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {columns.map((column) => (
                        <tr
                          key={column.name}
                          className="transition hover:bg-slate-50"
                        >
                          <td className="whitespace-nowrap px-5 py-4 font-medium text-slate-800">
                            {column.name}
                          </td>
                          <td className="px-5 py-4">
                            <span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600">
                              {column.dtype}
                            </span>
                          </td>
                          <td className="px-5 py-4">
                            <span
                              className={
                                column.missing_count > 0
                                  ? "font-medium text-amber-600"
                                  : "text-slate-600"
                              }
                            >
                              {column.missing_count} (
                              {column.missing_percentage}%)
                            </span>
                          </td>
                          <td className="px-5 py-4 text-slate-600">
                            {column.unique_count}
                          </td>
                          <td className="px-5 py-4 text-slate-600">
                            {column.outlier_count ?? "—"}
                          </td>
                        </tr>
                      ))}

                      {!profile && (
                        <tr>
                          <td colSpan={5} className="px-5 py-12 text-center">
                            <Database
                              size={26}
                              className="mx-auto text-slate-300"
                            />
                            <p className="mt-3 font-medium text-slate-600">
                              No dataset loaded
                            </p>
                            <p className="mt-1 text-xs text-slate-400">
                              Upload a CSV or XLSX file to inspect its columns.
                            </p>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="flex items-center gap-2 border-t border-slate-100 px-5 py-3 text-xs text-slate-400">
                  <ArrowUpRight size={14} />
                  Statistics are calculated by the DataLens backend.
                </div>
              </section>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
