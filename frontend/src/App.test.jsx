import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import App from "./App";

const mockProfile = {
  dataset_id: "test-dataset-123",
  dataset: {
    total_rows: 3,
    total_columns: 2,
  },
  data_quality: {
    missing_values: 1,
    missing_percentage: 16.67,
    duplicate_rows: 0,
    quality_score: 83.33,
  },
  columns: {
    product: {
      dtype: "object",
      missing_count: 0,
      missing_percentage: 0,
      unique_count: 3,
      sample_values: ["Phone", "Laptop", "Tablet"],
    },
    price: {
      dtype: "float64",
      missing_count: 1,
      missing_percentage: 33.33,
      unique_count: 2,
      sample_values: [100, 200],
      outlier_count: 0,
    },
  },
};

const mockPreview = {
  dataset_id: "test-dataset-123",
  columns: ["product", "price"],
  rows: [
    { product: "Phone", price: 100 },
    { product: "Laptop", price: 200 },
    { product: "Tablet", price: null },
  ],
  total_rows: 3,
  page: 1,
  total_pages: 1,
};

function mockJsonResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  };
}

describe("DataLens dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders the dashboard before a dataset is uploaded", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "DataLens" }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", { name: "Data overview" }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: /upload dataset/i }),
    ).toBeInTheDocument();
  });

  it("uploads a CSV and displays the dataset metrics", async () => {
    fetch
      .mockResolvedValueOnce(mockJsonResponse(mockProfile))
      .mockResolvedValueOnce(mockJsonResponse(mockPreview));

    render(<App />);

    const file = new File(
      ["product,price\n" + "Phone,100\n" + "Laptop,200\n" + "Tablet,\n"],
      "products.csv",
      { type: "text/csv" },
    );

    const fileInput = document.querySelector('input[type="file"]');

    fireEvent.change(fileInput, {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    expect(fetch.mock.calls[0][0]).toContain("/api/v1/datasets/profile");

    expect(fetch.mock.calls[0][1].method).toBe("POST");

    await waitFor(() => {
      expect(
        screen.getByText("Analysis results for products.csv"),
      ).toBeInTheDocument();

      expect(screen.getAllByText("83.33%")).toHaveLength(2);
    });

    fireEvent.click(screen.getByRole("button", { name: /datasets/i }));

    await waitFor(() => {
      expect(screen.getByText("Phone")).toBeInTheDocument();
    });
  });

  it("displays an API error when the upload fails", async () => {
    fetch.mockResolvedValueOnce(
      mockJsonResponse({ detail: "Invalid CSV file." }, 400),
    );

    render(<App />);

    const file = new File(["invalid data"], "products.csv", {
      type: "text/csv",
    });

    const fileInput = document.querySelector('input[type="file"]');

    fireEvent.change(fileInput, {
      target: { files: [file] },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid CSV file.",
    );
  });

  it("opens the Data Cleaning Studio when no dataset is uploaded", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Data cleaning" }));

    expect(
      screen.getByRole("heading", { name: "Data Cleaning Studio" }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Upload a dataset to get started"),
    ).toBeInTheDocument();
  });

  it("previews filling missing values and sends the correct API request", async () => {
    const mockCleanPreview = {
      before: {
        rows: 3,
        columns: ["product", "price"],
        preview: [
          { product: "Phone", price: 100 },
          { product: "Laptop", price: 200 },
          { product: "Tablet", price: null },
        ],
      },
      after: {
        rows: 3,
        columns: ["product", "price"],
        preview: [
          { product: "Phone", price: 100 },
          { product: "Laptop", price: 200 },
          { product: "Tablet", price: 150 },
        ],
      },
      summary: {
        operation: "fill_missing",
        columns_modified: ["price"],
      },
    };

    fetch
      .mockResolvedValueOnce(mockJsonResponse(mockProfile))
      .mockResolvedValueOnce(mockJsonResponse(mockPreview))
      .mockResolvedValueOnce(mockJsonResponse(mockCleanPreview));

    render(<App />);

    const file = new File(
      ["product,price\nPhone,100\nLaptop,200\nTablet,\n"],
      "products.csv",
      { type: "text/csv" },
    );

    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: { files: [file] },
    });

    await screen.findByText("Analysis results for products.csv");

    fireEvent.click(screen.getByRole("button", { name: "Data cleaning" }));

    fireEvent.change(screen.getByLabelText("Column"), {
      target: { value: "price" },
    });

    fireEvent.click(screen.getByRole("button", { name: /preview changes/i }));

    await screen.findByText("Operation summary");

    expect(fetch).toHaveBeenCalledTimes(3);

    expect(fetch.mock.calls[2][0]).toContain(
      "/api/v1/datasets/test-dataset-123/clean/preview",
    );

    expect(fetch.mock.calls[2][1].method).toBe("POST");

    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual({
      type: "fill_missing",
      columns: ["price"],
      strategy: "mean",
    });

    expect(screen.getByText("150")).toBeInTheDocument();
  });

  it("applies a cleaning operation and displays the success message", async () => {
    const mockCleanPreview = {
      before: {
        rows: 3,
        columns: ["product", "price"],
        preview: [
          { product: "Phone", price: 100 },
          { product: "Laptop", price: 200 },
          { product: "Tablet", price: null },
        ],
      },
      after: {
        rows: 3,
        columns: ["product", "price"],
        preview: [
          { product: "Phone", price: 100 },
          { product: "Laptop", price: 200 },
          { product: "Tablet", price: 150 },
        ],
      },
      summary: {
        operation: "fill_missing",
        columns_modified: ["price"],
      },
    };

    const updatedProfile = {
      ...mockProfile,
      data_quality: {
        ...mockProfile.data_quality,
        missing_values: 0,
        missing_percentage: 0,
        quality_score: 100,
      },
      columns: {
        ...mockProfile.columns,
        price: {
          ...mockProfile.columns.price,
          missing_count: 0,
          missing_percentage: 0,
        },
      },
    };

    const updatedPreview = {
      ...mockPreview,
      rows: [
        { product: "Phone", price: 100 },
        { product: "Laptop", price: 200 },
        { product: "Tablet", price: 150 },
      ],
    };

    fetch
      .mockResolvedValueOnce(mockJsonResponse(mockProfile))
      .mockResolvedValueOnce(mockJsonResponse(mockPreview))
      .mockResolvedValueOnce(mockJsonResponse(mockCleanPreview))
      .mockResolvedValueOnce(
        mockJsonResponse({
          message: "Cleaning applied successfully.",
          profile: updatedProfile,
        }),
      )
      .mockResolvedValueOnce(mockJsonResponse(updatedPreview));

    render(<App />);

    const file = new File(
      ["product,price\nPhone,100\nLaptop,200\nTablet,\n"],
      "products.csv",
      { type: "text/csv" },
    );

    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: { files: [file] },
    });

    await screen.findByText("Analysis results for products.csv");

    fireEvent.click(screen.getByRole("button", { name: "Data cleaning" }));

    fireEvent.change(screen.getByLabelText("Column"), {
      target: { value: "price" },
    });

    fireEvent.click(screen.getByRole("button", { name: /preview changes/i }));

    await screen.findByText("Operation summary");

    fireEvent.click(screen.getByRole("button", { name: /apply cleaning/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Cleaning applied successfully.",
    );

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(6);
    });

    expect(fetch.mock.calls[3][0]).toContain(
      "/api/v1/datasets/test-dataset-123/clean/apply",
    );

    expect(fetch.mock.calls[3][1].method).toBe("POST");

    expect(JSON.parse(fetch.mock.calls[3][1].body)).toEqual({
      type: "fill_missing",
      columns: ["price"],
      strategy: "mean",
    });

    expect(fetch.mock.calls[4][0]).toContain(
      "/api/v1/datasets/test-dataset-123/preview",
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Cleaning applied successfully.",
    );
  });

  it("opens Analytics Studio when no dataset is uploaded", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Analytics" }));

    expect(
      screen.getByRole("heading", { name: "Analytics Studio" }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Upload a dataset to get started"),
    ).toBeInTheDocument();
  });
});
