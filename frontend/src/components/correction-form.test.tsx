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
  fireEvent.change(screen.getByLabelText(/Your feedback/), { target: { value: "Please make searching by song easier." } });
}

describe("CorrectionForm", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it("validates feedback and optional email", () => {
    vi.stubGlobal("fetch", vi.fn());
    renderForm();
    fireEvent.change(screen.getByLabelText(/Email, if/), { target: { value: "not-an-email" } });
    fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));
    expect(screen.getByText("Enter your feedback.")).toBeTruthy();
    expect(screen.getByText("Enter a valid email address.")).toBeTruthy();
    expect(fetch).not.toHaveBeenCalled();
    expect(screen.queryByText(/sent privately through Discord/)).toBeNull();
    expect(screen.queryByText(/They are not published/)).toBeNull();
  });

  it("clears the form and announces success", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({ detail: "Report accepted." }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    renderForm();
    fillRequired();
    fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));
    await screen.findByText("Thanks! Your feedback was sent.");
    expect((screen.getByLabelText(/Related page or link/) as HTMLInputElement).value).toBe("");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body)).page_or_record).toBe("");
  });

  it("preserves text after failure and blocks duplicate submission", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({ detail: "Unavailable" }), { status: 503 }));
    vi.stubGlobal("fetch", fetchMock);
    renderForm();
    fillRequired();
    const button = screen.getByRole("button", { name: "Send feedback" });
    fireEvent.click(button);
    fireEvent.submit(button.closest("form")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    expect((screen.getByLabelText(/Related page or link/) as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText(/Your feedback/) as HTMLTextAreaElement).value).toBe("Please make searching by song easier.");
  });
});
