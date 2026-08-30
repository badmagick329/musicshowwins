// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CorrectionForm } from "./correction-form";

function renderForm() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><CorrectionForm /></QueryClientProvider>);
}

function fillRequired() {
  fireEvent.change(screen.getByLabelText(/Page or record/), { target: { value: "Music Bank 2025-01-02" } });
  fireEvent.change(screen.getByLabelText(/What should be corrected/), { target: { value: "The winner is incorrect." } });
}

describe("CorrectionForm", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it("validates required fields and source URLs", () => {
    vi.stubGlobal("fetch", vi.fn());
    renderForm();
    fireEvent.change(screen.getByLabelText(/Supporting source/), { target: { value: "ftp://example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send correction" }));
    expect(screen.getByText("Enter the page or record to check.")).toBeTruthy();
    expect(screen.getByText("Describe what should be corrected.")).toBeTruthy();
    expect(screen.getByText("Enter a valid HTTP or HTTPS URL.")).toBeTruthy();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("clears the form and announces success", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ detail: "Report accepted." }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    renderForm();
    fillRequired();
    fireEvent.click(screen.getByRole("button", { name: "Send correction" }));
    await screen.findByText(/report has been received/);
    expect((screen.getByLabelText(/Page or record/) as HTMLInputElement).value).toBe("");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("preserves text after failure and blocks duplicate submission", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ detail: "Unavailable" }), { status: 503 }));
    vi.stubGlobal("fetch", fetchMock);
    renderForm();
    fillRequired();
    const button = screen.getByRole("button", { name: "Send correction" });
    fireEvent.click(button);
    fireEvent.submit(button.closest("form")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    expect((screen.getByLabelText(/Page or record/) as HTMLInputElement).value).toBe("Music Bank 2025-01-02");
    expect((screen.getByLabelText(/What should be corrected/) as HTMLTextAreaElement).value).toBe("The winner is incorrect.");
  });
});
