import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RecipeField } from "./RecipeField";

describe("Explicit execution choices", () => {
  it("does not infer an empty multiselect from loaded options", async () => {
    const change = vi.fn();
    render(<RecipeField name="regions" declaration={{type: "array", allow_empty: true, field: {control: "multiselect"}}}
      value={undefined} catalog={{options: [{value: "new", label: "Nova região", disabled: false}], error: null}} onChange={change} />);
    expect(change).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", {name: "Confirmar regions sem seleção"}));
    expect(change).toHaveBeenCalledWith("[]");
  });
  it("requires an explicit decision for an unchecked checkbox", async () => {
    const change = vi.fn();
    render(<RecipeField name="flag" declaration={{type: "boolean", field: {control: "checkbox"}}} value={undefined} onChange={change} />);
    expect(screen.getByRole("checkbox")).toBePartiallyChecked();
    expect(change).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", {name: "Definir flag como desmarcado"}));
    expect(change).toHaveBeenCalledWith("false");
  });
  it("allows confirming the browser's color without implying a recorded default", async () => {
    const change = vi.fn();
    render(<RecipeField name="color" declaration={{type: "string", field: {control: "color"}}} value={undefined} onChange={change} />);
    expect(change).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", {name: "Confirmar color"}));
    expect(change).toHaveBeenCalledWith("#000000");
  });
  it("uses the configured display name while keeping the parameter identity", async () => {
    const change = vi.fn();
    render(<RecipeField name="input_001" declaration={{type: "string", label: "Email do responsável", field: {control: "email", max_length: 80}}} value="" onChange={change} />);
    const field = screen.getByLabelText("Email do responsável");
    expect(field).toHaveAttribute("id", "parameter-input_001");
    expect(field).toHaveAttribute("type", "email");
    await userEvent.setup().type(field, "a");
    expect(change).toHaveBeenCalledWith("a");
  });

});
