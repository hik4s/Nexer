import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CorporateCredentialsFields } from "./CorporateCredentialsFields";

describe("Corporate credential readiness", () => {
  it("blocks both systems and explains the missing validations", () => {
    render(<CorporateCredentialsFields />);
    expect(screen.getByLabelText("Usuário SGIND")).toBeDisabled();
    expect(screen.getByLabelText("Senha SGIND")).toBeDisabled();
    expect(screen.getByLabelText("Usuário IQOS")).toBeDisabled();
    expect(screen.getByLabelText("Senha IQOS")).toBeDisabled();
    expect(screen.getAllByText(/Telas de login e início identificadas/i)).toHaveLength(2);
    expect(screen.getAllByText(/Integração automática em preparação/i)).toHaveLength(2);
  });
});
